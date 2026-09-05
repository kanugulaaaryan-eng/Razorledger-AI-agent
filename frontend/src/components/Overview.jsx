import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/client';
import { AlertTriangle, Link as LinkIcon, Sparkles, ArrowUpRight, MoreHorizontal, Calendar, ChevronDown, ArrowRight } from 'lucide-react';

/* ----------------------------- helpers ----------------------------- */

function inr(n) {
  return `₹${(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}
function inr2(n) {
  return `₹${(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

// Compact count: 11 -> "11", 12000 -> "12.0k" (avoids misleading "0.0k").
function kFormat(v) {
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v);
}

/* A horizontal "funnel" bar with the angled parallelogram look from the ref. */
function FunnelBar({ label, value, max, highlight, color, stripes, onClick }) {
  const pct = max > 0 ? Math.max(6, (value / max) * 100) : 6;
  const skew = 'polygon(14px 0, 100% 0, calc(100% - 14px) 100%, 0 100%)';
  return (
    <div className="flex items-center gap-3">
      <div className="w-32 shrink-0 text-right">
        <p className={`text-[13px] font-semibold ${highlight ? 'text-slate-900' : 'text-slate-500'}`}>{label}</p>
        <p className={`text-sm font-extrabold ${highlight ? 'text-slate-900' : 'text-slate-400'}`}>
          {value.toLocaleString('en-IN')}
        </p>
      </div>
      <div className="flex-1 h-9">
        <button
          onClick={onClick}
          className={`h-full w-full block rounded transition-transform hover:scale-x-[1.01] hover:shadow ${stripes} ${color}`}
          style={{ clipPath: skew, opacity: highlight ? 1 : 0.85 }}
          title={`${label}: ${value.toLocaleString('en-IN')}`}
        />
      </div>
    </div>
  );
}

/* A column chart made of stacked dots, like the reference dot-matrix. */
function DotMatrix({ values, peakLabel }) {
  const max = Math.max(...values, 1);
  const HEIGHT = 10;
  const peakIdx = values.indexOf(Math.max(...values));
  return (
    <div className="flex items-end justify-between gap-2 h-24">
      {values.map((v, i) => {
        const n = Math.max(1, Math.round((v / max) * HEIGHT));
        const isPeak = i === peakIdx;
        const dots = Array.from({ length: n });
        return (
          <div key={i} className="flex flex-col items-center flex-1 gap-0.5 relative">
            {isPeak && peakLabel && (
              <span className="absolute -top-5 left-1/2 -translate-x-1/2 bg-white text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow ring-1 ring-slate-100 whitespace-nowrap">
                {peakLabel}
              </span>
            )}
            {dots.map((_, d) => (
              <span
                key={d}
                className={`w-[6px] h-[6px] rounded-full ${
                  isPeak ? 'bg-slate-900' : 'bg-slate-300'
                }`}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}

/* A soft step/area line from the forecast series. */
function StepChart({ data, color }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map((d) => d.expected || 0), 1);
  const peakIdx = data.reduce((bi, d, i) => (d.expected > data[bi].expected ? i : bi), 0);
  const peakVal = data[peakIdx].expected;
  const w = 640, h = 160, px = 6;
  const step = w / data.length;
  const y = (v) => h - (v / max) * (h - px);
  const pts = data.map((d, i) => ({ x: i * step, y: y(d.expected || 0) }));
  // build step path (horizontal then vertical)
  let d = `M0,${pts[0].y} `;
  for (let i = 1; i < pts.length; i++) {
    d += `H${pts[i].x} V${pts[i].y} `;
  }
  d += `V${h} H0 Z`;
  let line = `M0,${pts[0].y} `;
  for (let i = 1; i < pts.length; i++) line += `H${pts[i].x} V${pts[i].y} `;
  const labels = data.map((d) => d.date);
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-32" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`stepFill-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={d} fill={`url(#stepFill-${color})`} />
        <path d={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
        <circle
          cx={pts[peakIdx].x}
          cy={pts[peakIdx].y}
          r="5"
          fill="#fff"
          stroke={color}
          strokeWidth="3"
        />
      </svg>
      {/* peak bubble */}
      <span
        className="absolute -top-1 bg-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow ring-1 ring-slate-100"
        style={{ left: `${(peakIdx / data.length) * 100}%`, transform: 'translateX(-50%)' }}
      >
        {inr2(peakVal)}
      </span>
      <div className="flex justify-between mt-1 text-[10px] text-slate-400">
        {labels.map((l, i) => (
          <span key={i}>{l}</span>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------- Overview ----------------------------- */

export default function Overview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forecast, setForecast] = useState(null);
  const [aiInput, setAiInput] = useState('');

  const load = () => {
    setLoading(true);
    Promise.all([api.getOverview(), api.getCashForecast(7)])
      .then(([o, f]) => { setData(o.data); setForecast(f.data); setLoading(false); })
      .catch((e) => { console.error(e); setLoading(false); });
  };

  useEffect(load, []);

  const funnel = useMemo(() => {
    if (!data) return [];
    const s = data.payment_summary;
    return [
      { label: 'Initiated Payments', value: s.total_payments, key: 'initiated' },
      { label: 'Successful Payments', value: s.successful, key: 'successful', highlight: true },
      { label: 'Pending Payments', value: s.pending, key: 'pending' },
      { label: 'Refunded Payments', value: s.refunded, key: 'refunded' },
      { label: 'Failed Payments', value: s.failed, key: 'failed' },
    ];
  }, [data]);

  const gross = useMemo(() => {
    if (!data) return [];
    const c = data.cash_position;
    return [
      { label: 'Settled Cash', value: c.settled_cash, stripe: 'stripes-green' },
      { label: 'Pending Settlement', value: c.pending_settlement, stripe: 'stripes-blue' },
      { label: 'Refunds Issued', value: c.refunded, stripe: 'stripes-pink' },
      { label: 'Processing Fees', value: c.fees_paid, stripe: 'stripes-teal' },
      { label: 'Unresolved', value: c.unresolved, stripe: 'stripes-blue' },
    ];
  }, [data]);

  const forecastDots = useMemo(() => (forecast?.forecast || []).slice(0, 7).map((d) => d.expected || 0), [forecast]);
  const forecastLabels = useMemo(() => (forecast?.forecast || []).slice(0, 7).map((d) => d.date.slice(5)), [forecast]);

  const reconDots = useMemo(() => {
    if (!data) return [];
    const r = data.reconciliation_stats;
    return [r.matched, r.explainable, r.unresolved, r.flagged];
  }, [data]);

  const sendToLedger = (q) => {
    if (!q.trim()) return;
    window.dispatchEvent(new CustomEvent('ledger-ai:ask', { detail: q }));
    setAiInput('');
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-slate-400 gap-3">
        <div className="w-8 h-8 border-[3px] border-slate-200 border-t-razor-600 rounded-full animate-spin" />
        <p className="text-sm">Loading your finance control room...</p>
      </div>
    );
  }
  if (!data) return <div className="text-center py-24 text-red-600">Failed to load data. Is the backend running?</div>;

  const { payment_summary: ps, reconciliation_stats: rs, cash_position: cp, exceptions_count, daily_brief } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl lg:text-[26px] font-extrabold tracking-tight">Overview</h1>
          <span className="chip-btn"><LinkIcon size={15} /></span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button className="flex items-center gap-1.5 text-[12px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">
            <Calendar size={13} /> Jan 01 - Jul 31 <ChevronDown size={13} />
          </button>
          <span className="text-[11px] text-slate-400">compared to</span>
          <button className="flex items-center gap-1.5 text-[12px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">
            <Calendar size={13} /> Aug 01 - Dec 31 <ChevronDown size={13} />
          </button>
          <button className="flex items-center gap-1.5 text-[12px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">
            Daily <ChevronDown size={13} />
          </button>
          <button onClick={load} className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-700 border border-slate-300 hover:bg-slate-50 px-3 py-1.5 rounded-full">
            Add widget <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* Row 1: Payments pipeline + Gross volume */}
      <div className="grid lg:grid-cols-3 gap-5">
        {/* Payments funnel */}
        <div className="lg:col-span-2 rl-card rl-card-hover p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-bold">Payments Pipeline</h2>
            <button className="chip-btn"><MoreHorizontal size={18} /></button>
          </div>
          <div className="grid grid-cols-5 gap-2 mb-4">
            {funnel.map((f) => (
              <div key={f.key} className="text-center">
                <p className={`text-[11px] font-medium ${f.highlight ? 'text-slate-700' : 'text-slate-400'}`}>
                  {f.label.replace(' Payments', '')}
                </p>
                <p className={`text-lg font-extrabold ${f.highlight ? 'text-slate-900' : 'text-slate-400'}`}>
                  {kFormat(f.value)}
                </p>
              </div>
            ))}
          </div>
          <div className="space-y-3">
            {funnel.map((f) => (
              <FunnelBar
                key={f.key}
                label={f.label}
                value={f.value}
                max={funnel[0].value}
                highlight={f.highlight}
                color={f.highlight ? 'bg-blue-600' : 'bg-blue-100'}
                stripes={f.highlight ? '' : 'stripes-blue'}
              />
            ))}
          </div>
          <p className="text-[11px] text-slate-400 mt-3">
            Conversion to successful: <span className="font-semibold text-slate-600">{ps.success_rate}%</span> · drop-off from initiation {(100 - ps.success_rate).toFixed(1)}%
          </p>

          {/* Integrated AI prompt */}
          <div className="mt-5 rounded-xl bg-gradient-to-b from-blue-50 to-white ring-1 ring-blue-100 p-3.5">
            <p className="text-[12px] text-slate-600 mb-2 flex items-center gap-1.5">
              <Sparkles size={13} className="text-blue-600" /> What would you like to explore next?
            </p>
            <form onSubmit={(e) => { e.preventDefault(); sendToLedger(aiInput); }} className="flex items-center gap-2 bg-white rounded-full border border-slate-200 px-3 py-1.5 shadow-sm focus-within:ring-2 focus-within:ring-blue-500">
              <input
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                placeholder="Ask Ledger AI to investigate your finance..."
                className="flex-1 text-[13px] outline-none placeholder:text-slate-400 bg-transparent"
              />
              <button type="submit" className="flex items-center justify-center w-7 h-7 rounded-full bg-blue-600 text-white hover:bg-blue-700" aria-label="Ask">
                <ArrowRight size={15} />
              </button>
            </form>
          </div>
        </div>

        {/* Gross volume */}
        <div className="rl-card rl-card-hover p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-[15px] font-bold">Gross Volume</h2>
            <button className="chip-btn"><MoreHorizontal size={18} /></button>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-extrabold tracking-tight">{inr2(cp.captured_total)}</span>
            <span className="flex items-center gap-1 text-[12px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
              <ArrowUpRight size={13} /> {ps.success_rate}%
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5 mb-5">Total collected volume</p>
          <div className="space-y-4">
            {gross.map((g) => {
              const pct = cp.captured_total > 0 ? Math.max(4, (g.value / cp.captured_total) * 100) : 4;
              return (
                <div key={g.label}>
                  <div className="flex justify-between text-[12px] mb-1.5">
                    <span className="text-slate-500">{g.label}</span>
                    <span className="font-bold text-slate-800">{inr2(g.value)}</span>
                  </div>
                  <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${g.stripe} bg-gradient-to-b from-white/30 to-transparent`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Row 2: Forecast + Reconciliation + Insights */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Settlement forecast (step chart) */}
        <div className="rl-card rl-card-hover p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-bold">Settlement Forecast</h2>
            <button className="chip-btn"><MoreHorizontal size={18} /></button>
          </div>
          <StepChart data={forecast?.forecast || []} color="#ec4899" />
          <p className="text-[11px] text-slate-400 mt-3 text-center">
            Next 7 days expected <span className="font-semibold text-slate-600">{inr2(forecast?.total_expected)}</span>
          </p>
        </div>

        {/* Transactions & Reconciliation dot-matrix */}
        <div className="rl-card rl-card-hover p-5 flex flex-col gap-5">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-[13px] font-bold text-slate-700">Cash Flow Forecast</h3>
              <button className="chip-btn"><MoreHorizontal size={16} /></button>
            </div>
            <p className="text-2xl font-extrabold">{inr2(forecast?.total_expected)}</p>
            <div className="mt-4">
              <DotMatrix values={forecastDots} peakLabel="Peak" />
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-slate-400">
              {forecastLabels.map((l, i) => <span key={i}>{l}</span>)}
            </div>
            <p className="text-[11px] text-slate-400 mt-1 text-right">
              vs last period <span className="font-bold text-emerald-600">+{Math.round(((forecast?.total_expected || 0) / 1000))}k</span>
            </p>
          </div>
          <div className="border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-[13px] font-bold text-slate-700">Reconciliation</h3>
            </div>
            <p className="text-2xl font-extrabold">{rs.match_rate}%</p>
            <div className="mt-4">
              <DotMatrix values={reconDots} peakLabel="Top" />
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-slate-400">
              <span>Matched</span><span>Explainable</span><span>Unresolved</span><span>Flagged</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 text-right">
              <span className="font-bold text-slate-700">{rs.matched}</span> matched of {rs.total_records}
            </p>
          </div>
        </div>

        {/* Insights gradient card */}
        <div className="md:col-span-2 lg:col-span-1 relative overflow-hidden rounded-2xl bg-gradient-to-tr from-teal-600 via-cyan-500 to-orange-400 text-white p-6 shadow-xl">
          <span className="absolute -right-6 -top-8 text-[160px] leading-none text-white/10 font-black select-none">›</span>
          <span className="absolute right-3 top-3 flex items-center gap-1 text-[11px] font-semibold bg-white/20 backdrop-blur px-2.5 py-1 rounded-full">
            <Sparkles size={12} /> Insights
          </span>
          <p className="mt-8 text-5xl font-extrabold tracking-tight">{rs.match_rate}%</p>
          <h3 className="text-lg font-bold leading-snug mt-2 max-w-[90%]">
            {daily_brief.top_priorities?.[0]?.replace(/^(CRITICAL|HIGH|MEDIUM|LOW):\s*/i, '') || `${exceptions_count} items need attention`}
          </h3>
          <p className="text-[13px] text-white/85 mt-2 max-w-[92%]">
            {exceptions_count} open exceptions · {ps.failed} failed payments · reconciliation health at {rs.match_rate}%
          </p>
          <div className="mt-5">
            <div className="flex justify-between text-[11px] font-medium text-white/90 mb-1.5">
              <span>Attention health</span><span>{Math.round(rs.match_rate)}%</span>
            </div>
            <div className="h-2.5 bg-white/25 rounded-full overflow-hidden">
              <div className="h-full bg-slate-900 rounded-full" style={{ width: `${Math.max(4, rs.match_rate)}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Bottom strip: exceptions summary */}
      <div className="rl-card p-5 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <span className="w-11 h-11 rounded-xl bg-red-50 text-red-600 flex items-center justify-center">
            <AlertTriangle size={20} />
          </span>
          <div>
            <p className="text-[15px] font-bold">{exceptions_count} open exceptions</p>
            <p className="text-[12px] text-slate-500">from today's brief · {daily_brief.top_priorities.length} priorities</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 sm:ml-auto">
          {daily_brief.top_priorities.slice(0, 3).map((p, i) => (
            <span key={i} className="text-[11px] px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">{p.split(':')[1] || p}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
