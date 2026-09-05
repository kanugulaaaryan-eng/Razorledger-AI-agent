from sqlalchemy.orm import Session
from models import Payment, Settlement, Refund, Exception as Exc, AuditLog, PaymentStatus, SettlementStatus, RefundStatus, ExceptionSeverity, ReconciliationStatus
from datetime import datetime, timedelta
from typing import List, Dict, Any
from reconciliation import ReconciliationEngine
import statistics
import math


class FinanceTools:
    def __init__(self, db: Session):
        self.db = db
        self.reconciliation_engine = ReconciliationEngine(db)
    
    def get_payment_summary(self) -> Dict[str, Any]:
        payments = self.db.query(Payment).all()
        total = len(payments)
        successful = sum(1 for p in payments if p.payment_status == PaymentStatus.CAPTURED)
        pending = sum(1 for p in payments if p.payment_status == PaymentStatus.PENDING)
        failed = sum(1 for p in payments if p.payment_status == PaymentStatus.FAILED)
        refunded = sum(1 for p in payments if p.payment_status == PaymentStatus.REFUNDED)
        authorized = sum(1 for p in payments if p.payment_status == PaymentStatus.AUTHORIZED)
        
        return {
            "total_payments": total,
            "successful": successful,
            "pending": pending,
            "failed": failed,
            "refunded": refunded,
            "authorized": authorized,
            "success_rate": round((successful / total * 100) if total > 0 else 0, 1)
        }
    
    def list_payments(self, limit: int = 100, status: str = None) -> List[Dict[str, Any]]:
        query = self.db.query(Payment)
        if status:
            try:
                payment_status = PaymentStatus(status)
                query = query.filter(Payment.payment_status == payment_status)
            except ValueError:
                pass
        payments = query.order_by(Payment.created_at.desc()).limit(limit).all()
        
        return [self._payment_to_dict(p) for p in payments]
    
    def get_payment_details(self, payment_id: str) -> Dict[str, Any]:
        payment = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            return None
        
        result = self._payment_to_dict(payment)
        rec = self.reconciliation_engine.reconcile_payment(payment)
        result["reconciliation_status"] = rec["status"].value
        result["ai_diagnosis"] = rec["reason"]
        result["confidence"] = rec["confidence"]
        result["recommended_action"] = rec["recommended_action"]
        return result
    
    def get_pending_payments(self) -> List[Dict[str, Any]]:
        payments = self.db.query(Payment).filter(
            Payment.payment_status == PaymentStatus.PENDING
        ).all()
        return [self._payment_to_dict(p) for p in payments]
    
    def get_failed_payments(self) -> List[Dict[str, Any]]:
        payments = self.db.query(Payment).filter(
            Payment.payment_status == PaymentStatus.FAILED
        ).all()
        return [self._payment_to_dict(p) for p in payments]
    
    def get_refunds(self, limit: int = 50) -> Dict[str, Any]:
        refunds = self.db.query(Refund).order_by(Refund.created_at.desc()).limit(limit).all()
        
        total_count = len(refunds)
        total_amount = sum(r.refund_amount for r in refunds)
        full_refunds = sum(1 for r in refunds if r.refund_amount >= r.original_amount * 0.95)
        partial_refunds = sum(1 for r in refunds if 0 < r.refund_amount < r.original_amount * 0.95)
        pending_refunds = sum(1 for r in refunds if r.refund_status == RefundStatus.PENDING)
        
        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "full_refunds": full_refunds,
            "partial_refunds": partial_refunds,
            "pending_refunds": pending_refunds,
            "refunds": [self._refund_to_dict(r) for r in refunds]
        }
    
    def get_settlements(self, limit: int = 50) -> List[Dict[str, Any]]:
        settlements = self.db.query(Settlement).order_by(Settlement.processed_at.desc()).limit(limit).all()
        return [self._settlement_to_dict(s) for s in settlements]
    
    def reconcile_transaction(self, payment_id: str) -> Dict[str, Any]:
        payment = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            return {"error": "Payment not found"}
        return self.reconciliation_engine.reconcile_payment(payment)
    
    def reconcile_batch(self, limit: int = 100) -> Dict[str, Any]:
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.reconciliation_engine.run_reconciliation(batch_id)
    
    def find_exceptions(self) -> List[Exc]:
        payments = self.db.query(Payment).all()
        exceptions = []
        
        for p in payments:
            exc_counter = 0
            
            def gen_exc_id(exception_type):
                nonlocal exc_counter
                exc_counter += 1
                return f"exc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{exc_counter}_{p.payment_id[-12:]}_{exception_type[:3]}"
            
            if p.payment_status == PaymentStatus.CAPTURED:
                expected = p.amount - p.fee - p.tax - p.refund_amount
                actual = p.settlement_amount
                diff = abs(actual - expected)
                
                if diff > 10000:
                    exceptions.append(Exc(
                        exception_id=gen_exc_id("unexplained_settlement_difference"),
                        exception_type="unexplained_settlement_difference",
                        severity=ExceptionSeverity.CRITICAL if diff > 50000 else ExceptionSeverity.HIGH,
                        payment_id=p.payment_id,
                        amount=diff,
                        reason=f"Settlement difference of ₹{diff:,.2f} cannot be explained by fees or refunds",
                        evidence=f"Expected: ₹{expected:,.2f}, Actual: ₹{actual:,.2f}, Fees: ₹{p.fee:,.2f}, Tax: ₹{p.tax:,.2f}, Refunds: ₹{p.refund_amount:,.2f}",
                        confidence=0.9 if diff > 50000 else 0.75,
                        recommended_action="Contact payment provider immediately",
                        is_synthetic=1
                    ))
                elif diff > 1000:
                    exceptions.append(Exc(
                        exception_id=gen_exc_id("settlement_mismatch"),
                        exception_type="settlement_mismatch",
                        severity=ExceptionSeverity.HIGH,
                        payment_id=p.payment_id,
                        amount=diff,
                        reason=f"Settlement mismatch of ₹{diff:,.2f}",
                        evidence=f"Expected: ₹{expected:,.2f}, Actual: ₹{actual:,.2f}",
                        confidence=0.8,
                        recommended_action="Review settlement report",
                        is_synthetic=1
                    ))
            
            if p.payment_status == PaymentStatus.PENDING and (datetime.now() - p.created_at).days > 3:
                exceptions.append(Exc(
                    exception_id=gen_exc_id("stale_pending_payment"),
                    exception_type="stale_pending_payment",
                    severity=ExceptionSeverity.MEDIUM,
                    payment_id=p.payment_id,
                    amount=p.amount,
                    reason=f"Payment pending for {(datetime.now() - p.created_at).days} days",
                    evidence=f"Created: {p.created_at.strftime('%Y-%m-%d')}, Status: pending",
                    confidence=0.85,
                    recommended_action="Follow up with payment provider",
                    is_synthetic=1
                ))
            
            if p.payment_status == PaymentStatus.CAPTURED and p.settlement_status == SettlementStatus.MISSING:
                exceptions.append(Exc(
                    exception_id=gen_exc_id("missing_settlement"),
                    exception_type="missing_settlement",
                    severity=ExceptionSeverity.HIGH,
                    payment_id=p.payment_id,
                    amount=p.amount,
                    reason="Captured payment has no settlement record",
                    evidence=f"Payment captured but settlement_status is MISSING",
                    confidence=0.95,
                    recommended_action="Request settlement report from provider",
                    is_synthetic=1
                ))
            
            if p.refund_amount > 0 and p.refund_status == RefundStatus.PENDING:
                exceptions.append(Exc(
                    exception_id=gen_exc_id("pending_refund"),
                    exception_type="pending_refund",
                    severity=ExceptionSeverity.MEDIUM,
                    payment_id=p.payment_id,
                    amount=p.refund_amount,
                    reason=f"Refund of ₹{p.refund_amount:,.2f} pending",
                    evidence=f"Refund initiated but status is PENDING",
                    confidence=0.8,
                    recommended_action="Check refund status with provider",
                    is_synthetic=1
                ))
        
        existing_exceptions = {e.payment_id + "_" + e.exception_type for e in self.db.query(Exc).filter(Exc.status == "open").all()}
        new_exceptions = []
        for e in exceptions:
            key = e.payment_id + "_" + e.exception_type
            if key not in existing_exceptions:
                new_exceptions.append(e)
        
        for exc in new_exceptions:
            self.db.add(exc)
        self.db.commit()
        
        return self.db.query(Exc).filter(Exc.status == "open").order_by(Exc.severity.desc(), Exc.created_at.desc()).all()
    
    def find_duplicates(self) -> List[Dict[str, Any]]:
        payments = self.db.query(Payment).all()
        duplicates = []
        
        seen = {}
        for p in payments:
            key = (p.customer_id, p.amount, p.created_at.date())
            if key in seen:
                duplicates.append({
                    "payment_id": p.payment_id,
                    "duplicate_of": seen[key],
                    "amount": p.amount,
                    "customer_id": p.customer_id,
                    "date": p.created_at.date().isoformat()
                })
            else:
                seen[key] = p.payment_id
        
        return duplicates
    
    def calculate_cash_position(self) -> Dict[str, Any]:
        payments = self.db.query(Payment).all()
        
        captured_total = sum(p.amount for p in payments if p.payment_status == PaymentStatus.CAPTURED)
        settled_cash = sum(p.settlement_amount for p in payments if p.settlement_status == SettlementStatus.PROCESSED)
        pending_settlement = sum(p.amount - p.fee - p.refund_amount for p in payments if p.settlement_status == SettlementStatus.PENDING)
        refunded = sum(p.refund_amount for p in payments)
        fees_paid = sum(p.fee for p in payments if p.payment_status == PaymentStatus.CAPTURED)
        
        unresolved_payments = [p for p in payments if p.payment_status == PaymentStatus.CAPTURED and p.settlement_status == SettlementStatus.MISSING]
        unresolved = sum(p.amount for p in unresolved_payments)
        
        available_cash = settled_cash
        
        return {
            "captured_total": captured_total,
            "settled_cash": settled_cash,
            "available_cash": available_cash,
            "pending_settlement": pending_settlement,
            "refunded": refunded,
            "fees_paid": fees_paid,
            "unresolved": unresolved,
            "expected_incoming": pending_settlement
        }
    
    def forecast_cash_flow(self, days: int = 7) -> Dict[str, Any]:
        today = datetime.now().date()
        pending = self.db.query(Payment).filter(
            Payment.payment_status == PaymentStatus.CAPTURED,
            Payment.settlement_status == SettlementStatus.PENDING
        ).all()
        
        # 1) Direct projection from pending settlements with a known future date.
        daily_expected = {}
        for p in pending:
            if p.settlement_date:
                date_key = p.settlement_date.date().isoformat()
            else:
                date_key = (p.created_at + timedelta(days=2)).date().isoformat()
            amount = round(p.amount - p.fee - p.tax - p.refund_amount, 2)
            if amount < 0:
                amount = 0.0
            daily_expected[date_key] = daily_expected.get(date_key, 0.0) + amount
        
        # 2) Historical fallback: average daily settlement velocity over the last
        #    14 processed settlements, used when no future-dated settlement exists.
        hist = self.db.query(Settlement).filter(
            Settlement.status == SettlementStatus.PROCESSED,
            Settlement.actual_amount > 0
        ).order_by(Settlement.processed_at.desc()).limit(14).all()
        historical_daily = (sum(s.actual_amount for s in hist) / 14.0) if hist else 0.0
        projected_any = any(daily_expected.get((today + timedelta(days=i)).isoformat(), 0) > 0 for i in range(days))
        
        forecast = []
        total = 0.0
        for i in range(days):
            date_key = (today + timedelta(days=i)).isoformat()
            expected = daily_expected.get(date_key, 0.0)
            if expected <= 0 and not projected_any:
                expected = round(historical_daily, 2)
            total += expected
            volatility = expected * 0.15
            forecast.append({
                "date": date_key,
                "expected": round(expected, 2),
                "confidence_low": round(max(0, expected - volatility), 2),
                "confidence_high": round(expected + volatility, 2)
            })
        
        std_dev = statistics.stdev([f["expected"] for f in forecast]) if len(forecast) > 1 else 0.0
        methodology = (
            "Based on pending settlement dates and historical 2-day settlement pattern with 15% volatility"
            if projected_any else
            "Projected from average daily settlement velocity over the last 14 processed settlements"
        )
        
        return {
            "forecast": forecast,
            "total_expected": round(total, 2),
            "confidence_range": {
                "low": round(max(0, total - 1.96 * std_dev * math.sqrt(days)), 2),
                "high": round(total + 1.96 * std_dev * math.sqrt(days), 2)
            },
            "methodology": methodology
        }
    
    def get_finance_insights(self) -> List[Dict[str, Any]]:
        insights = []
        payments = self.db.query(Payment).all()
        
        total = len(payments)
        if total == 0:
            return insights
        
        failed_count = sum(1 for p in payments if p.payment_status == PaymentStatus.FAILED)
        failed_rate = failed_count / total * 100
        
        if failed_rate > 5:
            insights.append({
                "title": "Payment Failure Rate Elevated",
                "description": f"Failure rate is {failed_rate:.1f}% (threshold: 5%). {failed_count} of {total} payments failed.",
                "type": "alert",
                "impact": "high",
                "metric": f"Failure rate: {failed_rate:.1f}%"
            })
        
        refund_count = sum(1 for p in payments if p.refund_amount > 0)
        refund_rate = refund_count / total * 100
        
        if refund_rate > 10:
            insights.append({
                "title": "Refund Rate Above Normal",
                "description": f"Refund rate is {refund_rate:.1f}% with {refund_count} refunded payments.",
                "type": "warning",
                "impact": "medium",
                "metric": f"Refund rate: {refund_rate:.1f}%"
            })
        
        pending_count = sum(1 for p in payments if p.payment_status == PaymentStatus.PENDING)
        if pending_count > total * 0.15:
            insights.append({
                "title": "High Pending Payment Volume",
                "description": f"{pending_count} payments ({pending_count/total*100:.1f}%) are still pending.",
                "type": "warning",
                "impact": "medium",
                "metric": f"Pending: {pending_count} payments"
            })
        
        missing_settlements = sum(1 for p in payments if p.settlement_status == SettlementStatus.MISSING)
        if missing_settlements > 0:
            insights.append({
                "title": "Missing Settlement Records",
                "description": f"{missing_settlements} captured payments have no settlement record.",
                "type": "alert",
                "impact": "high",
                "metric": f"Missing: {missing_settlements} settlements"
            })
        
        method_performance = {}
        for p in payments:
            if p.payment_method not in method_performance:
                method_performance[p.payment_method] = {"total": 0, "failed": 0}
            method_performance[p.payment_method]["total"] += 1
            if p.payment_status == PaymentStatus.FAILED:
                method_performance[p.payment_method]["failed"] += 1
        
        for method, stats in method_performance.items():
            if stats["total"] > 5:
                rate = stats["failed"] / stats["total"] * 100
                if rate > 10:
                    insights.append({
                        "title": f"High Failure Rate: {method.upper()}",
                        "description": f"{method} has {rate:.1f}% failure rate ({stats['failed']}/{stats['total']}).",
                        "type": "warning",
                        "impact": "medium",
                        "metric": f"{method} failure rate: {rate:.1f}%"
                    })
        
        amounts = [p.amount for p in payments if p.payment_status == PaymentStatus.CAPTURED]
        if amounts:
            avg_amount = statistics.mean(amounts)
            std_amount = statistics.stdev(amounts) if len(amounts) > 1 else 0
            large_payments = [p for p in payments if p.payment_status == PaymentStatus.CAPTURED and p.amount > avg_amount + 2 * std_amount]
            if large_payments:
                insights.append({
                    "title": "Unusually Large Transactions Detected",
                    "description": f"{len(large_payments)} transactions exceed 2 standard deviations from mean (₹{avg_amount:,.0f}).",
                    "type": "info",
                    "impact": "low",
                    "metric": f"Mean: ₹{avg_amount:,.0f}, Threshold: ₹{avg_amount + 2*std_amount:,.0f}"
                })
        
        return insights
    
    def get_daily_finance_brief(self) -> Dict[str, Any]:
        today = datetime.now().date()
        today_payments = [p for p in self.db.query(Payment).all() if p.created_at.date() == today]
        
        collected = sum(p.amount for p in today_payments if p.payment_status == PaymentStatus.CAPTURED)
        success_count = sum(1 for p in today_payments if p.payment_status == PaymentStatus.CAPTURED)
        total_today = len(today_payments)
        success_rate = round((success_count / total_today * 100) if total_today > 0 else 0, 1)
        refunded = sum(p.refund_amount for p in today_payments)
        pending = sum(p.amount for p in today_payments if p.payment_status == PaymentStatus.PENDING)
        
        exceptions = self.find_exceptions()
        
        # Compute match rate in-memory (no side-effectful DB writes on every brief).
        all_results = [self.reconciliation_engine.reconcile_payment(p) for p in self.db.query(Payment).all()]
        if all_results:
            matched = sum(1 for r in all_results if r["status"] == ReconciliationStatus.MATCHED)
            match_rate = round(matched / len(all_results) * 100, 1)
        else:
            match_rate = 0.0
        
        top_priorities = []
        critical = [e for e in exceptions if e.severity == ExceptionSeverity.CRITICAL]
        high = [e for e in exceptions if e.severity == ExceptionSeverity.HIGH]
        
        for e in critical[:2]:
            top_priorities.append(f"CRITICAL: {e.reason}")
        for e in high[:3]:
            top_priorities.append(f"HIGH: {e.reason}")
        
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        
        return {
            "greeting": greeting,
            "collected": collected,
            "success_rate": success_rate,
            "refunded": refunded,
            "pending_settlement": pending,
            "match_rate": match_rate,
            "top_priorities": top_priorities[:5]
        }
    
    def get_money_flow(self) -> Dict[str, Any]:
        cash_pos = self.calculate_cash_position()
        
        breakdown = {
            "collected": cash_pos["captured_total"],
            "successfully_settled": cash_pos["settled_cash"],
            "refunds": cash_pos["refunded"],
            "processing_fees": cash_pos["fees_paid"],
            "pending_settlement": cash_pos["pending_settlement"],
            "unresolved": cash_pos["unresolved"]
        }
        
        explanation = self._generate_money_flow_explanation(breakdown)
        
        return {
            "collected": cash_pos["captured_total"],
            "settled": cash_pos["settled_cash"],
            "refunds": cash_pos["refunded"],
            "fees": cash_pos["fees_paid"],
            "pending": cash_pos["pending_settlement"],
            "unresolved": cash_pos["unresolved"],
            "explanation": explanation,
            "breakdown": breakdown
        }
    
    def _generate_money_flow_explanation(self, breakdown: Dict) -> str:
        parts = []
        parts.append(f"Total collected: ₹{breakdown['collected']:,.2f}")
        parts.append(f"Successfully settled: ₹{breakdown['successfully_settled']:,.2f}")
        parts.append(f"Processing fees deducted: ₹{breakdown['processing_fees']:,.2f}")
        parts.append(f"Refunds issued: ₹{breakdown['refunds']:,.2f}")
        
        if breakdown['pending_settlement'] > 0:
            parts.append(f"Pending settlement: ₹{breakdown['pending_settlement']:,.2f}")
        if breakdown['unresolved'] > 0:
            parts.append(f"Unresolved discrepancies: ₹{breakdown['unresolved']:,.2f}")
        
        net = breakdown['collected'] - breakdown['refunds'] - breakdown['processing_fees']
        parts.append(f"Net expected: ₹{net:,.2f}")
        
        return " | ".join(parts)
    
    def get_actions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "mark_review", "name": "Mark for Review", "description": "Flag exception for manual review"},
            {"id": "create_note", "name": "Create Investigation Note", "description": "Add note to exception"},
            {"id": "categorize", "name": "Categorize as Explainable", "description": "Mark discrepancy as understood"},
            {"id": "export", "name": "Export Report", "description": "Download reconciliation report"},
            {"id": "flag_suspicious", "name": "Flag Suspicious", "description": "Mark transaction as suspicious"}
        ]
    
    def _payment_to_dict(self, p: Payment) -> Dict[str, Any]:
        return {
            "id": p.id,
            "payment_id": p.payment_id,
            "order_id": p.order_id,
            "customer_id": p.customer_id,
            "customer_email": p.customer_email,
            "customer_name": p.customer_name,
            "amount": p.amount,
            "currency": p.currency,
            "payment_status": p.payment_status.value,
            "payment_method": p.payment_method,
            "fee": p.fee,
            "tax": p.tax,
            "refund_amount": p.refund_amount,
            "refund_status": p.refund_status.value,
            "settlement_id": p.settlement_id,
            "settlement_amount": p.settlement_amount,
            "settlement_status": p.settlement_status.value,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "settlement_date": p.settlement_date.isoformat() if p.settlement_date else None,
            "description": p.description
        }
    
    def _settlement_to_dict(self, s: Settlement) -> Dict[str, Any]:
        return {
            "id": s.id,
            "settlement_id": s.settlement_id,
            "expected_amount": s.expected_amount,
            "actual_amount": s.actual_amount,
            "discrepancy": s.discrepancy,
            "payment_count": s.payment_count,
            "fee_total": s.fee_total,
            "refund_total": s.refund_total,
            "processed_at": s.processed_at.isoformat() if s.processed_at else None,
            "status": s.status.value
        }
    
    def _refund_to_dict(self, r: Refund) -> Dict[str, Any]:
        return {
            "id": r.id,
            "refund_id": r.refund_id,
            "payment_id": r.payment_id,
            "order_id": r.order_id,
            "original_amount": r.original_amount,
            "refund_amount": r.refund_amount,
            "refund_status": r.refund_status.value,
            "customer_email": r.customer_email,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }