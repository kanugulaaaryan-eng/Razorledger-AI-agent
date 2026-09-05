import React, { useState, useRef, useEffect } from 'react';
import api from '../api/client';
import { Bot, Send, Loader, CheckCircle, AlertCircle, FileText } from 'lucide-react';

const SAMPLE_QUESTIONS = [
  "Where is my money right now?",
  "Why was today's settlement lower?",
  "Show me payments that need attention.",
  "Which payments are still pending?",
  "How much have I lost to refunds?",
  "Forecast my next 7 days.",
  "What should I look at first?",
  "Show me unusual payment activity."
];

export default function AIController() {
  const [messages, setMessages] = useState([{ role: 'assistant', content: "Hello! I'm your AI finance controller. Ask me anything about your payments, settlements, cash position, or exceptions. I'll analyze your actual data and provide grounded insights." }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [evidence, setEvidence] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);

  const send = async (msg) => {
    if (!msg.trim()) return;
    const userMsg = msg.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);
    setEvidence(null);
    try {
      const res = await api.chat(userMsg);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
      setEvidence({ tools: res.data.tools_used, results: res.data.tool_results, audit: res.data.audit_trail });
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error. Please try again." }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex gap-4">
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col bg-white rounded-xl shadow-sm border">
        <div className="p-4 border-b flex items-center gap-2">
          <Bot size={24} className="text-razor-600" />
          <div><h2 className="font-semibold">AI Controller</h2><p className="text-xs text-slate-500">NVIDIA NIM-powered finance agent</p></div>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-4 ${m.role === 'user' ? 'bg-razor-600 text-white' : 'bg-slate-100'}`}>
                <p className="text-sm whitespace-pre-wrap">{m.content}</p>
              </div>
            </div>
          ))}
          {loading && <div className="flex justify-start"><div className="bg-slate-100 rounded-lg p-4 flex items-center gap-2"><Loader size={18} className="animate-spin" /><span className="text-sm">Thinking...</span></div></div>}
        </div>
        <div className="p-4 border-t">
          <div className="flex gap-2 mb-3 flex-wrap">
            {SAMPLE_QUESTIONS.slice(0, 4).map((q, i) => (
              <button key={i} onClick={() => send(q)} className="text-xs px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-full transition-colors">{q}</button>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about your finances..." className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-razor-500" />
            <button type="submit" disabled={loading} className="flex items-center gap-2 bg-razor-600 hover:bg-razor-700 text-white px-4 py-2 rounded-lg disabled:opacity-50">
              <Send size={18} /> Send
            </button>
          </form>
        </div>
      </div>

      {/* Evidence Panel */}
      <div className="w-96 bg-white rounded-xl shadow-sm border flex flex-col">
        <div className="p-4 border-b"><h3 className="font-semibold flex items-center gap-2"><FileText size={18} /> Evidence & Audit</h3></div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!evidence ? (
            <div className="text-center text-slate-500 text-sm py-12">Ask a question to see evidence, tools used, and audit trail</div>
          ) : (
            <>
              <div>
                <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">Tools Used</h4>
                {evidence.tools.length === 0 ? <p className="text-sm text-slate-600">No tools called</p> : (
                  <div className="flex flex-wrap gap-2">{evidence.tools.map((t, i) => <span key={i} className="text-xs px-2 py-1 bg-razor-100 text-razor-700 rounded">{t}</span>)}</div>
                )}
              </div>
              {evidence.results?.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">Tool Results</h4>
                  <div className="space-y-2">
                    {evidence.results.map((r, i) => (
                      <div key={i} className="text-xs bg-slate-50 p-2 rounded border">
                        <p className="font-mono text-slate-700">{r.tool}</p>
                        <pre className="mt-1 text-slate-600 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(r.result, null, 2).slice(0, 500)}{JSON.stringify(r.result, null, 2).length > 500 ? '...' : ''}</pre>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {evidence.audit && (
                <div>
                  <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">Audit Trail</h4>
                  <div className="text-xs space-y-1">
                    <p><span className="text-slate-500">Records inspected:</span> {evidence.audit.records_inspected}</p>
                    <p><span className="text-slate-500">Calculations:</span> {evidence.audit.calculations?.join(', ') || 'None'}</p>
                    <p><span className="text-slate-500">Confidence:</span> {(evidence.audit.confidence * 100).toFixed(0)}%</p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
