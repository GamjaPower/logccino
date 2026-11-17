'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, RotateCcw, Send, Loader2, Lightbulb } from 'lucide-react';
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
          setMessages([...newHistory, { role: 'assistant', content: '분석 중 오류 발생: ' + (data.detail || '알 수 없는 에러') }]);
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
      setMessages([...newHistory, { role: 'assistant', content: '서버 통신 실패: ' + err.message }]);
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
    <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-semibold text-white">AI 자연어 로그 분석가 (Chat UI)</h2>
        </div>
        <button
          onClick={clearChat}
          className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition"
        >
          <RotateCcw className="w-3 h-3" /> 초기화
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div ref={scrollRef} className="flex-1 p-5 overflow-y-auto space-y-4 max-h-[calc(100vh-290px)]">
        {messages.length === 0 && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-600/30 border border-purple-500/40 flex items-center justify-center text-sm shrink-0">
              ☕
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl rounded-tl-none p-4 text-sm text-slate-200 leading-relaxed max-w-[90%]">
              <p className="font-semibold text-white mb-1">Logccino AI 로그 분석가에 오신 것을 환영합니다.</p>
              <p className="text-xs text-slate-300 mb-3">
                수백만 건의 분산 OpenSearch 로그를 사람과 대화하듯 질의하여 이상치 진단, 원인 분석, 타임라인을 파악하세요.
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <button
                  onClick={() => handleSend('어제 결제 모듈에서 발생한 타임아웃 에러 원인 분석해줘')}
                  className="text-xs bg-slate-800 hover:bg-purple-900/40 border border-slate-700 text-slate-300 hover:text-purple-300 px-2.5 py-1 rounded-full transition"
                >
                  💳 결제 타임아웃 원인 분석
                </button>
                <button
                  onClick={() => handleSend('서비스별 24시간 로그 볼륨과 에러율 통계 표로 보여줘')}
                  className="text-xs bg-slate-800 hover:bg-purple-900/40 border border-slate-700 text-slate-300 hover:text-purple-300 px-2.5 py-1 rounded-full transition"
                >
                  📊 서비스별 에러율 통계
                </button>
                <button
                  onClick={() => handleSend('notification-service에서 발생하는 에러 패턴 알려줘')}
                  className="text-xs bg-slate-800 hover:bg-purple-900/40 border border-slate-700 text-slate-300 hover:text-purple-300 px-2.5 py-1 rounded-full transition"
                >
                  🔔 알림 서비스 에러 진단
                </button>
              </div>
            </div>
          </div>
        )}

        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}
          >
            {m.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-purple-600/30 border border-purple-500/40 flex items-center justify-center text-sm shrink-0">
                🤖
              </div>
            )}
            <div
              className={`rounded-2xl p-4 text-sm leading-relaxed max-w-[85%] ${
                m.role === 'user'
                  ? 'bg-purple-600 text-white rounded-tr-none shadow-md'
                  : 'bg-slate-950/80 border border-slate-800 text-slate-200 rounded-tl-none prose prose-invert prose-sm'
              }`}
            >
              {m.role === 'assistant' ? (
                <ReactMarkdown>{m.content}</ReactMarkdown>
              ) : (
                <p className="whitespace-pre-wrap">{m.content}</p>
              )}
            </div>
            {m.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-xs shrink-0">
                👤
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-600/30 border border-purple-500/40 flex items-center justify-center text-sm shrink-0">
              🤖
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl rounded-tl-none px-4 py-3 text-sm text-slate-400 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              <span>OpenSearch 분산 쿼리 및 로그 분석 수행 중...</span>
            </div>
          </div>
        )}
      </div>

      {/* Suggested Chips */}
      {chips.length > 0 && (
        <div className="px-5 py-2 border-t border-slate-800/60 bg-slate-950/30 flex items-center gap-2 overflow-x-auto">
          <span className="text-[11px] text-slate-400 shrink-0 flex items-center gap-1">
            <Lightbulb className="w-3 h-3 text-amber-400" /> 추천 질문:
          </span>
          <div className="flex gap-1.5 shrink-0">
            {chips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip)}
                className="text-xs bg-slate-800 hover:bg-purple-900/40 border border-slate-700 text-slate-300 hover:text-purple-300 px-2.5 py-0.5 rounded-full transition whitespace-nowrap"
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
            placeholder="자연어로 로그 질문 입력 (예: 'auth-service 로그인 실패 원인 분석해줘')..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500 transition placeholder:text-slate-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>전송</span>
          </button>
        </form>
      </div>
    </div>
  );
}
