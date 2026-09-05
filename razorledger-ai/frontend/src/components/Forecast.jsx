import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

export default function Forecast() {
  const [forecast7, setForecast7] = useState(null);
  const [forecast30, setForecast30] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api.getCashForecast(7), api.getCashForecast(30)]).then(([r7, r30]) => {
      setForecast7(r7.data); setForecast30(r30.data); setLoading(false);
    }).catch(console.error);
  }, []);
  if (loading) return <div className="text-center py-12">Loading forecast...</div>;
  const data7 = forecast7?.forecast?.map(d => ({...d, date: d.date.slice(5)})) || [];
  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-slate-900">Cash Flow Forecast</h1><p className="text-slate-600 mt-1">7-day and 30-day projections based on historical patterns</p></div>
      <div className="grid md:grid-cols-3 gap-4">
        <ForecastCard title="7-Day Expected" value={forecast7?.total_expected} low={forecast7?.confidence_range?.low} high={forecast7?.confidence_range?.high} />
        <ForecastCard title="30-Day Expected" value={forecast30?.total_expected} low={forecast30?.confidence_range?.low} high={forecast30?.confidence_range?.high} />
        <div className="bg-white p-6 rounded-xl shadow-sm border"><p className="text-sm text-slate-600">Methodology</p><p className="text-xs mt-2 text-slate-500">{forecast7?.methodology}</p></div>
      </div>
      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="font-semibold mb-4">7-Day Forecast</h3>
        <div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={data7}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="date" /><YAxis tickFormatter={(v)=>`₹${(v/1000).toFixed(0)}K`} /><Tooltip formatter={(v)=>`₹${v.toLocaleString('en-IN')}`} /><Line type="monotone" dataKey="expected" stroke="#0ea5e9" strokeWidth={2} /><Line type="monotone" dataKey="confidence_low" stroke="#94a3b8" strokeDasharray="3 3" dot={false} /><Line type="monotone" dataKey="confidence_high" stroke="#94a3b8" strokeDasharray="3 3" dot={false} /></LineChart></ResponsiveContainer></div>
      </div>
    </div>
  );
}

function ForecastCard({ title, value, low, high }) {
  return <div className="bg-white p-6 rounded-xl shadow-sm border"><p className="text-sm text-slate-600">{title}</p><p className="text-2xl font-bold mt-2">₹{value?.toLocaleString('en-IN')}</p><p className="text-xs text-slate-500 mt-1">Range: ₹{low?.toLocaleString('en-IN')} - ₹{high?.toLocaleString('en-IN')}</p></div>;
}
