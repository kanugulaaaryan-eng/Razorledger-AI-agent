import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';

export default function Exceptions() {
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.getExceptions().then(res => { setExceptions(res.data); setLoading(false); }).catch(console.error); }, []);

  const severityIcon = { critical: AlertTriangle, high: AlertTriangle, medium: AlertCircle, low: Info };
  const severityColors = { critical: 'bg-red-100 border-red-300 text-red-800', high: 'bg-orange-100 border-orange-300 text-orange-800', medium: 'bg-yellow-100 border-yellow-300 text-yellow-800', low: 'bg-blue-100 border-blue-300 text-blue-800' };

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Exception Center</h1><p className="text-slate-600 mt-1">Transactions requiring attention, prioritized by severity</p></div>
      {loading ? <div className="text-center py-12">Loading exceptions...</div> : exceptions.length === 0 ? <div className="text-center py-12 text-slate-500">No open exceptions</div> : (
        <div className="space-y-4">
          {exceptions.map(exc => { const Icon = severityIcon[exc.severity] || Info; return (
            <div key={exc.id} className={`p-4 rounded-lg border-l-4 ${severityColors[exc.severity]}`}>
              <div className="flex items-start gap-3">
                <Icon size={24} className="mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{exc.exception_type.replace('_', ' ').toUpperCase()}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-white/50">{exc.severity.toUpperCase()}</span>
                  </div>
                  <p className="mt-1 text-sm">{exc.reason}</p>
                  <div className="mt-2 text-xs flex flex-wrap gap-4">
                    <span>Payment: {exc.payment_id?.slice(0,12) || '-'}</span>
                    <span>Amount: ₹{exc.amount.toLocaleString('en-IN')}</span>
                    <span>Confidence: {(exc.confidence*100).toFixed(0)}%</span>
                    <span>{new Date(exc.created_at).toLocaleDateString('en-IN')}</span>
                  </div>
                  {exc.recommended_action && <p className="mt-2 text-sm font-medium">Action: {exc.recommended_action}</p>}
                </div>
              </div>
            </div>
          );})}
        </div>
      )}
    </div>
  );
}
