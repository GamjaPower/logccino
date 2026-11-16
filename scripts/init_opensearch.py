import json
import os
import sys
from datetime import datetime, timezone
from opensearchpy import OpenSearch

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
INDEX_TEMPLATE_PATH = "configs/index_template.json"

def main():
    print(f"Connecting to OpenSearch at {OPENSEARCH_HOST}...")
    client = OpenSearch(hosts=[OPENSEARCH_HOST], ssl_show_warn=False)

    if not client.ping():
        print("❌ Cannot connect to OpenSearch. Make sure 'docker compose up -d' is running.")
        sys.exit(1)

    print(" Connected to OpenSearch.")

    # 1. 인덱스 템플릿 등록
    if os.path.exists(INDEX_TEMPLATE_PATH):
        with open(INDEX_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template_body = json.load(f)
        
        client.indices.put_index_template(name="logccino-template", body=template_body)
        print(" Successfully applied index template: logccino-template")

    # 2. 샘플 로그 등록
    sample_index = f"logccino-logs-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"
    sample_logs = [
        {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "host": "web-server-01",
            "service": "auth-service",
            "source": "/var/log/auth.log",
            "sourcetype": "json",
            "level": "INFO",
            "message": "User login successful for user: user123",
            "attributes": {"user_id": "user123", "ip": "192.168.1.10", "duration_ms": 45}
        },
        {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "host": "web-server-02",
            "service": "auth-service",
            "source": "/var/log/auth.log",
            "sourcetype": "json",
            "level": "ERROR",
            "message": "DatabaseConnectionTimeoutException: Failed to acquire DB pool connection",
            "attributes": {"error_code": "DB_CONN_TIMEOUT", "pool_size": 20, "wait_time_ms": 3000}
        },
        {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "host": "payment-api-01",
            "service": "payment-service",
            "source": "/var/log/payment.log",
            "sourcetype": "json",
            "level": "ERROR",
            "message": "PaymentGatewayTimeout: Stripe gateway did not respond within 5000ms",
            "attributes": {"order_id": "ord_99812", "amount": 49000, "currency": "KRW"}
        }
    ]

    for log in sample_logs:
        client.index(index=sample_index, body=log)

    print(f" Ingested {len(sample_logs)} sample logs into '{sample_index}'.")
    print("Logccino OpenSearch initialization completed!")

if __name__ == "__main__":
    main()
