import React, { useState, useEffect } from 'react';
import api from '../api/client';

export default function Settlements() {
  const [settlements, setSettlements] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getSettlements(100).then(res => { setSettlements(res.data); setLoading(false); }).catch(console.error); }, []);
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Settlements</h1><p className="text-slate-600 mt-1">Settlement records and discrepancies</p></div>
      {loading ? <div className="text-center py-12">Loading settlements...</div> : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left">Settlement ID</th><th className="px-4 py-3 text-left">Expected</th><th className="px-4 py-3 text-left">Actual</th><th className="px-4 py-3 text-left">Discrepancy</th><th className="px-4 py-3 text-left">Payments</th><th className="px-4 py-3 text-left">Fees</th><th className="px-4 py-3 text-left">Date</th><th className="px-4 py-3 text-left">Status</th></tr></thead>
            <tbody className="divide-y divide-slate-200">
              {settlements.map(s => <tr key={s.settlement_id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-mono">{s.settlement_id}</td>
                <td className="px-4 py-3">₹{s.expected_amount.toLocaleString('en-IN')}</td>
                <td className="px-4 py-3">₹{s.actual_amount.toLocaleString('en-IN')}</td>
                <td className={`px-4 py-3 font-semibold ${s.discrepancy < 0 ? 'text-red-700' : s.discrepancy > 0 ? 'text-green-700' : 'text-slate-700'}`}>{s.discrepancy !== 0 ? `₹${s.discrepancy.toLocaleString('en-IN')}` : '-'}</td>
                <td className="px-4 py-3">{s.payment_count}</td>
                <td className="px-4 py-3">₹{s.fee_total.toLocaleString('en-IN')}</td>
                <td className="px-4 py-3">{new Date(s.processed_at).toLocaleDateString('en-IN')}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs ${s.status === 'processed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>{s.status}</span></td>
              </tr>)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
