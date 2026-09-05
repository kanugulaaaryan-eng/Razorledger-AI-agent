import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Lightbulb, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';

export default function Insights() {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.getInsights().then(res => { setInsights(res.data); setLoading(false); }).catch(console.error); }, []);
  const iconMap = { positive: CheckCircle, warning: AlertTriangle, alert: AlertTriangle, info: Lightbulb };
  const colorMap = { positive: 'bg-green-50 border-green-200 text-green-800', warning: 'bg-yellow-50 border-yellow-200 text-yellow-800', alert: 'bg-red-50 border-red-200 text-red-800', info: 'bg-blue-50 border-blue-200 text-blue-800' };
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Business Insights</h1><p className="text-slate-600 mt-1">AI-identified patterns from your payment data</p></div>
      {loading ? <div className="text-center py-12">Loading insights...</div> : insights.length === 0 ? <div className="text-center py-12 text-slate-500">No insights available</div> : (
        <div className="grid md:grid-cols-2 gap-4">
          {insights.map((i, idx) => { const Icon = iconMap[i.type] || Lightbulb; return (
            <div key={idx} className={`p-6 rounded-xl border ${colorMap[i.type]}`}>
              <div className="flex items-start gap-3">
                <Icon size={24} className="mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2"><span className="font-semibold">{i.title}</span><span className="text-xs px-2 py-0.5 rounded bg-white/50 uppercase">{i.impact} impact</span></div>
                  <p className="mt-2 text-sm">{i.description}</p>
                  <p className="mt-2 text-xs opacity-70">Metric: {i.metric}</p>
                </div>
              </div>
            </div>
          );})}
        </div>
      )}
    </div>
  );
}
