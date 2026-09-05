from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from api.routes import router as api_router
import uvicorn

app = FastAPI(
    title="RazorLedger AI",
    description="AI-powered finance controller for merchants",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def startup_event():
    init_db()
    # Auto-seed on first boot so the dashboard shows real data immediately.
    try:
        from database import SessionLocal
        from models import Payment
        db = SessionLocal()
        try:
            has_data = db.query(Payment).first() is not None
        finally:
            db.close()
        if not has_data:
            from seed_data import seed_database
            seed_database()
    except Exception:
        # Seeding is best-effort; the app still boots with empty tables if it fails.
        pass


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "razorledger-ai"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)