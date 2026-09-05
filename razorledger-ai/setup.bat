@echo off
echo === RazorLedger AI Setup ===

echo Setting up backend...
cd backend
python -m venv venv
call venv\Scriptsctivate
pip install -r requirements.txt
copy .env.example .env
echo Edit backend\.env and add your NVIDIA_API_KEY
cd ..

echo Setting up frontend...
cd frontend
npm install
cd ..

echo.
echo === Setup Complete ===
echo.
echo To run:
echo   1. cd backend ^&^& venv\Scriptsctivate ^&^& uvicorn main:app --reload
echo   2. cd frontend ^&^& npm run dev
echo   3. Open http://localhost:5173
pause
