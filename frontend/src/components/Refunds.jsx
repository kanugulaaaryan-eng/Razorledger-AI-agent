import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { TrendingUp } from 'lucide-react';

export default function Refunds() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getRefunds(100).then(res => { setData(res.data); setLoading(false); }).catch(console.error); }, []);
  if (loading) return <div className="text-center py-12">Loading refunds...</div>;
  if (!data) return <div className="text-center py-12 text-slate-500">No refund data</div>;
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Refunds</h1><p className="text-slate-600 mt-1">Refund tracking and analysis</p></div>
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border"><p className="text-sm text-slate-600">Total Refunds</p><p className="text-2xl font-bold">{data.total_count}</p></div>
        <div className="bg-white p-6 rounded-xl shadow-sm border"><p className="text-sm text-slate-600">Total Amount</p><p className="text-2xl font-bold text-blue-700">₹{data.total_amount.toLocaleString('en-IN')}</p></div>
        <div className="bg-white p-6 rounded-xl shadow-sm border"><p className="text-sm text-slate-600">Avg Refund</p><p className="text-2xl font-bold">₹{data.total_count ? (data.total_amount/data.total_count).toLocaleString('en-IN', {maximumFractionDigits:0}) : 0}</p></div>
      </div>
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50"><tr><th className="px-4 py-3 text-left">Payment ID</th><th className="px-4 py-3 text-left">Order ID</th><th className="px-4 py-3 text-left">Original</th><th className="px-4 py-3 text-left">Refund</th><th className="px-4 py-3 text-left">Status</th><th className="px-4 py-3 text-left">Customer</th><th className="px-4 py-3 text-left">Date</th></tr></thead>
          <tbody className="divide-y divide-slate-200">
            {data.refunds.map(r => <tr key={r.payment_id} className="hover:bg-slate-50">
              <td className="px-4 py-3 font-mono">{r.payment_id.slice(0,12)}...</td>
              <td className="px-4 py-3">{r.order_id}</td>
              <td className="px-4 py-3">₹{r.original_amount.toLocaleString('en-IN')}</td>
              <td className="px-4 py-3 font-semibold text-blue-700">₹{r.refund_amount.toLocaleString('en-IN')}</td>
              <td className="px-4 py-3"><span className="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">{r.refund_status}</span></td>
              <td className="px-4 py-3">{r.customer_email?.split('@')[0]}</td>
              <td className="px-4 py-3">{new Date(r.created_at).toLocaleDateString('en-IN')}</td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </div>
  );
}
