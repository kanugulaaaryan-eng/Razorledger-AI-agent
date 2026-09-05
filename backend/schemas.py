from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class PaymentStatus(str, Enum):
    CAPTURED = "captured"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    AUTHORIZED = "authorized"


class SettlementStatus(str, Enum):
    PROCESSED = "processed"
    PENDING = "pending"
    MISSING = "missing"
    REFUNDED = "refunded"
    NOT_SETTLED = "not_settled"


class RefundStatus(str, Enum):
    PROCESSED = "processed"
    PENDING = "pending"
    FAILED = "failed"
    PARTIAL = "partial"


class ReconciliationStatus(str, Enum):
    MATCHED = "matched"
    EXPLAINABLE = "explainable"
    REVIEW = "review"
    UNRESOLVED = "unresolved"
    DUPLICATE = "duplicate"


class ExceptionSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PaymentResponse(BaseModel):
    id: int
    payment_id: str
    order_id: str
    customer_id: str
    customer_email: Optional[str]
    customer_name: Optional[str]
    amount: float
    currency: str
    payment_status: PaymentStatus
    payment_method: str
    fee: float
    tax: float
    refund_amount: float
    refund_status: RefundStatus
    settlement_id: Optional[str]
    settlement_amount: float
    settlement_status: SettlementStatus
    created_at: datetime
    settlement_date: Optional[datetime]
    description: Optional[str]
    reconciliation_status: Optional[str] = None
    ai_diagnosis: Optional[str] = None
    confidence: Optional[float] = None
    recommended_action: Optional[str] = None

    class Config:
        from_attributes = True


class SettlementResponse(BaseModel):
    id: int
    settlement_id: str
    expected_amount: float
    actual_amount: float
    discrepancy: float
    payment_count: int
    fee_total: float
    refund_total: float
    processed_at: datetime
    status: SettlementStatus

    class Config:
        from_attributes = True


class RefundResponse(BaseModel):
    id: int
    refund_id: str
    payment_id: str
    order_id: str
    original_amount: float
    refund_amount: float
    refund_status: RefundStatus
    customer_email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ExceptionResponse(BaseModel):
    id: int
    exception_id: str
    exception_type: str
    severity: ExceptionSeverity
    payment_id: Optional[str]
    settlement_id: Optional[str]
    amount: float
    reason: str
    evidence: Optional[str]
    confidence: float
    recommended_action: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReconciliationResultResponse(BaseModel):
    payment_id: str
    amount: float
    status: ReconciliationStatus
    reason: str
    discrepancy: float
    confidence: float
    recommended_action: str


class ReconciliationBatchResponse(BaseModel):
    batch_id: str
    statistics: "ReconciliationStatistics"
    results: List[ReconciliationResultResponse]


class ReconciliationStatistics(BaseModel):
    total_records: int
    matched: int
    explainable: int
    review_required: int
    unresolved: int
    flagged: int
    match_rate: float
    total_amount: float
    total_settled: float
    total_refunds: float
    total_fees: float
    total_pending: float
    total_unresolved: float


class CashPositionResponse(BaseModel):
    captured_total: float
    settled_cash: float
    available_cash: float
    pending_settlement: float
    refunded: float
    fees_paid: float
    unresolved: float
    expected_incoming: float


class ForecastResponse(BaseModel):
    forecast: List["ForecastPoint"]
    total_expected: float
    confidence_range: "ConfidenceRange"
    methodology: str


class ForecastPoint(BaseModel):
    date: str
    expected: float
    confidence_low: float
    confidence_high: float


class ConfidenceRange(BaseModel):
    low: float
    high: float


class InsightResponse(BaseModel):
    title: str
    description: str
    type: str
    impact: str
    metric: str


class DailyBriefResponse(BaseModel):
    greeting: str
    collected: float
    success_rate: float
    refunded: float
    pending_settlement: float
    match_rate: float
    top_priorities: List[str]


class MoneyFlowResponse(BaseModel):
    collected: float
    settled: float
    refunds: float
    fees: float
    pending: float
    unresolved: float
    explanation: str
    breakdown: Dict[str, Any]


class AIChatRequest(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    response: str
    tools_used: List[str]
    tool_results: List[Dict[str, Any]]
    audit_trail: Dict[str, Any]


class ImportResponse(BaseModel):
    success: bool
    message: str
    records_imported: int
    validation_errors: List[str] = []


class DemoResetResponse(BaseModel):
    generated: Dict[str, int]
    match_rate: float


class EvaluationResponse(BaseModel):
    test_cases: int
    passed: int
    failed: int
    accuracy: float
    details: List[Dict[str, Any]]


class AuditLogResponse(BaseModel):
    id: int
    question: str
    tools_used: List[str]
    records_inspected: int
    confidence: float
    conclusion: str
    created_at: datetime

    class Config:
        from_attributes = True


class OverviewResponse(BaseModel):
    payment_summary: "PaymentSummary"
    reconciliation_stats: ReconciliationStatistics
    cash_position: CashPositionResponse
    exceptions_count: int
    daily_brief: DailyBriefResponse


class PaymentSummary(BaseModel):
    total_payments: int
    successful: int
    pending: int
    failed: int
    refunded: int
    success_rate: float