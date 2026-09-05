import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { RefreshCcw, CheckCircle, AlertTriangle, Search } from 'lucide-react';

export default function Reconciliation() {
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const loadData = () => {
    setLoading(true);
    api.getReconciliationBatch(200).then(res => { setBatch(res.data); setLoading(false); }).catch(console.error);
  };

  useEffect(loadData, []);

  const runReconciliation = async () => {
    setRunning(true);
    try {
      await api.runReconciliation();
      loadData();
    } finally { setRunning(false); }
  };

  if (loading) return <div className="text-center py-12">Loading reconciliation data...</div>;
  const s = batch?.statistics;
  const statusStyles = { matched: 'bg-green-100 text-green-800', explainable: 'bg-blue-100 text-blue-800', unresolved: 'bg-yellow-100 text-yellow-800', flagged: 'bg-red-100 text-red-800' };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-slate-900">Reconciliation</h1><p className="text-slate-600 mt-1">Deterministic payment and settlement matching</p></div>
        <button onClick={runReconciliation} disabled={running} className="flex items-center gap-2 bg-razor-600 hover:bg-razor-700 text-white px-4 py-2 rounded-lg disabled:opacity-50">
          <RefreshCcw size={18} className={running ? 'animate-spin' : ''} /> {running ? 'Running...' : 'Run Reconciliation'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Metric title="Records Processed" value={s.total_records} />
        <Metric title="Exact Matches" value={s.matched} color="green" />
        <Metric title="Match Rate" value={`${s.match_rate}%`} color="green" />
        <Metric title="Review Required" value={s.review_required} color="yellow" />
        <Metric title="Unresolved" value={s.unresolved} color="red" />
        <Metric title="Flagged" value={s.flagged} color="red" />
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
        <h3 className="font-semibold mb-4">Batch Financial Summary</h3>
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          <div><span className="text-slate-500">Total Amount Processed</span><p className="text-lg font-bold">₹{s.total_amount.toLocaleString('en-IN')}</p></div>
          <div><span className="text-slate-500">Total Settlement Amount</span><p className="text-lg font-bold text-green-700">₹{s.total_settled.toLocaleString('en-IN')}</p></div>
          <div><span className="text-slate-500">Total Refunds</span><p className="text-lg font-bold text-blue-700">₹{s.total_refunds.toLocaleString('en-IN')}</p></div>
          <div><span className="text-slate-500">Total Fees</span><p className="text-lg font-bold">₹{s.total_fees.toLocaleString('en-IN')}</p></div>
          <div><span className="text-slate-500">Pending Money</span><p className="text-lg font-bold text-yellow-700">₹{s.total_pending.toLocaleString('en-IN')}</p></div>
          <div><span className="text-slate-500">Unresolved Money</span><p className="text-lg font-bold text-red-700">₹{s.total_unresolved.toLocaleString('en-IN')}</p></div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 border-b"><h3 className="font-semibold">Reconciliation Results</h3></div>
        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 sticky top-0"><tr><th className="px-4 py-3 text-left">Payment ID</th><th className="px-4 py-3 text-left">Amount</th><th className="px-4 py-3 text-left">Status</th><th className="px-4 py-3 text-left">Reason</th><th className="px-4 py-3 text-left">Difference</th><th className="px-4 py-3 text-left">Confidence</th><th className="px-4 py-3 text-left">Recommended Action</th></tr></thead>
            <tbody className="divide-y divide-slate-200">
              {batch?.results?.map(r => <tr key={r.payment_id} className="hover:bg-slate-50"><td className="px-4 py-3 font-mono">{r.payment_id.slice(0, 16)}...</td><td className="px-4 py-3">₹{r.amount.toLocaleString('en-IN')}</td><td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[r.status]}`}>{r.status}</span></td><td className="px-4 py-3 text-slate-700 max-w-xs">{r.reason}</td><td className="px-4 py-3">₹{r.discrepancy.toLocaleString('en-IN')}</td><td className="px-4 py-3">{(r.confidence * 100).toFixed(0)}%</td><td className="px-4 py-3 text-slate-600 max-w-xs">{r.recommended_action}</td></tr>)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Metric({ title, value, color = 'slate' }) { const colors = { slate: 'bg-slate-50 border-slate-200', green: 'bg-green-50 border-green-200', yellow: 'bg-yellow-50 border-yellow-200', red: 'bg-red-50 border-red-200' }; return <div className={`p-4 rounded-lg border ${colors[color]}`}><p className="text-xs text-slate-600">{title}</p><p className="text-2xl font-bold mt-1">{value}</p></div>; }
