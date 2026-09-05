from sqlalchemy.orm import Session
from models import Payment, Settlement, ReconciliationResult, ReconciliationStatus, SettlementStatus, PaymentStatus
from datetime import datetime
import math

# A shortfall larger than this fraction of the payment amount is treated as
# a genuinely unexplained shortfall (escalate) rather than a review item.
UNRESOLVED_SHORTFALL_RATIO = 0.10


class ReconciliationEngine:
    def __init__(self, db: Session):
        self.db = db
    
    def reconcile_payment(self, payment: Payment) -> dict:
        expected = payment.amount - payment.fee - payment.tax - payment.refund_amount
        actual = payment.settlement_amount
        discrepancy = round(actual - expected, 2)
        
        if abs(discrepancy) < 0.5:
            status = ReconciliationStatus.MATCHED
            reason = "Amount matches expected settlement (within tolerance)"
            confidence = 0.99
            recommended_action = "No action required"
        elif payment.settlement_status == SettlementStatus.MISSING:
            status = ReconciliationStatus.UNRESOLVED
            reason = "No settlement record found for captured payment"
            confidence = 0.95
            recommended_action = "Contact payment provider for settlement status"
        elif payment.payment_status == PaymentStatus.FAILED:
            status = ReconciliationStatus.MATCHED
            reason = "Payment failed - no settlement expected"
            confidence = 1.0
            recommended_action = "No action required"
        elif payment.payment_status == PaymentStatus.PENDING:
            status = ReconciliationStatus.MATCHED
            reason = "Payment pending - no settlement expected yet"
            confidence = 0.95
            recommended_action = "Wait for payment completion"
        elif payment.refund_amount > 0 and payment.refund_amount >= payment.amount:
            status = ReconciliationStatus.MATCHED
            reason = f"Full refund of ₹{payment.refund_amount:,.2f} processed"
            confidence = 0.98
            recommended_action = "Verify refund completion"
        elif payment.refund_amount > 0 and payment.refund_amount < payment.amount:
            expected_partial = payment.amount - payment.fee - payment.tax - payment.refund_amount
            if abs(actual - expected_partial) < 0.5:
                status = ReconciliationStatus.MATCHED
                reason = f"Partial refund of ₹{payment.refund_amount:,.2f} accounted for"
                confidence = 0.95
                recommended_action = "No action required"
            else:
                status = ReconciliationStatus.EXPLAINABLE
                reason = f"Partial refund present, settlement difference ₹{discrepancy:,.2f}"
                confidence = 0.85
                recommended_action = "Review refund and settlement timing"
        elif payment.amount > 0 and abs(discrepancy) > payment.amount * UNRESOLVED_SHORTFALL_RATIO:
            status = ReconciliationStatus.UNRESOLVED
            reason = (f"Unexplained settlement shortfall of ₹{abs(discrepancy):,.2f} "
                      f"({abs(discrepancy)/payment.amount*100:.1f}% of the payment amount)")
            confidence = 0.60
            recommended_action = "Escalate to payment provider"
        elif abs(discrepancy) <= (payment.fee + payment.tax):
            # A discrepancy no larger than the fee+tax actually charged is
            # explainable as fee/tax variation.
            status = ReconciliationStatus.EXPLAINABLE
            reason = f"Fee/tax difference of ₹{abs(discrepancy):,.2f} within expected range"
            confidence = 0.80
            recommended_action = "Verify fee structure with provider"
        else:
            # Larger unexplained difference (either direction) needs review.
            status = ReconciliationStatus.REVIEW
            if discrepancy > 0:
                reason = f"Settlement exceeds expected by ₹{discrepancy:,.2f}"
            else:
                reason = f"Unexplained settlement difference of ₹{abs(discrepancy):,.2f}"
            confidence = 0.70
            recommended_action = "Investigate settlement discrepancy"

        evidence = (
            f"Expected: ₹{payment.amount - payment.fee - payment.tax - payment.refund_amount:,.2f}, "
            f"Actual: ₹{payment.settlement_amount:,.2f}, Diff: ₹{discrepancy:,.2f}"
        )
        
        return {
            "payment_id": payment.payment_id,
            "amount": payment.amount,
            "status": status,
            "reason": reason,
            "evidence": evidence,
            "discrepancy": discrepancy,
            "confidence": confidence,
            "recommended_action": recommended_action
        }
    
    def run_reconciliation(self, batch_id: str = None) -> dict:
        if not batch_id:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        payments = self.db.query(Payment).all()
        results = []
        
        for payment in payments:
            result = self.reconcile_payment(payment)
            result["batch_id"] = batch_id
            
            rec_result = ReconciliationResult(
                batch_id=batch_id,
                payment_id=payment.payment_id,
                status=result["status"],
                reason=result["reason"],
                evidence=result["evidence"],
                discrepancy=result["discrepancy"],
                confidence=result["confidence"],
                recommended_action=result["recommended_action"]
            )
            self.db.add(rec_result)
            results.append(result)
        
        self.db.commit()
        
        statistics = self.calculate_statistics(results)
        
        return {
            "batch_id": batch_id,
            "statistics": statistics,
            "results": results
        }
    
    def calculate_statistics(self, results: list) -> dict:
        total = len(results)
        matched = sum(1 for r in results if r["status"] == ReconciliationStatus.MATCHED)
        explainable = sum(1 for r in results if r["status"] == ReconciliationStatus.EXPLAINABLE)
        review = sum(1 for r in results if r["status"] == ReconciliationStatus.REVIEW)
        unresolved = sum(1 for r in results if r["status"] == ReconciliationStatus.UNRESOLVED)
        flagged = sum(1 for r in results if r["status"] in [ReconciliationStatus.REVIEW, ReconciliationStatus.UNRESOLVED])
        
        payments = self.db.query(Payment).all()
        total_amount = sum(p.amount for p in payments)
        total_settled = sum(p.settlement_amount for p in payments)
        total_refunds = sum(p.refund_amount for p in payments)
        total_fees = sum(p.fee for p in payments)
        total_pending = sum(p.amount for p in payments if p.settlement_status == SettlementStatus.PENDING)
        total_unresolved = sum(abs(r["discrepancy"]) for r in results if r["status"] == ReconciliationStatus.UNRESOLVED)
        
        match_rate = round((matched / total * 100) if total > 0 else 0, 1)
        
        return {
            "total_records": total,
            "matched": matched,
            "explainable": explainable,
            "review_required": review,
            "unresolved": unresolved,
            "flagged": flagged,
            "match_rate": match_rate,
            "total_amount": total_amount,
            "total_settled": total_settled,
            "total_refunds": total_refunds,
            "total_fees": total_fees,
            "total_pending": total_pending,
            "total_unresolved": total_unresolved
        }