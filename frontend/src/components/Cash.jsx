import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { DollarSign } from 'lucide-react';

export default function Cash() {
  const [position, setPosition] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getCashPosition().then(res => { setPosition(res.data); setLoading(false); }).catch(console.error); }, []);
  if (loading) return <div className="text-center py-12">Loading cash position...</div>;
  if (!position) return <div className="text-center py-12 text-slate-500">No data</div>;
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Cash Position</h1><p className="text-slate-600 mt-1">Current cash availability and breakdown</p></div>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <CashCard title="Captured Total" value={position.captured_total} />
        <CashCard title="Available Cash" value={position.available_cash} highlight />
        <CashCard title="Pending Settlement" value={position.pending_settlement} warning />
        <CashCard title="Unresolved" value={position.unresolved} danger />
      </div>
      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="font-semibold mb-4">Cash Flow Breakdown</h3>
        <div className="space-y-3">
          <CashRow label="Settled Cash" value={position.settled_cash} total={position.captured_total} color="bg-green-500" />
          <CashRow label="Pending Settlement" value={position.pending_settlement} total={position.captured_total} color="bg-yellow-500" />
          <CashRow label="Refunded" value={position.refunded} total={position.captured_total} color="bg-blue-500" />
          <CashRow label="Fees Paid" value={position.fees_paid} total={position.captured_total} color="bg-red-500" />
          <CashRow label="Unresolved" value={position.unresolved} total={position.captured_total} color="bg-orange-500" />
        </div>
      </div>
    </div>
  );
}

function CashCard({ title, value, highlight, warning, danger }) {
  const colors = highlight ? 'bg-green-50 border-green-200' : warning ? 'bg-yellow-50 border-yellow-200' : danger ? 'bg-red-50 border-red-200' : 'bg-slate-50 border-slate-200';
  return <div className={`p-6 rounded-xl border ${colors}`}><p className="text-sm text-slate-600">{title}</p><p className="text-2xl font-bold mt-2">₹{value.toLocaleString('en-IN')}</p></div>;
}

function CashRow({ label, value, total, color }) {
  const pct = total > 0 ? (value / total * 100) : 0;
  return <div><div className="flex justify-between text-sm mb-1"><span>{label}</span><span>₹{value.toLocaleString('en-IN')} ({pct.toFixed(1)}%)</span></div><div className="h-2 bg-slate-100 rounded-full overflow-hidden"><div className={`h-full ${color}`} style={{width: `${pct}%`}} /></div></div>;
}
