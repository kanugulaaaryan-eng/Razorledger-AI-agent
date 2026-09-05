"""
Unit tests for razorpay_client.py and sync_service.py using mocked httpx.

These tests do NOT hit the real Razorpay API (no network access is required
or attempted). They verify:
  - RazorpayClient behavior when unconfigured / configured / rejected (401).
  - mode / key_id_last4 derivation from key prefixes.
  - SyncService status/test_and_mark_connected/sync_all against a mocked
    RazorpayClient, including the paise -> rupees field-mapping in
    sync_service._upsert_payments/_upsert_refunds/_upsert_settlements.

Run with:
    cd backend
    PYTHONPATH=. pytest tests/test_razorpay_sync.py -v
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from models import Base, Payment, Settlement, Refund, RazorpayConnection
from razorpay_client import RazorpayClient, RazorpayConfigError
from sync_service import SyncService, _paise_to_rupees


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite DB per test, isolated from the app's real DB."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clean_razorpay_env(monkeypatch):
    """Ensure tests never accidentally read real credentials from the
    environment / a developer's local backend/.env."""
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    yield


def _sample_payment_item(**overrides):
    item = {
        "id": "pay_TESTid001",
        "order_id": "order_TESTid001",
        "customer_id": None,
        "contact": "+919999999999",
        "email": "buyer@example.com",
        "amount": 150000,        # paise -> 1500.00 rupees
        "fee": 3500,             # paise -> 35.00 rupees
        "tax": 630,              # paise -> 6.30 rupees
        "amount_refunded": 0,
        "currency": "INR",
        "status": "captured",
        "method": "upi",
        "created_at": 1710000000,
        "description": "Test order",
        "notes": {"name": "Test Customer"},
    }
    item.update(overrides)
    return item


def _sample_refund_item(**overrides):
    item = {
        "id": "rfnd_TESTid001",
        "payment_id": "pay_TESTid001",
        "amount": 50000,  # paise -> 500.00 rupees
        "status": "processed",
        "created_at": 1710000500,
        "notes": {"order_id": "order_TESTid001"},
    }
    item.update(overrides)
    return item


def _sample_settlement_item(**overrides):
    item = {
        "id": "setl_TESTid001",
        "amount": 146500,  # paise -> 1465.00 rupees (net of fee+tax)
        "fees": 3500,      # paise -> 35.00
        "tax": 630,        # paise -> 6.30
        "status": "processed",
        "created_at": 1710003600,
    }
    item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# RazorpayClient
# ---------------------------------------------------------------------------

class TestRazorpayClientConfig:
    def test_unconfigured_when_no_env(self):
        client = RazorpayClient()
        assert client.is_configured is False
        assert client.key_id_last4 is None
        assert client.mode == "unknown"

    def test_configured_when_env_set(self, monkeypatch):
        monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_ABCD1234")
        monkeypatch.setenv("RAZORPAY_KEY_SECRET", "supersecret")
        client = RazorpayClient()
        assert client.is_configured is True
        assert client.mode == "test"
        assert client.key_id_last4 == "1234"

    def test_live_mode_prefix(self, monkeypatch):
        monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_WXYZ9999")
        monkeypatch.setenv("RAZORPAY_KEY_SECRET", "supersecret")
        client = RazorpayClient()
        assert client.mode == "live"

    def test_get_raises_config_error_when_unconfigured(self):
        client = RazorpayClient()
        with pytest.raises(RazorpayConfigError):
            client._get("/payments", params={"count": 1})


class TestRazorpayClientHTTP:
    """Mocks httpx.Client so no real network call is made."""

    def _mock_client_context(self, mock_get_response):
        mock_httpx_client = MagicMock()
        mock_httpx_client.get.return_value = mock_get_response
        mock_httpx_client.__enter__.return_value = mock_httpx_client
        mock_httpx_client.__exit__.return_value = False
        return mock_httpx_client

    def test_test_connection_success(self, monkeypatch):
        monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_ABCD1234")
        monkeypatch.setenv("RAZORPAY_KEY_SECRET", "supersecret")
        client = RazorpayClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": [{"id": "pay_1"}]}
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.Client", return_value=self._mock_client_context(mock_resp)):
            result = client.test_connection()

        assert result["ok"] is True
        assert result["mode"] == "test"
        assert result["key_id_last4"] == "1234"
        assert result["sample_count"] == 1

    def test_401_raises_config_error(self, monkeypatch):
        monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_BADKEY01")
        monkeypatch.setenv("RAZORPAY_KEY_SECRET", "wrongsecret")
        client = RazorpayClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("httpx.Client", return_value=self._mock_client_context(mock_resp)):
            with pytest.raises(RazorpayConfigError, match="401"):
                client.test_connection()

    def test_fetch_payments_returns_items(self, monkeypatch):
        monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_ABCD1234")
        monkeypatch.setenv("RAZORPAY_KEY_SECRET", "supersecret")
        client = RazorpayClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": [_sample_payment_item()]}
        mock_resp.raise_for_status.return_value = None

        with patch("httpx.Client", return_value=self._mock_client_context(mock_resp)):
            items = client.fetch_payments(count=1)

        assert len(items) == 1
        assert items[0]["id"] == "pay_TESTid001"


# ---------------------------------------------------------------------------
# _paise_to_rupees
# ---------------------------------------------------------------------------

class TestPaiseToRupees:
    def test_none_is_zero(self):
        assert _paise_to_rupees(None) == 0.0

    def test_conversion(self):
        assert _paise_to_rupees(150000) == 1500.00

    def test_rounding(self):
        assert _paise_to_rupees(333) == 3.33


# ---------------------------------------------------------------------------
# SyncService — status / connect (mocked RazorpayClient, no network)
# ---------------------------------------------------------------------------

class TestSyncServiceConnection:
    def test_status_unconfigured(self, db_session):
        svc = SyncService(db_session)
        status = svc.status()
        assert status["configured"] is False
        assert status["connected"] is False

    def test_test_and_mark_connected_unconfigured(self, db_session):
        svc = SyncService(db_session)
        result = svc.test_and_mark_connected()
        assert result["connected"] is False
        assert "not set" in result["error"]

    def test_test_and_mark_connected_success(self, db_session, monkeypatch):
        svc = SyncService(db_session)
        svc.client = MagicMock()
        svc.client.is_configured = True
        svc.client.test_connection.return_value = {"mode": "test", "key_id_last4": "1234"}

        result = svc.test_and_mark_connected()

        assert result["connected"] is True
        conn = db_session.query(RazorpayConnection).first()
        assert conn.is_connected == 1
        assert conn.mode == "test"

    def test_test_and_mark_connected_rejected(self, db_session):
        svc = SyncService(db_session)
        svc.client = MagicMock()
        svc.client.is_configured = True
        svc.client.test_connection.side_effect = RazorpayConfigError("401 Unauthorized")

        result = svc.test_and_mark_connected()

        assert result["connected"] is False
        conn = db_session.query(RazorpayConnection).first()
        assert conn.is_connected == 0
        assert "401" in conn.last_sync_error


# ---------------------------------------------------------------------------
# SyncService — sync_all / upserts (mocked RazorpayClient, no network)
# ---------------------------------------------------------------------------

class TestSyncServiceSyncAll:
    def test_sync_all_unconfigured_leaves_data_untouched(self, db_session):
        svc = SyncService(db_session)
        result = svc.sync_all()
        assert result["last_sync_status"] == "failed"
        assert db_session.query(Payment).count() == 0

    def test_sync_all_upserts_paise_to_rupees_correctly(self, db_session):
        svc = SyncService(db_session)
        svc.client = MagicMock()
        svc.client.is_configured = True
        svc.client.fetch_payments.return_value = [_sample_payment_item()]
        svc.client.fetch_refunds.return_value = [_sample_refund_item()]
        svc.client.fetch_settlements.return_value = [_sample_settlement_item()]

        result = svc.sync_all()

        assert result["last_sync_status"] == "success"
        assert result["this_sync"] == {"payments": 1, "refunds": 1, "settlements": 1}

        payment = db_session.query(Payment).filter(Payment.payment_id == "pay_TESTid001").first()
        assert payment is not None
        assert payment.amount == 1500.00  # 150000 paise
        assert payment.fee == 35.00
        assert payment.tax == 6.30
        assert payment.is_synthetic == 0
        assert payment.customer_email == "buyer@example.com"

        refund = db_session.query(Refund).filter(Refund.refund_id == "rfnd_TESTid001").first()
        assert refund is not None
        assert refund.refund_amount == 500.00
        assert refund.is_synthetic == 0

        settlement = db_session.query(Settlement).filter(Settlement.settlement_id == "setl_TESTid001").first()
        assert settlement is not None
        assert settlement.actual_amount == 1465.00
        assert settlement.fee_total == 35.00
        assert settlement.is_synthetic == 0

    def test_sync_all_is_idempotent_upsert_not_duplicate(self, db_session):
        """Running sync twice with the same Razorpay IDs must update, not
        duplicate, rows (safe to run repeatedly)."""
        svc = SyncService(db_session)
        svc.client = MagicMock()
        svc.client.is_configured = True
        svc.client.fetch_payments.return_value = [_sample_payment_item()]
        svc.client.fetch_refunds.return_value = []
        svc.client.fetch_settlements.return_value = []

        svc.sync_all()
        # Second sync: same payment id, amount changed upstream (e.g. partial refund).
        svc.client.fetch_payments.return_value = [_sample_payment_item(amount_refunded=50000)]
        svc.sync_all()

        payments = db_session.query(Payment).filter(Payment.payment_id == "pay_TESTid001").all()
        assert len(payments) == 1
        assert payments[0].refund_amount == 500.00

    def test_sync_all_network_error_records_failure_without_crashing(self, db_session):
        svc = SyncService(db_session)
        svc.client = MagicMock()
        svc.client.is_configured = True
        svc.client.fetch_payments.side_effect = RazorpayConfigError("Razorpay rejected the API key/secret (401 Unauthorized).")

        result = svc.sync_all()

        assert result["last_sync_status"] == "failed"
        assert "401" in result["last_sync_error"]
        conn = db_session.query(RazorpayConnection).first()
        assert conn.is_connected == 0

    def test_sync_all_unexpected_exception_is_caught(self, db_session):
        svc = SyncService(db_session)
        svc.client = MagicMock()
        svc.client.is_configured = True
        svc.client.fetch_payments.side_effect = RuntimeError("connection reset")

        result = svc.sync_all()

        assert result["last_sync_status"] == "failed"
        assert "connection reset" in result["last_sync_error"]
