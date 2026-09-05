from sqlalchemy.orm import Session
from models import Payment, PaymentStatus, SettlementStatus, RefundStatus
from finance_tools import FinanceTools
from reconciliation import ReconciliationEngine, ReconciliationStatus
from datetime import datetime
import json


def create_test_payment(db: Session, **kwargs) -> Payment:
    defaults = {
        "payment_id": f"pay_test_{kwargs.get('amount', 1000)}",
        "order_id": f"order_test_{kwargs.get('amount', 1000)}",
        "customer_id": "cust_test",
        "customer_email": "test@example.com",
        "amount": 10000.0,
        "currency": "INR",
        "payment_status": PaymentStatus.CAPTURED,
        "payment_method": "upi",
        "fee": 250.0,
        "tax": 45.0,
        "refund_amount": 0.0,
        "refund_status": RefundStatus.PENDING,
        "settlement_id": "sett_test",
        "settlement_amount": 9705.0,
        "settlement_status": SettlementStatus.PROCESSED,
        "created_at": datetime(2024, 1, 15, 10, 0, 0),
        "description": "Test payment",
        "is_synthetic": 1
    }
    defaults.update(kwargs)
    p = Payment(**defaults)
    db.add(p)
    db.commit()
    return p


def run_evaluation_tests(db: Session) -> dict:
    test_cases = []
    passed = 0
    failed = 0
    
    db.query(Payment).delete()
    db.commit()
    
    tools = FinanceTools(db)
    engine = ReconciliationEngine(db)
    
    # Test 1: Exact match
    p1 = create_test_payment(db, payment_id="pay_exact_1", amount=10000, fee=250, tax=45, settlement_amount=9705)
    result = engine.reconcile_payment(p1)
    test_cases.append({
        "name": "exact_match",
        "expected": ReconciliationStatus.MATCHED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.MATCHED
    })
    if result["status"] == ReconciliationStatus.MATCHED:
        passed += 1
    else:
        failed += 1
    
    # Test 2: Fee mismatch
    p2 = create_test_payment(db, payment_id="pay_fee_mismatch", amount=10000, fee=250, tax=45, settlement_amount=9500)
    result = engine.reconcile_payment(p2)
    test_cases.append({
        "name": "fee_mismatch",
        "expected": ReconciliationStatus.EXPLAINABLE,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.EXPLAINABLE
    })
    if result["status"] == ReconciliationStatus.EXPLAINABLE:
        passed += 1
    else:
        failed += 1
    
    # Test 3: Full refund
    p3 = create_test_payment(db, payment_id="pay_refund_full", amount=10000, fee=250, tax=45, 
                            refund_amount=10000, refund_status=RefundStatus.PROCESSED, settlement_amount=0)
    result = engine.reconcile_payment(p3)
    test_cases.append({
        "name": "full_refund",
        "expected": ReconciliationStatus.MATCHED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.MATCHED
    })
    if result["status"] == ReconciliationStatus.MATCHED:
        passed += 1
    else:
        failed += 1
    
    # Test 4: Partial refund
    p4 = create_test_payment(db, payment_id="pay_refund_partial", amount=10000, fee=250, tax=45, 
                            refund_amount=3000, refund_status=RefundStatus.PARTIAL, settlement_amount=6705)
    result = engine.reconcile_payment(p4)
    test_cases.append({
        "name": "partial_refund",
        "expected": ReconciliationStatus.MATCHED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.MATCHED
    })
    if result["status"] == ReconciliationStatus.MATCHED:
        passed += 1
    else:
        failed += 1
    
    # Test 5: Missing settlement
    p5 = create_test_payment(db, payment_id="pay_missing_settlement", amount=10000, fee=250, tax=45, 
                            settlement_id=None, settlement_amount=0, settlement_status=SettlementStatus.MISSING)
    result = engine.reconcile_payment(p5)
    test_cases.append({
        "name": "missing_settlement",
        "expected": ReconciliationStatus.UNRESOLVED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.UNRESOLVED
    })
    if result["status"] == ReconciliationStatus.UNRESOLVED:
        passed += 1
    else:
        failed += 1
    
# Test 6: Duplicate detection
    p6a = create_test_payment(db, payment_id="pay_dup_1", amount=5000, customer_id="cust_dup",
                              created_at=datetime(2024, 1, 15, 10, 0, 0))
    p6b = create_test_payment(db, payment_id="pay_dup_2", amount=5000, customer_id="cust_dup",
                              created_at=datetime(2024, 1, 15, 10, 0, 0))
    duplicates = tools.find_duplicates()
    test_cases.append({
        "name": "duplicate_detection",
        "expected": True,
        "actual": len(duplicates) > 0,
        "passed": len(duplicates) > 0
    })
    if len(duplicates) > 0:
        passed += 1
    else:
        failed += 1
    
    # Test 7: Unresolved transaction
    p7 = create_test_payment(db, payment_id="pay_unresolved", amount=50000, fee=1000, tax=180, 
                            settlement_amount=40000, settlement_status=SettlementStatus.PROCESSED)
    result = engine.reconcile_payment(p7)
    test_cases.append({
        "name": "unresolved_transaction",
        "expected": ReconciliationStatus.UNRESOLVED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.UNRESOLVED
    })
    if result["status"] == ReconciliationStatus.UNRESOLVED:
        passed += 1
    else:
        failed += 1
    
    # Test 8: Pending payment
    p8 = create_test_payment(db, payment_id="pay_pending", amount=10000, 
                            payment_status=PaymentStatus.PENDING, settlement_status=SettlementStatus.NOT_SETTLED,
                            settlement_amount=0)
    result = engine.reconcile_payment(p8)
    test_cases.append({
        "name": "pending_payment",
        "expected": ReconciliationStatus.MATCHED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.MATCHED
    })
    if result["status"] == ReconciliationStatus.MATCHED:
        passed += 1
    else:
        failed += 1
    
    # Test 9: Failed payment
    p9 = create_test_payment(db, payment_id="pay_failed", amount=10000, 
                            payment_status=PaymentStatus.FAILED, settlement_status=SettlementStatus.NOT_SETTLED,
                            settlement_amount=0)
    result = engine.reconcile_payment(p9)
    test_cases.append({
        "name": "failed_payment",
        "expected": ReconciliationStatus.MATCHED,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.MATCHED
    })
    if result["status"] == ReconciliationStatus.MATCHED:
        passed += 1
    else:
        failed += 1
    
    # Test 10: Large discrepancy review
    p10 = create_test_payment(db, payment_id="pay_large_diff", amount=100000, fee=2000, tax=360, 
                             settlement_amount=95000)
    result = engine.reconcile_payment(p10)
    test_cases.append({
        "name": "large_discrepancy_review",
        "expected": ReconciliationStatus.REVIEW,
        "actual": result["status"],
        "passed": result["status"] == ReconciliationStatus.REVIEW
    })
    if result["status"] == ReconciliationStatus.REVIEW:
        passed += 1
    else:
        failed += 1
    
    total = passed + failed
    accuracy = round((passed / total * 100) if total > 0 else 0, 1)
    
    return {
        "test_cases": total,
        "passed": passed,
        "failed": failed,
        "accuracy": accuracy,
        "details": test_cases
    }


if __name__ == "__main__":
    from database import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        result = run_evaluation_tests(db)
        print(json.dumps(result, indent=2))
    finally:
        db.close()