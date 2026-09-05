from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, Text, Index
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
import enum
from database import Base


class PaymentStatus(str, enum.Enum):
    CAPTURED = "captured"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    AUTHORIZED = "authorized"


class SettlementStatus(str, enum.Enum):
    PROCESSED = "processed"
    PENDING = "pending"
    MISSING = "missing"
    REFUNDED = "refunded"
    NOT_SETTLED = "not_settled"


class RefundStatus(str, enum.Enum):
    PROCESSED = "processed"
    PENDING = "pending"
    FAILED = "failed"
    PARTIAL = "partial"


class ReconciliationStatus(str, enum.Enum):
    MATCHED = "matched"
    EXPLAINABLE = "explainable"
    REVIEW = "review"
    UNRESOLVED = "unresolved"
    DUPLICATE = "duplicate"


class ExceptionSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, index=True, nullable=False)
    order_id = Column(String, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    customer_email = Column(String)
    customer_name = Column(String)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    payment_status = Column(SQLEnum(PaymentStatus), nullable=False)
    payment_method = Column(String, nullable=False)
    fee = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)
    refund_status = Column(SQLEnum(RefundStatus), default=RefundStatus.PENDING)
    settlement_id = Column(String, index=True)
    settlement_amount = Column(Float, default=0.0)
    settlement_status = Column(SQLEnum(SettlementStatus), default=SettlementStatus.NOT_SETTLED)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    settlement_date = Column(DateTime, nullable=True)
    description = Column(Text)
    is_synthetic = Column(Integer, default=1)


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True)
    settlement_id = Column(String, unique=True, index=True, nullable=False)
    expected_amount = Column(Float, nullable=False)
    actual_amount = Column(Float, nullable=False)
    discrepancy = Column(Float, default=0.0)
    payment_count = Column(Integer, default=0)
    fee_total = Column(Float, default=0.0)
    refund_total = Column(Float, default=0.0)
    processed_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(SQLEnum(SettlementStatus), default=SettlementStatus.PROCESSED)
    is_synthetic = Column(Integer, default=1)


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    refund_id = Column(String, unique=True, index=True, nullable=False)
    payment_id = Column(String, index=True, nullable=False)
    order_id = Column(String, index=True, nullable=False)
    original_amount = Column(Float, nullable=False)
    refund_amount = Column(Float, nullable=False)
    refund_status = Column(SQLEnum(RefundStatus), nullable=False)
    customer_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_synthetic = Column(Integer, default=1)


class Exception(Base):
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, index=True)
    exception_id = Column(String, unique=True, index=True, nullable=False)
    exception_type = Column(String, nullable=False)
    severity = Column(SQLEnum(ExceptionSeverity), nullable=False)
    payment_id = Column(String, index=True)
    settlement_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    evidence = Column(Text)
    confidence = Column(Float, default=0.0)
    recommended_action = Column(Text)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    is_synthetic = Column(Integer, default=1)


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True, nullable=False)
    payment_id = Column(String, index=True, nullable=False)
    status = Column(SQLEnum(ReconciliationStatus), nullable=False)
    reason = Column(Text)
    evidence = Column(Text)
    discrepancy = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    recommended_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    tools_used = Column(JSON)
    records_inspected = Column(Integer, default=0)
    calculations = Column(JSON)
    evidence = Column(JSON)
    decision = Column(Text)
    confidence = Column(Float, default=0.0)
    recommended_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_synthetic = Column(Integer, default=1)

    @property
    def conclusion(self) -> str:
        # Frontend/schema expose the AI decision as `conclusion`; the DB
        # column stores it as `decision`. This property bridges the two so
        # /api/audit serializes without a validation error.
        return self.decision or ""


class RazorpayConnection(Base):
    """Tracks the state of the merchant's Razorpay connection.

    Only one row is expected to exist (singleton). Never stores the raw
    API secret - that stays in environment variables only. This table
    just records whether a connection has been verified and sync metadata,
    so the frontend can show Connected/Demo mode and sync history.
    """
    __tablename__ = "razorpay_connection"

    id = Column(Integer, primary_key=True, index=True)
    key_id_last4 = Column(String, nullable=True)
    is_connected = Column(Integer, default=0)
    mode = Column(String, default="test")  # "test" or "live", derived from key prefix
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, nullable=True)  # "success" | "failed" | None
    last_sync_error = Column(Text, nullable=True)
    payments_synced = Column(Integer, default=0)
    settlements_synced = Column(Integer, default=0)
    refunds_synced = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


Index("ix_payments_status_created", Payment.payment_status, Payment.created_at)
Index("ix_settlements_processed", Settlement.processed_at)
Index("ix_exceptions_severity_status", Exception.severity, Exception.status)
Index("ix_audit_created", AuditLog.created_at)