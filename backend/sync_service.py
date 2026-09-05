"""
Data synchronization layer: Razorpay -> local normalized database.

Design:
  Razorpay API (razorpay_client.py)
      -> normalize into existing Payment / Settlement / Refund models
      -> upsert by Razorpay's own IDs (payment_id / settlement_id / refund_id)
      -> safe to run repeatedly (no duplicate rows)
      -> updates RazorpayConnection with last_synced_at / counts / errors

This intentionally reuses the SAME tables Demo Mode seeds into
(models.Payment/Settlement/Refund). Real synced rows are marked
is_synthetic=0 so the UI and FinanceAgent can distinguish demo data from
live merchant data if needed, without maintaining a second set of models.
"""
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from models import Payment, Settlement, Refund, PaymentStatus, SettlementStatus, RefundStatus, RazorpayConnection
from razorpay_client import RazorpayClient, RazorpayConfigError

# Razorpay payment status -> our PaymentStatus
_PAYMENT_STATUS_MAP = {
    "captured": PaymentStatus.CAPTURED,
    "authorized": PaymentStatus.AUTHORIZED,
    "failed": PaymentStatus.FAILED,
    "refunded": PaymentStatus.REFUNDED,
    "created": PaymentStatus.PENDING,
}

_SETTLEMENT_STATUS_MAP = {
    "processed": SettlementStatus.PROCESSED,
    "pending": SettlementStatus.PENDING,
    "failed": SettlementStatus.MISSING,
}

_REFUND_STATUS_MAP = {
    "processed": RefundStatus.PROCESSED,
    "pending": RefundStatus.PENDING,
    "failed": RefundStatus.FAILED,
}


def _paise_to_rupees(amount_paise) -> float:
    if amount_paise is None:
        return 0.0
    return round(float(amount_paise) / 100.0, 2)


class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.client = RazorpayClient()

    def get_or_create_connection(self) -> RazorpayConnection:
        conn = self.db.query(RazorpayConnection).first()
        if not conn:
            conn = RazorpayConnection()
            self.db.add(conn)
            self.db.commit()
            self.db.refresh(conn)
        return conn

    def status(self) -> Dict[str, Any]:
        conn = self.get_or_create_connection()
        configured = self.client.is_configured
        return {
            "configured": configured,
            "connected": bool(conn.is_connected),
            "mode": conn.mode,
            "key_id_last4": conn.key_id_last4,
            "last_synced_at": conn.last_synced_at.isoformat() if conn.last_synced_at else None,
            "last_sync_status": conn.last_sync_status,
            "last_sync_error": conn.last_sync_error,
            "payments_synced": conn.payments_synced,
            "settlements_synced": conn.settlements_synced,
            "refunds_synced": conn.refunds_synced,
        }

    def test_and_mark_connected(self) -> Dict[str, Any]:
        """Verifies credentials against the Razorpay API and records the result.

        Never fakes a successful connection: if the API key/secret is missing
        or rejected, this raises/returns an error and is_connected stays 0.
        """
        conn = self.get_or_create_connection()
        if not self.client.is_configured:
            conn.is_connected = 0
            conn.last_sync_error = "RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set"
            self.db.commit()
            return {"connected": False, "error": conn.last_sync_error}

        try:
            result = self.client.test_connection()
        except RazorpayConfigError as e:
            conn.is_connected = 0
            conn.last_sync_error = str(e)
            self.db.commit()
            return {"connected": False, "error": str(e)}

        conn.is_connected = 1
        conn.mode = result["mode"]
        conn.key_id_last4 = result["key_id_last4"]
        conn.last_sync_error = None
        self.db.commit()
        return {"connected": True, "mode": result["mode"], "key_id_last4": result["key_id_last4"]}

    def sync_all(self) -> Dict[str, Any]:
        """Pulls payments, refunds, and settlements from Razorpay and upserts them.

        Fails gracefully: if Razorpay is unreachable or misconfigured, the
        connection record captures the error and the existing local data
        (demo or previously synced) is left untouched.
        """
        conn = self.get_or_create_connection()

        if not self.client.is_configured:
            conn.last_sync_status = "failed"
            conn.last_sync_error = "Razorpay not configured. Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET."
            conn.last_synced_at = datetime.utcnow()
            self.db.commit()
            return self.status()

        try:
            payments = self.client.fetch_payments(count=100)
            refunds = self.client.fetch_refunds(count=100)
            settlements = self.client.fetch_settlements(count=100)
        except RazorpayConfigError as e:
            conn.is_connected = 0
            conn.last_sync_status = "failed"
            conn.last_sync_error = str(e)
            conn.last_synced_at = datetime.utcnow()
            self.db.commit()
            return self.status()
        except Exception as e:
            conn.last_sync_status = "failed"
            conn.last_sync_error = f"Sync failed: {e}"
            conn.last_synced_at = datetime.utcnow()
            self.db.commit()
            return self.status()

        payments_upserted = self._upsert_payments(payments)
        refunds_upserted = self._upsert_refunds(refunds)
        settlements_upserted = self._upsert_settlements(settlements)

        self.db.commit()

        conn.is_connected = 1
        conn.last_synced_at = datetime.utcnow()
        conn.last_sync_status = "success"
        conn.last_sync_error = None
        conn.payments_synced = self.db.query(Payment).filter(Payment.is_synthetic == 0).count()
        conn.settlements_synced = self.db.query(Settlement).filter(Settlement.is_synthetic == 0).count()
        conn.refunds_synced = self.db.query(Refund).filter(Refund.is_synthetic == 0).count()
        self.db.commit()

        return {
            **self.status(),
            "this_sync": {
                "payments": payments_upserted,
                "refunds": refunds_upserted,
                "settlements": settlements_upserted,
            },
        }

    def _upsert_payments(self, items) -> int:
        count = 0
        for item in items:
            payment_id = item.get("id")
            if not payment_id:
                continue
            existing = self.db.query(Payment).filter(Payment.payment_id == payment_id).first()
            status = _PAYMENT_STATUS_MAP.get(item.get("status"), PaymentStatus.PENDING)
            amount = _paise_to_rupees(item.get("amount"))
            fee = _paise_to_rupees(item.get("fee"))
            tax = _paise_to_rupees(item.get("tax"))
            created_at = datetime.utcfromtimestamp(item["created_at"]) if item.get("created_at") else datetime.utcnow()

            fields = dict(
                order_id=item.get("order_id") or payment_id,
                customer_id=item.get("customer_id") or item.get("contact") or "unknown",
                customer_email=item.get("email"),
                customer_name=item.get("notes", {}).get("name") if isinstance(item.get("notes"), dict) else None,
                amount=amount,
                currency=item.get("currency", "INR"),
                payment_status=status,
                payment_method=item.get("method", "unknown"),
                fee=fee,
                tax=tax,
                refund_amount=_paise_to_rupees(item.get("amount_refunded")),
                created_at=created_at,
                description=item.get("description"),
                is_synthetic=0,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                self.db.add(Payment(payment_id=payment_id, **fields))
            count += 1
        return count

    def _upsert_refunds(self, items) -> int:
        count = 0
        for item in items:
            refund_id = item.get("id")
            if not refund_id:
                continue
            existing = self.db.query(Refund).filter(Refund.refund_id == refund_id).first()
            created_at = datetime.utcfromtimestamp(item["created_at"]) if item.get("created_at") else datetime.utcnow()
            fields = dict(
                payment_id=item.get("payment_id"),
                order_id=item.get("notes", {}).get("order_id") if isinstance(item.get("notes"), dict) else "",
                original_amount=_paise_to_rupees(item.get("amount")),
                refund_amount=_paise_to_rupees(item.get("amount")),
                refund_status=_REFUND_STATUS_MAP.get(item.get("status"), RefundStatus.PENDING),
                created_at=created_at,
                is_synthetic=0,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                self.db.add(Refund(refund_id=refund_id, **fields))
            count += 1
        return count

    def _upsert_settlements(self, items) -> int:
        count = 0
        for item in items:
            settlement_id = item.get("id")
            if not settlement_id:
                continue
            existing = self.db.query(Settlement).filter(Settlement.settlement_id == settlement_id).first()
            processed_at = datetime.utcfromtimestamp(item["created_at"]) if item.get("created_at") else datetime.utcnow()
            actual_amount = _paise_to_rupees(item.get("amount"))
            fee_total = _paise_to_rupees(item.get("fees"))
            tax_total = _paise_to_rupees(item.get("tax"))
            expected_amount = round(actual_amount + fee_total + tax_total, 2)
            fields = dict(
                expected_amount=expected_amount,
                actual_amount=actual_amount,
                discrepancy=round(actual_amount - expected_amount, 2),
                fee_total=fee_total,
                processed_at=processed_at,
                status=_SETTLEMENT_STATUS_MAP.get(item.get("status"), SettlementStatus.PENDING),
                is_synthetic=0,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                self.db.add(Settlement(settlement_id=settlement_id, **fields))
            count += 1
        return count
