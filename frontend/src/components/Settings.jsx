import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { Upload, RefreshCcw, CheckCircle, AlertCircle, Link2, Unlink } from 'lucide-react';

function RazorpayCard() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    try { const res = await api.getRazorpayStatus(); setStatus(res.data); }
    catch (e) { setError('Could not reach backend for Razorpay status'); }
  };

  useEffect(() => { load(); }, []);

  const connect = async () => {
    setBusy(true); setError(null);
    try { await api.connectRazorpay(); await load(); }
    catch (e) { setError(e.response?.data?.detail || 'Connection failed'); }
    finally { setBusy(false); }
  };

  const sync = async () => {
    setBusy(true); setError(null);
    try { await api.syncRazorpay(); await load(); }
    catch (e) { setError(e.response?.data?.detail || 'Sync failed'); }
    finally { setBusy(false); }
  };

  const disconnect = async () => {
    setBusy(true);
    try { await api.disconnectRazorpay(); await load(); }
    finally { setBusy(false); }
  };

  if (!status) return null;

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold">Razorpay Connection</h3>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${status.connected ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'}`}>
          {status.connected ? `Connected (${status.mode})` : 'Demo Mode'}
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        {status.connected
          ? `Key ending •••${status.key_id_last4}. Live data is merged into the same dashboard.`
          : status.configured
            ? 'Credentials found in .env but not yet verified. Click Connect to verify.'
            : 'No Razorpay credentials configured. Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in backend/.env to enable Connected Mode.'}
      </p>

      <div className="grid grid-cols-3 gap-4 mb-4 text-center">
        <div className="p-3 bg-slate-50 rounded-lg"><p className="text-lg font-semibold">{status.payments_synced}</p><p className="text-xs text-slate-500">Payments synced</p></div>
        <div className="p-3 bg-slate-50 rounded-lg"><p className="text-lg font-semibold">{status.settlements_synced}</p><p className="text-xs text-slate-500">Settlements synced</p></div>
        <div className="p-3 bg-slate-50 rounded-lg"><p className="text-lg font-semibold">{status.refunds_synced}</p><p className="text-xs text-slate-500">Refunds synced</p></div>
      </div>

      {status.last_synced_at && (
        <p className="text-xs text-slate-500 mb-4">Last synced: {new Date(status.last_synced_at).toLocaleString()} ({status.last_sync_status})</p>
      )}

      <div className="flex gap-3">
        {!status.connected ? (
          <button onClick={connect} disabled={busy || !status.configured} className="flex items-center gap-2 bg-razor-600 hover:bg-razor-700 text-white px-4 py-2 rounded-lg disabled:opacity-50">
            <Link2 size={16} /> {busy ? 'Connecting...' : 'Connect'}
          </button>
        ) : (
          <>
            <button onClick={sync} disabled={busy} className="flex items-center gap-2 bg-razor-600 hover:bg-razor-700 text-white px-4 py-2 rounded-lg disabled:opacity-50">
              <RefreshCcw size={16} className={busy ? 'animate-spin' : ''} /> {busy ? 'Syncing...' : 'Sync Now'}
            </button>
            <button onClick={disconnect} disabled={busy} className="flex items-center gap-2 border border-slate-300 px-4 py-2 rounded-lg disabled:opacity-50">
              <Unlink size={16} /> Disconnect
            </button>
          </>
        )}
      </div>
      {error && <p className="text-xs text-red-600 mt-3">{error}</p>}
    </div>
  );
}

export default function Settings() {
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState(null);
  const [resetting, setResetting] = useState(false);

  const handleCSV = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImporting(true);
    try {
      const res = await api.importCSV(file);
      setMessage({ type: res.data.success ? 'success' : 'error', text: `${res.data.message} - ${res.data.records_imported} imported` });
    } catch (err) { setMessage({ type: 'error', text: err.response?.data?.detail || 'Import failed' }); }
    finally { setImporting(false); }
  };

  const handleJSON = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImporting(true);
    try {
      const res = await api.importJSON(file);
      setMessage({ type: res.data.success ? 'success' : 'error', text: `${res.data.message} - ${res.data.records_imported} imported` });
    } catch (err) { setMessage({ type: 'error', text: err.response?.data?.detail || 'Import failed' }); }
    finally { setImporting(false); }
  };

  const resetDemo = async () => {
    setResetting(true);
    try { const res = await api.resetDemo(); setMessage({ type: 'success', text: `Demo reset: ${res.data.generated.payments} payments, ${res.data.generated.settlements} settlements, ${res.data.generated.exceptions} exceptions. Match rate: ${res.data.match_rate}%` }); }
    catch (err) { setMessage({ type: 'error', text: 'Reset failed' }); }
    finally { setResetting(false); }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div><h1 className="text-2xl font-bold text-slate-900">Settings</h1><p className="text-slate-600 mt-1">Data management and configuration</p></div>

      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="font-semibold mb-4">Import Data</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-slate-50">
            <Upload size={24} className="text-razor-600" />
            <div><p className="font-medium">Import CSV</p><p className="text-xs text-slate-500">Upload payment records</p></div>
            <input type="file" accept=".csv" onChange={handleCSV} className="hidden" />
          </label>
          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-slate-50">
            <Upload size={24} className="text-razor-600" />
            <div><p className="font-medium">Import JSON</p><p className="text-xs text-slate-500">Structured payment data</p></div>
            <input type="file" accept=".json" onChange={handleJSON} className="hidden" />
          </label>
        </div>
        {importing && <p className="mt-4 text-sm text-slate-600">Importing...</p>}
      </div>

      <RazorpayCard />

      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="font-semibold mb-4">Demo Data</h3>
        <button onClick={resetDemo} disabled={resetting} className="flex items-center gap-2 bg-razor-600 hover:bg-razor-700 text-white px-4 py-2 rounded-lg disabled:opacity-50">
          <RefreshCcw size={18} className={resetting ? 'animate-spin' : ''} /> {resetting ? 'Resetting...' : 'Reset Demo Data'}
        </button>
        <p className="text-xs text-slate-500 mt-2">Regenerates 120 synthetic payment records with settlements, refunds, and exceptions</p>
      </div>

      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {message.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          <span className="text-sm">{message.text}</span>
        </div>
      )}

      <div className="bg-white rounded-xl p-6 shadow-sm border">
        <h3 className="font-semibold mb-2">API Configuration</h3>
        <p className="text-sm text-slate-600">NVIDIA API Key: Configure in backend <code className="px-2 py-0.5 bg-slate-100 rounded">.env</code> file</p>
        <p className="text-xs text-slate-500 mt-2">Environment variable: <code className="px-1 bg-slate-100 rounded">NVIDIA_API_KEY</code></p>
      </div>
    </div>
  );
}
