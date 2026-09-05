import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { FileText } from 'lucide-react';

export default function Audit() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getAudit(100).then(res => { setLogs(res.data); setLoading(false); }).catch(console.error); }, []);
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Audit Trail</h1><p className="text-slate-600 mt-1">Complete history of AI interactions and tool usage</p></div>
      {loading ? <div className="text-center py-12">Loading audit logs...</div> : logs.length === 0 ? <div className="text-center py-12 text-slate-500">No audit logs yet</div> : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left">Time</th><th className="px-4 py-3 text-left">Question</th><th className="px-4 py-3 text-left">Tools</th><th className="px-4 py-3 text-left">Records</th><th className="px-4 py-3 text-left">Confidence</th><th className="px-4 py-3 text-left">Conclusion</th></tr></thead>
            <tbody className="divide-y divide-slate-200">
              {logs.map(log => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-600">{new Date(log.created_at).toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 max-w-xs truncate">{log.question}</td>
                  <td className="px-4 py-3"><div className="flex gap-1 flex-wrap">{log.tools_used?.map((t,i) => <span key={i} className="text-xs px-2 py-0.5 bg-slate-100 rounded">{t}</span>)}</div></td>
                  <td className="px-4 py-3">{log.records_inspected}</td>
                  <td className="px-4 py-3">{(log.confidence * 100).toFixed(0)}%</td>
                  <td className="px-4 py-3 max-w-xs truncate text-slate-700">{log.conclusion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
