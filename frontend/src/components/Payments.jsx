import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Search, Filter, ChevronDown } from 'lucide-react';

export default function Payments() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    api.getPayments({ limit: 100, status: statusFilter || undefined })
      .then(res => { setPayments(res.data); setLoading(false); })
      .catch(console.error);
  }, [statusFilter]);

  const filtered = payments.filter(p => 
    !filter || p.payment_id.toLowerCase().includes(filter.toLowerCase()) || 
    p.order_id.toLowerCase().includes(filter.toLowerCase()) ||
    p.customer_email?.toLowerCase().includes(filter.toLowerCase())
  );

  const statusColors = {
    captured: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    pending: 'bg-yellow-100 text-yellow-800',
    refunded: 'bg-blue-100 text-blue-800',
    authorized: 'bg-purple-100 text-purple-800',
  };

  const settlementColors = {
    settled: 'bg-green-100 text-green-700',
    pending: 'bg-yellow-100 text-yellow-700',
    missing: 'bg-red-100 text-red-700',
    refunded: 'bg-blue-100 text-blue-700',
    not_settled: 'bg-slate-100 text-slate-700',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Payments</h1>
        <p className="text-slate-600 mt-1">All payment transactions</p>
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input
            type="text"
            placeholder="Search by payment ID, order ID, or customer..."
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-razor-500 focus:border-razor-500"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <select
          className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-razor-500"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="captured">Captured</option>
          <option value="failed">Failed</option>
          <option value="pending">Pending</option>
          <option value="refunded">Refunded</option>
          <option value="authorized">Authorized</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Payment ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Order ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Amount</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Customer</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Method</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Settlement</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr><td colSpan="8" className="px-4 py-12 text-center text-slate-500">Loading payments...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan="8" className="px-4 py-12 text-center text-slate-500">No payments found</td></tr>
              ) : (
                filtered.map((p) => (
                  <tr key={p.payment_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm font-mono text-slate-700">{p.payment_id.slice(0, 12)}...</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{p.order_id}</td>
                    <td className="px-4 py-3 text-sm font-semibold">₹{p.amount.toLocaleString('en-IN')}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{p.customer_email || p.customer_name || '-'}</td>
                    <td className="px-4 py-3 text-sm text-slate-700 capitalize">{p.payment_method}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[p.payment_status] || 'bg-slate-100'}`}>{p.payment_status}</span></td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${settlementColors[p.settlement_status] || 'bg-slate-100'}`}>{p.settlement_status}</span></td>
                    <td className="px-4 py-3 text-sm text-slate-600">{new Date(p.created_at).toLocaleDateString('en-IN')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-xs text-slate-500">Showing {filtered.length} of {payments.length} payments • Demo data is synthetic</p>
    </div>
  );
}
