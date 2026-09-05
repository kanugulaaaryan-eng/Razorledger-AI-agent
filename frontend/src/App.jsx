import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, CreditCard, RefreshCcw, AlertTriangle, DollarSign,
  TrendingUp, Lightbulb, Bot, FileText, Settings, Bell, Search,
  ChevronRight, ArrowDownUp, Wallet
} from 'lucide-react';
import Overview from './components/Overview';
import Payments from './components/Payments';
import Reconciliation from './components/Reconciliation';
import Exceptions from './components/Exceptions';
import Settlements from './components/Settlements';
import Refunds from './components/Refunds';
import Cash from './components/Cash';
import Forecast from './components/Forecast';
import Insights from './components/Insights';
import AIController from './components/AIController';
import Audit from './components/Audit';
import SettingsPage from './components/Settings';
import LedgerAI from './components/LedgerAI';
import api from './api/client';

const NAV_ITEMS = [
  { path: '/', icon: LayoutDashboard, label: 'Overview' },
  { path: '/payments', icon: CreditCard, label: 'Payments' },
  { path: '/settlements', icon: DollarSign, label: 'Settlements' },
  { path: '/refunds', icon: ArrowDownUp, label: 'Refunds' },
  { path: '/reconciliation', icon: RefreshCcw, label: 'Reconciliation' },
  { path: '/exceptions', icon: AlertTriangle, label: 'Exceptions' },
  { path: '/cash', icon: Wallet, label: 'Cash' },
  { path: '/forecast', icon: TrendingUp, label: 'Forecast' },
  { path: '/insights', icon: Lightbulb, label: 'Insights' },
  { path: '/ai-controller', icon: Bot, label: 'AI Agent' },
  { path: '/audit', icon: FileText, label: 'Audit' },
];

function ModeBadge() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    let mounted = true;
    api.getRazorpayStatus().then(res => { if (mounted) setStatus(res.data); }).catch(() => {});
    return () => { mounted = false; };
  }, []);
  return (
    <span
      className={`flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full whitespace-nowrap ${
        status?.connected
          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
          : 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${status?.connected ? 'bg-emerald-500' : 'bg-amber-500'} animate-pulse`} />
      {status?.connected ? `LIVE · ${status.mode}` : 'DEMO MODE'}
    </span>
  );
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5 flex-shrink-0">
      <img src="/logo-mark.png" alt="RazorLedger AI logo" className="w-9 h-9 rounded-xl shadow-sm" />
      <span className="flex flex-col leading-none">
        <span className="font-extrabold text-[17px] font-jakarta tracking-tight text-slate-900">razorledger</span>
        <span className="text-[10px] text-slate-400 font-medium tracking-wide">Finance Controller</span>
      </span>
    </Link>
  );
}

function TopNav() {
  const location = useLocation();
  const openLedger = () => window.dispatchEvent(new CustomEvent('ledger-ai:open'));
  return (
    <header className="sticky top-0 z-40 bg-white/85 backdrop-blur-md border-b border-slate-200/70">
      <div className="max-w-[1400px] mx-auto px-4 lg:px-6 h-16 flex items-center gap-4">
        <Brand />

        {/* Center pill navigation — horizontally scrollable on small screens */}
        <nav className="hidden md:flex flex-1 justify-center">
          <div className="flex items-center gap-1 bg-slate-100/70 rounded-full p-1 overflow-x-auto max-w-full no-scrollbar">
            {NAV_ITEMS.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[13px] font-medium whitespace-nowrap transition-colors ${
                    active
                      ? 'bg-slate-900 text-white shadow-sm'
                      : 'text-slate-600 hover:bg-white/70 hover:text-slate-900'
                  }`}
                >
                  <item.icon size={15} strokeWidth={2.2} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Right actions */}
        <div className="ml-auto md:ml-0 flex items-center gap-2.5">
          <ModeBadge />
          <button
            onClick={openLedger}
            className="hidden sm:flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white text-[13px] font-semibold px-3.5 py-2 rounded-full transition-colors"
          >
            <Bot size={15} /> Ledger AI
          </button>
          <button className="chip-btn bg-slate-100" aria-label="Notifications">
            <Bell size={17} />
          </button>
        </div>
      </div>

      {/* Mobile pill nav */}
      <div className="md:hidden border-t border-slate-100 px-3 py-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-[12px] font-medium whitespace-nowrap ${
                  active ? 'bg-slate-900 text-white' : 'text-slate-600 bg-slate-100/60'
                }`}
              >
                <item.icon size={14} /> {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <TopNav />
        <div className="max-w-[1400px] mx-auto p-3 lg:p-6">
          <div className="app-frame overflow-hidden">
            <main className="p-4 lg:p-7">
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/payments" element={<Payments />} />
                <Route path="/reconciliation" element={<Reconciliation />} />
                <Route path="/exceptions" element={<Exceptions />} />
                <Route path="/settlements" element={<Settlements />} />
                <Route path="/refunds" element={<Refunds />} />
                <Route path="/cash" element={<Cash />} />
                <Route path="/forecast" element={<Forecast />} />
                <Route path="/insights" element={<Insights />} />
                <Route path="/ai-controller" element={<AIController />} />
                <Route path="/audit" element={<Audit />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>
          </div>
          <p className="text-center text-[11px] text-slate-400 py-3">
            RazorLedger AI · demo data is synthetic · {NAV_ITEMS.length} finance modules
          </p>
        </div>
        <LedgerAI />
      </div>
    </BrowserRouter>
  );
}

export default App;
