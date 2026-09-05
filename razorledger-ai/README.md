# RazorLedger AI

AI-powered finance controller for merchants using Razorpay. A reconciliation engine + deterministic finance tools + an NVIDIA NIM agent with real function/tool calling, served via FastAPI with a React/Vite dashboard.

## Architecture

```
Merchant → React (Vite) → FastAPI → FinanceAgent → NVIDIA NIM
                                              ↓ tool selection
                                         Finance tool → SQLite
                                              ↓ tool result
                                              NIM → grounded answer → React
```

## Quick Start

### 1. Backend (Python 3.11+ / 3.13)

```bash
cd backend
python -m venv venv
# Windows PowerShell: .\venv\Scripts\Activate.ps1   (macOS/Linux: source venv/bin/activate)
python -m pip install -r requirements.txt
Copy-Item .env.example .env          # Windows PowerShell
# or: cp .env.example .env           # macOS/Linux
uvicorn main:app --reload --port 8000
# or: python main.py
```

On first startup the app auto-seeds a synthetic SQLite database (~120 payments, ~77 settlements, ~34 exceptions). No real personal financial data — all rows are `is_synthetic=1`.

> **PowerShell activation note:** if `Activate.ps1` is blocked, run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open http://localhost:5173

## Environment (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and fill in:

```
NVIDIA_API_KEY=sk-your-real-nvidia-key-here
NVIDIA_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
DATABASE_URL=sqlite:///./razorledger.db

# Optional — Connected Mode (Razorpay live/test sync)
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
```

- The key is read **server-side only**, directly from `backend/.env` on every request (re-reading the file each time, so editing `.env` takes effect without a backend restart).
- **Never** leave the placeholder `your_nvidia_nim_api_key_here` in `.env` — it is treated as "no key" and triggers the fallback.
- `.env` is gitignored and must never be committed or shared. `.env.example` ships with placeholders only.

## UI

Premium, light financial theme (rounded white app frame on a light gray canvas, top pill navigation, funnel / striped-progress / step / dot-matrix charts). The **Overview** page embeds an **Ask Ledger AI** prompt bar, and a persistent **Ledger AI** side panel is available on every page (button in the top nav, or the floating button). The panel/agent-activity checklist only ever shows tools the backend actually ran (`tools_used`).

## AI / NIM Tool Calling

The agent (`backend/finance_agent.py`) performs real OpenAI-compatible multi-step tool calling against NVIDIA NIM:

- User question → NIM
- NIM requests tool(s) → tools execute against the real DB
- Real results returned to NIM → NIM produces a grounded answer
- Every important interaction is recorded in the audit log

If `NVIDIA_API_KEY` is missing/invalid, the app does **not** fabricate an AI answer. It shows verified ledger results with the message "AI unavailable. Here are the verified ledger results." plus an **`AI diagnostics:`** line stating the exact cause (missing key, 401, model-not-found, timeout) so the issue is easy to fix.

> **Performance:** a full multi-step NIM answer takes ~30s (real model calls, up to 6 tool iterations). This is honest AI latency, not a bug. A faster `NVIDIA_MODEL` can reduce it — see HANDOFF.md.

## Tests

```bash
# via the running app:
curl http://localhost:8000/api/evaluate
# or directly:
cd backend && PYTHONPATH=. python -c "import models; from tests.evaluation import run_evaluation_tests; from database import SessionLocal; print(run_evaluation_tests(SessionLocal()))"
```

Current baseline: **10/10 passing (100%)**.

> **Gotcha:** import `models` before `init_db()` (or use the FastAPI app) so SQLAlchemy creates all tables. `fastapi.testclient.TestClient` only runs the `startup` handler as a context manager (`with TestClient(app) as client:`).

## API Summary

`/api/overview`, `/payments`, `/reconciliation/batch`, `/exceptions`, `/settlements`, `/refunds`, `/cash/position`, `/cash/forecast`, `/insights`, `/daily-brief`, `/money-flow`, `/actions`, `/ai/chat`, `/audit`, `/import/csv`, `/import/json`, `/demo/reset`, `/evaluate`, `/razorpay/status`, `/razorpay/connect`, `/razorpay/sync`, `/razorpay/disconnect`, `/health`.

## Security

- `NVIDIA_API_KEY` and Razorpay keys are server-side only (`.env`), never hardcoded.
- `.env`, `node_modules/`, `dist/`, `venv/`, `__pycache__/`, `*.db`, `*.pyc` are git-ignored.
- The database is recreated from the seed on startup/first run; a fresh clone auto-seeds.
