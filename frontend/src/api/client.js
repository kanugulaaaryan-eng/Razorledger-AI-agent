import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export const api = {
  getOverview: () => axios.get(`${API_BASE}/overview`),
  getPayments: (params = {}) => axios.get(`${API_BASE}/payments`, { params }),
  getPaymentDetails: (id) => axios.get(`${API_BASE}/payments/${id}`),
  getReconciliationBatch: (limit = 100) => axios.get(`${API_BASE}/reconciliation/batch`, { params: { limit } }),
  runReconciliation: () => axios.post(`${API_BASE}/reconciliation/run`),
  getExceptions: () => axios.get(`${API_BASE}/exceptions`),
  getSettlements: (limit = 50) => axios.get(`${API_BASE}/settlements`, { params: { limit } }),
  getRefunds: (limit = 50) => axios.get(`${API_BASE}/refunds`, { params: { limit } }),
  getCashPosition: () => axios.get(`${API_BASE}/cash/position`),
  getCashForecast: (days = 7) => axios.get(`${API_BASE}/cash/forecast`, { params: { days } }),
  getInsights: () => axios.get(`${API_BASE}/insights`),
  getDailyBrief: () => axios.get(`${API_BASE}/daily-brief`),
  getMoneyFlow: () => axios.get(`${API_BASE}/money-flow`),
  getActions: () => axios.get(`${API_BASE}/actions`),
  chat: (message) => axios.post(`${API_BASE}/ai/chat`, { message }),
  getAudit: (limit = 50) => axios.get(`${API_BASE}/audit`, { params: { limit } }),
  importCSV: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE}/import/csv`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  importJSON: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE}/import/json`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  resetDemo: () => axios.post(`${API_BASE}/demo/reset`),
  evaluate: () => axios.get(`${API_BASE}/evaluate`),
  getRazorpayStatus: () => axios.get(`${API_BASE}/razorpay/status`),
  connectRazorpay: () => axios.post(`${API_BASE}/razorpay/connect`),
  syncRazorpay: () => axios.post(`${API_BASE}/razorpay/sync`),
  disconnectRazorpay: () => axios.post(`${API_BASE}/razorpay/disconnect`),
};

export default api;
