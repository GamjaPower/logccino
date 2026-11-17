use std::net::SocketAddr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use chrono::{DateTime, Datelike, Utc};
use clap::Parser;
use regex::Regex;
use serde::{Deserialize, Serialize};
use tokio::net::{TcpListener, UdpSocket};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::mpsc;
use tracing::{info, warn, error};

#[derive(Parser, Debug)]
#[command(author, version, about = "Logccino Enterprise Security Syslog Collector")]
struct Args {
    #[arg(short, long, default_value = "0.0.0.0")]
    host: String,

    #[arg(short, long, default_value_t = 1514)]
    port: u16,

    #[arg(short, long, default_value = "http://127.0.0.1:8000/api/v1/ingest/syslog")]
    backend_url: String,

    #[arg(long, default_value_t = 1515)]
    metrics_port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityEvent {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub category: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub action: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub outcome: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_ip: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_port: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub destination_ip: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub destination_port: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub process_command: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParsedSyslog {
    #[serde(rename = "@timestamp")]
    pub timestamp: String,
    pub service: String,
    pub host: String,
    pub level: String,
    pub source: String,
    pub sourcetype: String,
    pub message: String,
    pub facility: String,
    pub severity: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub program: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pid: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub security: Option<SecurityEvent>,
}

#[derive(Debug, Default)]
pub struct CollectorMetrics {
    pub received_total: AtomicU64,
    pub parsed_total: AtomicU64,
    pub forwarded_total: AtomicU64,
    pub security_alerts_total: AtomicU64,
    pub start_time_epoch: AtomicU64,
}

pub struct SyslogParser {
    re_rfc3164: Regex,
    re_rfc5424: Regex,
    re_ssh_failed: Regex,
    re_ssh_accepted: Regex,
    re_sudo: Regex,
    re_ufw: Regex,
    re_pam_fail: Regex,
}

impl SyslogParser {
    pub fn new() -> Self {
        Self {
            // <PRI>Mmm dd hh:mm:ss host tag[pid]: message
            re_rfc3164: Regex::new(r"^(?:<(\d{1,3})>)?([A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+([^\s:]+)\s+([a-zA-Z0-9_\-\.]+)(?:\[(\d+)\])?:\s*(.*)$").unwrap(),
            // <PRI>1 timestamp host app procid msgid - message
            re_rfc5424: Regex::new(r"^<(\d{1,3})>1\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(?:\[.*?\]|-)\s*(.*)$").unwrap(),
            // Filebeat auth module patterns
            re_ssh_failed: Regex::new(r"Failed (?:password|publickey) for (?:invalid user )?(\S+) from (\S+) port (\d+)").unwrap(),
            re_ssh_accepted: Regex::new(r"Accepted (?:password|publickey) for (\S+) from (\S+) port (\d+)").unwrap(),
            re_sudo: Regex::new(r"sudo:\s*(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(\S+)\s*;\s*USER=(\S+)\s*;\s*COMMAND=(.*)").unwrap(),
            re_ufw: Regex::new(r"\[UFW BLOCK\]\s+.*SRC=([0-9\.]+)\s+DST=([0-9\.]+).*PROTO=([A-Z0-9]+)(?:.*SPT=(\d+))?(?:.*DPT=(\d+))?").unwrap(),
            re_pam_fail: Regex::new(r"pam_unix\([^)]+\): authentication failure;.*(?:user=(\S+))?").unwrap(),
        }
    }

    pub fn parse(&self, raw: &str, client_addr: Option<SocketAddr>) -> ParsedSyslog {
        let trimmed = raw.trim();
        let fallback_host = client_addr.map(|a| a.ip().to_string()).unwrap_or_else(|| "syslog-host".to_string());
        let now_iso = Utc::now().to_rfc3339();

        let mut pri: u32 = 13; // default: user.notice (13 = 1*8 + 5)
        let mut host = fallback_host;
        let mut program: Option<String> = None;
        let mut pid: Option<u32> = None;
        let mut message = trimmed.to_string();
        let mut timestamp = now_iso;

        if let Some(caps) = self.re_rfc3164.captures(trimmed) {
            if let Some(p) = caps.get(1) {
                pri = p.as_str().parse().unwrap_or(13);
            }
            if let Some(h) = caps.get(3) {
                host = h.as_str().to_string();
            }
            if let Some(prog) = caps.get(4) {
                program = Some(prog.as_str().to_string());
            }
            if let Some(pid_m) = caps.get(5) {
                pid = pid_m.as_str().parse().ok();
            }
            if let Some(msg) = caps.get(6) {
                message = msg.as_str().to_string();
            }
        } else if let Some(caps) = self.re_rfc5424.captures(trimmed) {
            if let Some(p) = caps.get(1) {
                pri = p.as_str().parse().unwrap_or(13);
            }
            if let Some(ts) = caps.get(2) {
                timestamp = ts.as_str().to_string();
            }
            if let Some(h) = caps.get(3) {
                host = h.as_str().to_string();
            }
            if let Some(prog) = caps.get(4) {
                program = Some(prog.as_str().to_string());
            }
            if let Some(pid_m) = caps.get(5) {
                pid = pid_m.as_str().parse().ok();
            }
            if let Some(msg) = caps.get(7) {
                message = msg.as_str().to_string();
            }
        }

        let facility_num = pri / 8;
        let severity_num = pri % 8;

        let facility = match facility_num {
            0 => "kernel",
            1 => "user",
            2 => "mail",
            3 => "daemon",
            4 | 10 => "auth",
            5 => "syslog",
            9 => "cron",
            16..=23 => "local",
            _ => "unknown",
        }.to_string();

        let (severity, level) = match severity_num {
            0 => ("emergency", "FATAL"),
            1 => ("alert", "FATAL"),
            2 => ("critical", "ERROR"),
            3 => ("error", "ERROR"),
            4 => ("warning", "WARN"),
            5 => ("notice", "INFO"),
            6 => ("informational", "INFO"),
            7 => ("debug", "DEBUG"),
            _ => ("notice", "INFO"),
        };

        // Security Event Extraction (Filebeat system/auth module spec)
        let security = self.extract_security_event(&message);
        let final_level = if security.as_ref().map_or(false, |s| s.outcome.as_deref() == Some("failure")) {
            "ERROR"
        } else {
            level
        }.to_string();

        ParsedSyslog {
            timestamp,
            service: program.clone().unwrap_or_else(|| "security-syslog".to_string()),
            host,
            level: final_level,
            source: "syslog".to_string(),
            sourcetype: "syslog".to_string(),
            message,
            facility,
            severity: severity.to_string(),
            program,
            pid,
            security,
        }
    }

    fn extract_security_event(&self, msg: &str) -> Option<SecurityEvent> {
        if let Some(caps) = self.re_ssh_failed.captures(msg) {
            let user = caps.get(1).map(|m| m.as_str().to_string());
            let src_ip = caps.get(2).map(|m| m.as_str().to_string());
            let src_port = caps.get(3).and_then(|m| m.as_str().parse().ok());
            return Some(SecurityEvent {
                category: Some("authentication".to_string()),
                action: Some("ssh_login_failure".to_string()),
                outcome: Some("failure".to_string()),
                source_ip: src_ip,
                source_port: src_port,
                destination_ip: None,
                destination_port: Some(22),
                user_name: user,
                process_command: None,
            });
        }

        if let Some(caps) = self.re_ssh_accepted.captures(msg) {
            let user = caps.get(1).map(|m| m.as_str().to_string());
            let src_ip = caps.get(2).map(|m| m.as_str().to_string());
            let src_port = caps.get(3).and_then(|m| m.as_str().parse().ok());
            return Some(SecurityEvent {
                category: Some("authentication".to_string()),
                action: Some("ssh_login_success".to_string()),
                outcome: Some("success".to_string()),
                source_ip: src_ip,
                source_port: src_port,
                destination_ip: None,
                destination_port: Some(22),
                user_name: user,
                process_command: None,
            });
        }

        if let Some(caps) = self.re_sudo.captures(msg) {
            let user = caps.get(1).map(|m| m.as_str().to_string());
            let cmd = caps.get(5).map(|m| m.as_str().to_string());
            return Some(SecurityEvent {
                category: Some("privilege_escalation".to_string()),
                action: Some("sudo".to_string()),
                outcome: Some("success".to_string()),
                source_ip: None,
                source_port: None,
                destination_ip: None,
                destination_port: None,
                user_name: user,
                process_command: cmd,
            });
        }

        if let Some(caps) = self.re_ufw.captures(msg) {
            let src_ip = caps.get(1).map(|m| m.as_str().to_string());
            let dst_ip = caps.get(2).map(|m| m.as_str().to_string());
            let dst_port = caps.get(5).and_then(|m| m.as_str().parse().ok());
            return Some(SecurityEvent {
                category: Some("network".to_string()),
                action: Some("firewall_drop".to_string()),
                outcome: Some("blocked".to_string()),
                source_ip: src_ip,
                source_port: None,
                destination_ip: dst_ip,
                destination_port: dst_port,
                user_name: None,
                process_command: None,
            });
        }

        if let Some(caps) = self.re_pam_fail.captures(msg) {
            let user = caps.get(1).map(|m| m.as_str().to_string());
            return Some(SecurityEvent {
                category: Some("authentication".to_string()),
                action: Some("pam_auth_failure".to_string()),
                outcome: Some("failure".to_string()),
                source_ip: None,
                source_port: None,
                destination_ip: None,
                destination_port: None,
                user_name: user,
                process_command: None,
            });
        }

        None
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    let args = Args::parse();

    let metrics = Arc::new(CollectorMetrics::default());
    metrics.start_time_epoch.store(Utc::now().timestamp() as u64, Ordering::SeqCst);

    let parser = Arc::new(SyslogParser::new());
    let (tx, mut rx) = mpsc::channel::<ParsedSyslog>(10000);

    info!("Starting Logccino Enterprise Security Syslog Collector on {}:{} (UDP & TCP)", args.host, args.port);

    // 1. UDP Listener
    let udp_bind = format!("{}:{}", args.host, args.port);
    let udp_socket = UdpSocket::bind(&udp_bind).await?;
    let udp_tx = tx.clone();
    let udp_parser = parser.clone();
    let udp_metrics = metrics.clone();

    tokio::spawn(async move {
        let mut buf = [0u8; 8192];
        loop {
            match udp_socket.recv_from(&mut buf).await {
                Ok((len, src)) => {
                    udp_metrics.received_total.fetch_add(1, Ordering::Relaxed);
                    if let Ok(msg_str) = std::str::from_utf8(&buf[..len]) {
                        let parsed = udp_parser.parse(msg_str, Some(src));
                        if parsed.security.is_some() {
                            udp_metrics.security_alerts_total.fetch_add(1, Ordering::Relaxed);
                        }
                        udp_metrics.parsed_total.fetch_add(1, Ordering::Relaxed);
                        let _ = udp_tx.send(parsed).await;
                    }
                }
                Err(e) => {
                    warn!("UDP recv error: {}", e);
                }
            }
        }
    });

    // 2. TCP Listener
    let tcp_bind = format!("{}:{}", args.host, args.port);
    let tcp_listener = TcpListener::bind(&tcp_bind).await?;
    let tcp_tx = tx.clone();
    let tcp_parser = parser.clone();
    let tcp_metrics = metrics.clone();

    tokio::spawn(async move {
        loop {
            if let Ok((socket, src)) = tcp_listener.accept().await {
                let tx = tcp_tx.clone();
                let parser = tcp_parser.clone();
                let metrics = tcp_metrics.clone();

                tokio::spawn(async move {
                    let mut reader = BufReader::new(socket);
                    let mut line = String::new();
                    while let Ok(n) = reader.read_line(&mut line).await {
                        if n == 0 { break; }
                        metrics.received_total.fetch_add(1, Ordering::Relaxed);
                        let parsed = parser.parse(&line, Some(src));
                        if parsed.security.is_some() {
                            metrics.security_alerts_total.fetch_add(1, Ordering::Relaxed);
                        }
                        metrics.parsed_total.fetch_add(1, Ordering::Relaxed);
                        let _ = tx.send(parsed).await;
                        line.clear();
                    }
                });
            }
        }
    });

    // 3. Batch Forwarder to Logccino API
    let backend_url = args.backend_url.clone();
    let forward_metrics = metrics.clone();
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()?;

    tokio::spawn(async move {
        let mut batch = Vec::with_capacity(100);
        let mut interval = tokio::time::interval(Duration::from_millis(500));

        loop {
            tokio::select! {
                Some(log) = rx.recv() => {
                    batch.push(log);
                    if batch.len() >= 100 {
                        flush_batch(&client, &backend_url, &mut batch, &forward_metrics).await;
                    }
                }
                _ = interval.tick() => {
                    if !batch.is_empty() {
                        flush_batch(&client, &backend_url, &mut batch, &forward_metrics).await;
                    }
                }
            }
        }
    });

    // 4. Internal HTTP Metrics Listener for Logccino Dashboard
    let metrics_bind = format!("127.0.0.1:{}", args.metrics_port);
    let metrics_server = TcpListener::bind(&metrics_bind).await?;
    let server_metrics = metrics.clone();
    let collector_port = args.port;

    tokio::spawn(async move {
        loop {
            if let Ok((mut stream, _)) = metrics_server.accept().await {
                use tokio::io::AsyncWriteExt;
                let rx_cnt = server_metrics.received_total.load(Ordering::Relaxed);
                let parsed_cnt = server_metrics.parsed_total.load(Ordering::Relaxed);
                let fwd_cnt = server_metrics.forwarded_total.load(Ordering::Relaxed);
                let sec_cnt = server_metrics.security_alerts_total.load(Ordering::Relaxed);
                let start_ep = server_metrics.start_time_epoch.load(Ordering::Relaxed);
                let now_ep = Utc::now().timestamp() as u64;
                let uptime_sec = now_ep.saturating_sub(start_ep);

                let stats = serde_json::json!({
                    "status": "running",
                    "collector": "Rust High-Performance Syslog Engine",
                    "port": collector_port,
                    "protocols": ["UDP", "TCP"],
                    "uptime_seconds": uptime_sec,
                    "received_total": rx_cnt,
                    "parsed_total": parsed_cnt,
                    "forwarded_total": fwd_cnt,
                    "security_alerts_total": sec_cnt,
                    "throughput_eps": if uptime_sec > 0 { (rx_cnt as f64) / (uptime_sec as f64) } else { 0.0 }
                });

                let body = stats.to_string();
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(), body
                );
                let _ = stream.write_all(resp.as_bytes()).await;
            }
        }
    });

    info!("Collector running successfully. Metrics exposed on http://{}", metrics_bind);
    // Keep main thread alive
    tokio::signal::ctrl_c().await?;
    info!("Shutting down syslog collector.");
    Ok(())
}

async fn flush_batch(
    client: &reqwest::Client,
    url: &str,
    batch: &mut Vec<ParsedSyslog>,
    metrics: &CollectorMetrics,
) {
    let count = batch.len();
    let payload = serde_json::json!({
        "events": batch
    });

    match client.post(url).json(&payload).send().await {
        Ok(resp) if resp.status().is_success() => {
            metrics.forwarded_total.fetch_add(count as u64, Ordering::Relaxed);
        }
        Ok(resp) => {
            warn!("Failed to ingest batch to {}: HTTP {}", url, resp.status());
        }
        Err(e) => {
            warn!("Error connecting to Logccino backend {}: {}", url, e);
        }
    }
    batch.clear();
}
