import React, { useState, useRef, useEffect } from 'react';
import api from '../api/client';
import { Bot, Send, Loader, X, CheckCircle2, FileText, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const SAMPLE_QUESTIONS = [
  "Where is my money right now?",
  "Why is today's settlement lower?",
  "What should I look at first?",
];

// Maps a tool name to a short, human-readable description of what it checks.
// This is display copy only - the checklist is only ever rendered for tools
// that the backend actually reported running (audit.tools_used), never
// invented ahead of time.
const TOOL_LABELS = {
  get_payment_summary: 'Checking payment summary',
  list_payments: 'Listing payments',
  get_payment_details: 'Looking up payment details',
  get_pending_payments: 'Checking pending payments',
  get_failed_payments: 'Checking failed payments',
  get_refunds: 'Checking refunds',
  get_settlements: 'Checking settlements',
  reconcile_transaction: 'Reconciling transaction',
  reconcile_batch: 'Running batch reconciliation',
  find_exceptions: 'Scanning for exceptions',
  find_duplicates: 'Checking for duplicate payments',
  calculate_cash_position: 'Calculating cash position',
  forecast_cash_flow: 'Forecasting cash flow',
  get_finance_insights: 'Generating finance insights',
  get_daily_finance_brief: 'Building daily brief',
  get_money_flow: 'Tracing money flow',
  get_actions: 'Loading available actions',
};

const SUGGESTED_ROUTES = [
  { match: /exception/i, label: 'Open Exceptions', path: '/exceptions' },
  { match: /reconcil/i, label: 'Open Reconciliation', path: '/reconciliation' },
  { match: /settlement/i, label: 'View Settlements', path: '/settlements' },
  { match: /refund/i, label: 'View Refunds', path: '/refunds' },
  { match: /pending|failed|payment/i, label: 'View Transactions', path: '/payments' },
];

export default function LedgerAI() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hi, I'm Ledger AI. Ask me about your payments, settlements, refunds, or cash position — I'll investigate using your real data." }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastAudit, setLastAudit] = useState(null);
  const [lastTools, setLastTools] = useState([]);
  const scrollRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages, loading]);

  // Allow the app's top nav to open this panel via a global event.
  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener('ledger-ai:open', onOpen);
    return () => window.removeEventListener('ledger-ai:open', onOpen);
  }, []);

  // Allow the Overview's AI prompt bar to open the panel and ask directly.
  const ask = (q) => {
    setOpen(true);
    send(q);
  };
  useEffect(() => {
    const onAsk = (e) => ask(e.detail);
    window.addEventListener('ledger-ai:ask', onAsk);
    return () => window.removeEventListener('ledger-ai:ask', onAsk);
  }, []);

  const send = async (msg) => {
    if (!msg.trim() || loading) return;
    const userMsg = msg.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);
    setLastAudit(null);
    setLastTools([]);
    try {
      const res = await api.chat(userMsg);
      setLastTools(res.data.tools_used || []);
      setLastAudit(res.data.audit_trail || null);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response, tools: res.data.tools_used }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "I couldn't reach the backend just now. Please check that the API server is running and try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = SUGGESTED_ROUTES.filter(r => messages.slice(-1)[0]?.content?.match(r.match)).slice(0, 2);

  return (
    <>
      {/* Floating launcher */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-razor-600 hover:bg-razor-700 text-white px-4 py-3 rounded-full shadow-lg transition-transform hover:scale-105"
          aria-label="Open Ledger AI"
        >
          <Bot size={20} /> <span className="text-sm font-medium hidden sm:inline">Ledger AI</span>
        </button>
      )}

      {/* Slide-over panel */}
      <div className={`fixed inset-0 z-50 transition-opacity ${open ? 'pointer-events-auto' : 'pointer-events-none'}`}>
        <div
          onClick={() => setOpen(false)}
          className={`absolute inset-0 bg-black/30 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`}
        />
        <div className={`absolute top-0 right-0 h-full w-full sm:w-[420px] bg-white shadow-2xl flex flex-col transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
          <div className="p-4 border-b flex items-center justify-between bg-slate-900 text-white">
            <div className="flex items-center gap-2">
              <Bot size={20} />
              <div>
                <h2 className="font-semibold text-sm leading-tight">Ledger AI</h2>
                <p className="text-[11px] text-slate-300 leading-tight">Real-time financial investigation</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1 hover:bg-slate-800 rounded"><X size={18} /></button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-lg p-3 text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-razor-600 text-white' : 'bg-slate-100 text-slate-800'}`}>
                  {m.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 rounded-lg p-3 flex items-center gap-2 text-sm text-slate-600">
                  <Loader size={16} className="animate-spin" /> Analyzing your financial data...
                </div>
              </div>
            )}

            {!loading && lastTools.length > 0 && (
              <div className="bg-slate-50 border rounded-lg p-3">
                <p className="text-[11px] font-semibold uppercase text-slate-500 mb-2">Agent activity</p>
                <div className="space-y-1">
                  {lastTools.map((t, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-slate-700">
                      <CheckCircle2 size={14} className="text-green-600 flex-shrink-0" />
                      {TOOL_LABELS[t] || t}
                    </div>
                  ))}
                </div>
                {lastAudit && (
                  <div className="mt-3 pt-3 border-t flex items-center justify-between text-[11px] text-slate-500">
                    <span className="flex items-center gap-1"><FileText size={12} /> Logged to audit trail</span>
                    <span>{Math.round((lastAudit.confidence || 0) * 100)}% confidence</span>
                  </div>
                )}
                {suggestions.length > 0 && (
                  <div className="mt-3 pt-3 border-t flex flex-wrap gap-2">
                    {suggestions.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => { setOpen(false); navigate(s.path); }}
                        className="flex items-center gap-1 text-xs px-2 py-1 bg-white border border-slate-300 rounded-md hover:bg-slate-100"
                      >
                        {s.label} <ExternalLink size={11} />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="p-3 border-t">
            <div className="flex gap-2 mb-2 flex-wrap">
              {SAMPLE_QUESTIONS.map((q, i) => (
                <button key={i} onClick={() => send(q)} className="text-[11px] px-2 py-1 bg-slate-100 hover:bg-slate-200 rounded-full">{q}</button>
              ))}
            </div>
            <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Ledger AI..."
                className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-razor-500"
              />
              <button type="submit" disabled={loading} className="flex items-center justify-center bg-razor-600 hover:bg-razor-700 text-white w-10 h-10 rounded-lg disabled:opacity-50">
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
