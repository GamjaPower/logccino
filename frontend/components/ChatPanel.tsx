'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Terminal, RotateCcw, Send, Loader2, Lightbulb, Zap, ShieldCheck } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatPanelProps {
  onEvidenceReceived: (logs: any[]) => void;
  onAnalysisDone: () => void;
}

export function ChatPanel({ onEvidenceReceived, onAnalysisDone }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [chips, setChips] = useState<string[]>([]);
  const [currentLogsContext, setCurrentLogsContext] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const extractChips = (text: string) => {
    const regex = /["'](.*?[?？])["']/g;
    let match;
    const questions: string[] = [];
    while ((match = regex.exec(text)) !== null) {
      if (match[1].length > 5 && match[1].length < 45) {
        questions.push(match[1]);
      }
    }
    setChips(questions.slice(0, 3));
  };

  const handleSend = async (questionText?: string) => {
    const q = (questionText || input).trim();
    if (!q || loading) return;

    setInput('');
    const newHistory: ChatMessage[] = [...messages, { role: 'user', content: q }];
    setMessages(newHistory);
    setLoading(true);

    try {
      if (messages.length === 0) {
        // 1단계: Natural Analysis 엔드포인트 호출
        const res = await fetch('/api/v1/analyze/natural', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: q, sample_size: 30 })
        });
        const data = await res.json();

        if (data.status === 'success') {
          const report = data.analysis_report;
          setMessages([...newHistory, { role: 'assistant', content: report }]);
          setCurrentLogsContext(JSON.stringify(data.evidence_logs || []).slice(0, 4000));
          if (data.evidence_logs) onEvidenceReceived(data.evidence_logs);
          extractChips(report);
        } else {
          setMessages([...newHistory, { role: 'assistant', content: '엔터프라이즈 분석 실패: ' + (data.detail || '알 수 없는 에러') }]);
        }
      } else {
        // 후속 대화: Chat Endpoint 호출
        const res = await fetch('/api/v1/analyze/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: q,
            conversation_history: newHistory.map(m => ({ role: m.role, content: m.content })),
            logs_context: currentLogsContext
          })
        });
        const data = await res.json();
        const reply = data.response || '응답을 생성하지 못했습니다.';
        setMessages([...newHistory, { role: 'assistant', content: reply }]);
        extractChips(reply);
      }
    } catch (err: any) {
      setMessages([...newHistory, { role: 'assistant', content: '통신 장애 발생: ' + err.message }]);
    } finally {
      setLoading(false);
      onAnalysisDone();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setChips([]);
    setCurrentLogsContext('');
    onEvidenceReceived([]);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-800 shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">Autonomous SRE Incident Investigation Console</h2>
            <p className="text-[10px] text-slate-400">자연어 심층 원인 진단(RCA), 타임라인 상관분석 및 긴급 조치 가이드</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            LIVE AGENT READY
          </span>
          <button
            onClick={clearChat}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition p-1"
            title="대화 세션 초기화"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Enterprise Incident Presets */}
      <div className="px-5 py-2.5 bg-[#090d16]/70 border-b border-slate-800 flex items-center gap-2 overflow-x-auto">
        <span className="text-[10px] uppercase font-bold text-slate-400 shrink-0 flex items-center gap-1">
          <Zap className="w-3 h-3 text-amber-400" /> 긴급 프리셋:
        </span>
        <button
          onClick={() => handleSend('결제 서비스(payment-service) 타임아웃 및 서킷브레이커 장애 원인 분석해줘')}
          className="text-[11px] bg-slate-850 hover:bg-indigo-600/20 border border-slate-800 hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition shrink-0 font-medium"
        >
          [P1 INCIDENT] 결제 타임아웃 RCA
        </button>
        <button
          onClick={() => handleSend('전사 마이크로서비스 24시간 가용성 및 에러율 집계 요약해줘')}
          className="text-[11px] bg-slate-850 hover:bg-indigo-600/20 border border-slate-800 hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition shrink-0 font-medium"
        >
          [SLA AUDIT] 전사 에러율 매트릭스
        </button>
        <button
          onClick={() => handleSend('notification-service 429 쿼터 초과 및 발송 실패 원인 분석해줘')}
          className="text-[11px] bg-slate-850 hover:bg-indigo-600/20 border border-slate-800 hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition shrink-0 font-medium"
        >
          [ANOMALY] 알림 쿼터 초과 진단
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 p-5 overflow-y-auto space-y-4 max-h-[calc(100vh-370px)]">
        {messages.length === 0 && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 font-mono text-xs font-bold">
              SRE
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl rounded-tl-none p-4 text-xs text-slate-200 leading-relaxed max-w-[90%] shadow-lg">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-2">
                <span className="font-semibold text-white flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Logccino Enterprise Autonomous SRE Agent 초기화 완료
                </span>
                <span className="text-[10px] font-mono text-slate-400">ENGINE: gpt-6-luna</span>
              </div>
              <p className="text-slate-300 mb-2">
                분산 OpenSearch 2.18 클러스터에 인덱싱된 마이크로서비스 로그 및 분산 트레이스를 실시간 모니터링 중입니다.
                장애 현상, 특정 타임아웃, 트레이스 ID 또는 거시적 SLA 상태를 자연어로 질의하시면 엔터프라이즈 SRE 진단 보고서 규격으로 즉시 분석합니다.
              </p>
            </div>
          </div>
        )}

        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}
          >
            {m.role === 'assistant' && (
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 font-mono text-xs font-bold">
                SRE
              </div>
            )}
            <div
              className={`rounded-xl p-4 text-xs leading-relaxed max-w-[90%] shadow-md ${
                m.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-none font-sans'
                  : 'bg-slate-950/90 border border-slate-800 text-slate-200 rounded-tl-none prose prose-invert font-sans'
              }`}
            >
              {m.role === 'assistant' ? (
                <ReactMarkdown>{m.content}</ReactMarkdown>
              ) : (
                <p className="whitespace-pre-wrap">{m.content}</p>
              )}
            </div>
            {m.role === 'user' && (
              <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-xs font-mono text-slate-300 shrink-0 border border-slate-700 font-bold">
                SRE
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 font-mono text-xs font-bold">
              SRE
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl rounded-tl-none px-4 py-3 text-xs text-slate-400 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>분산 OpenSearch 클러스터 쿼리 컴파일 및 심층 원인 진단 수행 중...</span>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Chips */}
      {chips.length > 0 && (
        <div className="px-5 py-2 border-t border-slate-800/60 bg-slate-950/30 flex items-center gap-2 overflow-x-auto">
          <span className="text-[11px] text-slate-400 shrink-0 flex items-center gap-1 font-medium">
            <Lightbulb className="w-3 h-3 text-amber-400" /> 권장 후속 조사:
          </span>
          <div className="flex gap-1.5 shrink-0">
            {chips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip)}
                className="text-[11px] bg-slate-800 hover:bg-indigo-900/40 border border-slate-700 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition whitespace-nowrap font-medium"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="엔터프라이즈 SRE 질의 입력 (예: 'payment-service 타임아웃 및 장애 원인 분석해줘')..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition placeholder:text-slate-500 shadow-inner"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 shadow-md shadow-indigo-600/20"
          >
            <Send className="w-3.5 h-3.5" />
            <span>실행</span>
          </button>
        </form>
      </div>
    </div>
  );
}
