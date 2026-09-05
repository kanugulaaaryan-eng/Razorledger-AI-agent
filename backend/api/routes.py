from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from finance_tools import FinanceTools
from finance_agent import FinanceAgent
from sync_service import SyncService
from models import Payment, Settlement, Refund, Exception as Exc, ReconciliationResult, AuditLog, PaymentStatus, SettlementStatus, RefundStatus
from schemas import (
    PaymentResponse, SettlementResponse, RefundResponse, ExceptionResponse,
    ReconciliationBatchResponse, CashPositionResponse, ForecastResponse,
    InsightResponse, DailyBriefResponse, MoneyFlowResponse,
    AIChatRequest, AIChatResponse, ImportResponse, DemoResetResponse,
    EvaluationResponse, AuditLogResponse, OverviewResponse
)
import csv
import json
from io import StringIO
from datetime import datetime

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    
    payment_summary = tools.get_payment_summary()
    reconciliation = tools.reconcile_batch()
    cash_position = tools.calculate_cash_position()
    exceptions = tools.find_exceptions()
    daily_brief = tools.get_daily_finance_brief()
    
    return {
        "payment_summary": payment_summary,
        "reconciliation_stats": reconciliation["statistics"],
        "cash_position": cash_position,
        "exceptions_count": len(exceptions),
        "daily_brief": daily_brief
    }


@router.get("/payments", response_model=List[PaymentResponse])
def get_payments(limit: int = 100, status: Optional[str] = None, db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    payments = tools.list_payments(limit=limit, status=status)
    return payments


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment_details(payment_id: str, db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    payment = tools.get_payment_details(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/reconciliation/batch", response_model=ReconciliationBatchResponse)
def get_reconciliation_batch(limit: int = 100, db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    result = tools.reconcile_batch(limit=limit)
    return result


@router.post("/reconciliation/run")
def run_reconciliation(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    result = tools.reconcile_batch()
    return {"success": True, "batch_id": result["batch_id"], "statistics": result["statistics"]}


@router.get("/exceptions", response_model=List[ExceptionResponse])
def get_exceptions(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    exceptions = tools.find_exceptions()
    return exceptions


@router.get("/settlements", response_model=List[SettlementResponse])
def get_settlements(limit: int = 50, db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    settlements = tools.get_settlements(limit=limit)
    return settlements


@router.get("/refunds", response_model=dict)
def get_refunds(limit: int = 50, db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.get_refunds(limit=limit)


@router.get("/cash/position", response_model=CashPositionResponse)
def get_cash_position(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.calculate_cash_position()


@router.get("/cash/forecast", response_model=ForecastResponse)
def get_cash_forecast(days: int = 7, db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.forecast_cash_flow(days=days)


@router.get("/insights", response_model=List[InsightResponse])
def get_insights(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.get_finance_insights()


@router.get("/daily-brief", response_model=DailyBriefResponse)
def get_daily_brief(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.get_daily_finance_brief()


@router.get("/money-flow", response_model=MoneyFlowResponse)
def get_money_flow(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.get_money_flow()


@router.get("/actions", response_model=List[dict])
def get_actions(db: Session = Depends(get_db)):
    tools = FinanceTools(db)
    return tools.get_actions()


@router.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(request: AIChatRequest, db: Session = Depends(get_db)):
    agent = FinanceAgent(db)
    result = agent.chat(request.message)
    return result


@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs


@router.post("/import/csv", response_model=ImportResponse)
def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")
    
    content = file.file.read().decode('utf-8')
    reader = csv.DictReader(StringIO(content))
    
    required_fields = ['order_id', 'payment_id', 'customer_id', 'amount', 'payment_status', 'payment_method']
    errors = []
    imported = 0
    
    for row_num, row in enumerate(reader, 2):
        missing = [f for f in required_fields if f not in row or not row[f]]
        if missing:
            errors.append(f"Row {row_num}: Missing fields: {', '.join(missing)}")
            continue
        
        try:
            payment = Payment(
                payment_id=row['payment_id'],
                order_id=row['order_id'],
                customer_id=row['customer_id'],
                customer_email=row.get('customer_email'),
                customer_name=row.get('customer_name'),
                amount=float(row['amount']),
                currency=row.get('currency', 'INR'),
                payment_status=row['payment_status'],
                payment_method=row['payment_method'],
                fee=float(row.get('fee', 0)),
                tax=float(row.get('tax', 0)),
                refund_amount=float(row.get('refund_amount', 0)),
                refund_status=row.get('refund_status', 'pending'),
                settlement_id=row.get('settlement_id'),
                settlement_amount=float(row.get('settlement_amount', 0)),
                settlement_status=row.get('settlement_status', 'not_settled'),
                created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now(),
                settlement_date=datetime.fromisoformat(row['settlement_date']) if row.get('settlement_date') else None,
                description=row.get('description'),
                is_synthetic=0
            )
            db.add(payment)
            imported += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    db.commit()
    
    if imported > 0:
        tools = FinanceTools(db)
        tools.reconcile_batch()
        tools.find_exceptions()
    
    return ImportResponse(
        success=len(errors) == 0,
        message=f"Imported {imported} records" + (f" with {len(errors)} errors" if errors else ""),
        records_imported=imported,
        validation_errors=errors
    )


@router.post("/import/json", response_model=ImportResponse)
def import_json(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be JSON")
    
    content = file.file.read().decode('utf-8')
    data = json.loads(content)
    
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of payments")
    
    required_fields = ['order_id', 'payment_id', 'customer_id', 'amount', 'payment_status', 'payment_method']
    errors = []
    imported = 0
    
    for i, row in enumerate(data):
        missing = [f for f in required_fields if f not in row or not row[f]]
        if missing:
            errors.append(f"Record {i}: Missing fields: {', '.join(missing)}")
            continue
        
        try:
            payment = Payment(
                payment_id=row['payment_id'],
                order_id=row['order_id'],
                customer_id=row['customer_id'],
                customer_email=row.get('customer_email'),
                customer_name=row.get('customer_name'),
                amount=float(row['amount']),
                currency=row.get('currency', 'INR'),
                payment_status=row['payment_status'],
                payment_method=row['payment_method'],
                fee=float(row.get('fee', 0)),
                tax=float(row.get('tax', 0)),
                refund_amount=float(row.get('refund_amount', 0)),
                refund_status=row.get('refund_status', 'pending'),
                settlement_id=row.get('settlement_id'),
                settlement_amount=float(row.get('settlement_amount', 0)),
                settlement_status=row.get('settlement_status', 'not_settled'),
                created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now(),
                settlement_date=datetime.fromisoformat(row['settlement_date']) if row.get('settlement_date') else None,
                description=row.get('description'),
                is_synthetic=0
            )
            db.add(payment)
            imported += 1
        except Exception as e:
            errors.append(f"Record {i}: {str(e)}")
    
    db.commit()
    
    if imported > 0:
        tools = FinanceTools(db)
        tools.reconcile_batch()
        tools.find_exceptions()
    
    return ImportResponse(
        success=len(errors) == 0,
        message=f"Imported {imported} records" + (f" with {len(errors)} errors" if errors else ""),
        records_imported=imported,
        validation_errors=errors
    )


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo(db: Session = Depends(get_db)):
    from seed_data import seed_database
    result = seed_database()
    return DemoResetResponse(
        generated=result,
        match_rate=0.0
    )


@router.get("/evaluate", response_model=EvaluationResponse)
def run_evaluation(db: Session = Depends(get_db)):
    from tests.evaluation import run_evaluation_tests
    result = run_evaluation_tests(db)
    return result


# ---------------------------------------------------------------------------
# Razorpay integration
#
# DEMO MODE: no credentials required, seeded data powers every page above.
# CONNECTED MODE: once RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are set in
# backend/.env, /api/razorpay/connect verifies them against the real
# Razorpay API and /api/razorpay/sync pulls live payments/refunds/settlements
# into the same tables Demo Mode uses. Nothing here fakes a connection: if
# credentials are missing or invalid, `connected` stays false and the error
# is returned as-is.
# ---------------------------------------------------------------------------

@router.get("/razorpay/status")
def get_razorpay_status(db: Session = Depends(get_db)):
    return SyncService(db).status()


@router.post("/razorpay/connect")
def connect_razorpay(db: Session = Depends(get_db)):
    result = SyncService(db).test_and_mark_connected()
    if not result.get("connected"):
        raise HTTPException(status_code=400, detail=result.get("error", "Could not connect to Razorpay"))
    return result


@router.post("/razorpay/sync")
def sync_razorpay(db: Session = Depends(get_db)):
    result = SyncService(db).sync_all()
    if result.get("last_sync_status") == "failed":
        raise HTTPException(status_code=400, detail=result.get("last_sync_error", "Sync failed"))
    return result


@router.post("/razorpay/disconnect")
def disconnect_razorpay(db: Session = Depends(get_db)):
    service = SyncService(db)
    conn = service.get_or_create_connection()
    conn.is_connected = 0
    db.commit()
    return service.status()