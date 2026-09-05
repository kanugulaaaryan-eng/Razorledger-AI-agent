#!/bin/bash
echo "=== RazorLedger AI Setup ==="

# Backend
echo "Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
echo "Edit backend/.env and add your NVIDIA_API_KEY"
cd ..

# Frontend
echo "Setting up frontend..."
cd frontend
npm install
cd ..

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To run:"
echo "  1. cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "  2. cd frontend && npm run dev"
echo "  3. Open http://localhost:5173"
