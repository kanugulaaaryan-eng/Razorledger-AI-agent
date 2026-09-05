import random
from datetime import datetime, timedelta
from faker import Faker
from models import Payment, Settlement, Refund, Exception as Exc, ReconciliationResult, AuditLog, PaymentStatus, SettlementStatus, RefundStatus, ExceptionSeverity
from database import SessionLocal, init_db

fake = Faker('en_IN')

PAYMENT_METHODS = ['upi', 'card', 'netbanking', 'wallet', 'emi']
STATUSES = [PaymentStatus.CAPTURED, PaymentStatus.PENDING, PaymentStatus.FAILED, PaymentStatus.REFUNDED, PaymentStatus.AUTHORIZED]
SETTLEMENT_STATUSES = [SettlementStatus.PROCESSED, SettlementStatus.PENDING, SettlementStatus.MISSING, SettlementStatus.REFUNDED, SettlementStatus.NOT_SETTLED]
REFUND_STATUSES = [RefundStatus.PROCESSED, RefundStatus.PENDING, RefundStatus.FAILED, RefundStatus.PARTIAL]

def generate_synthetic_payments(count: int = 120):
    payments = []
    base_date = datetime.now() - timedelta(days=60)
    
    for i in range(count):
        payment_id = f"pay_{fake.unique.bothify(text='??#########')}"
        order_id = f"order_{fake.unique.bothify(text='??#########')}"
        customer_id = f"cust_{fake.unique.bothify(text='########')}"
        customer_email = fake.email()
        customer_name = fake.name()
        
        amount = round(random.uniform(100, 50000), 2)
        currency = "INR"
        payment_method = random.choice(PAYMENT_METHODS)
        
        base_fee = round(amount * random.uniform(0.015, 0.025), 2)
        tax = round(base_fee * 0.18, 2)
        fee = base_fee
        
        payment_status = random.choices(
            STATUSES,
            weights=[0.70, 0.10, 0.08, 0.08, 0.04]
        )[0]
        
        refund_amount = 0.0
        refund_status = RefundStatus.PENDING
        
        if payment_status == PaymentStatus.REFUNDED:
            refund_amount = amount
            refund_status = RefundStatus.PROCESSED
        elif payment_status == PaymentStatus.CAPTURED and random.random() < 0.05:
            refund_amount = round(amount * random.uniform(0.1, 0.5), 2)
            refund_status = RefundStatus.PARTIAL
        
        settlement_id = None
        settlement_amount = 0.0
        settlement_status = SettlementStatus.NOT_SETTLED
        settlement_date = None
        
        if payment_status in [PaymentStatus.CAPTURED, PaymentStatus.REFUNDED]:
            if random.random() < 0.85:
                settlement_id = f"sett_{fake.unique.bothify(text='??#########')}"
                settlement_amount = amount - fee - tax - refund_amount
                if settlement_amount < 0:
                    settlement_amount = 0
                settlement_status = SettlementStatus.PROCESSED
                settlement_date = base_date + timedelta(days=random.randint(1, 5))
            elif random.random() < 0.5:
                settlement_status = SettlementStatus.PENDING
            else:
                settlement_status = SettlementStatus.MISSING
        
        created_at = base_date + timedelta(
            days=random.randint(0, 60),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        description = fake.sentence(nb_words=6)
        
        payment = Payment(
            payment_id=payment_id,
            order_id=order_id,
            customer_id=customer_id,
            customer_email=customer_email,
            customer_name=customer_name,
            amount=amount,
            currency=currency,
            payment_status=payment_status,
            payment_method=payment_method,
            fee=fee,
            tax=tax,
            refund_amount=refund_amount,
            refund_status=refund_status,
            settlement_id=settlement_id,
            settlement_amount=settlement_amount,
            settlement_status=settlement_status,
            created_at=created_at,
            settlement_date=settlement_date,
            description=description,
            is_synthetic=1
        )
        payments.append(payment)
    
    return payments


def generate_synthetic_settlements(payments):
    settlements_by_id = {}
    
    for p in payments:
        if p.settlement_id and p.settlement_id not in settlements_by_id:
            settlements_by_id[p.settlement_id] = {
                'settlement_id': p.settlement_id,
                'expected': 0.0,
                'actual': 0.0,
                'fee_total': 0.0,
                'refund_total': 0.0,
                'payments': [],
                'processed_at': p.created_at + timedelta(days=random.randint(1, 3))
            }
        
        if p.settlement_id:
            # expected is the NET amount the provider should have settled
            # (gross minus fees/tax/refunds), compared against the actual
            # settlement_amount credited to the merchant.
            settlements_by_id[p.settlement_id]['expected'] += p.amount - p.fee - p.tax - p.refund_amount
            settlements_by_id[p.settlement_id]['actual'] += p.settlement_amount
            settlements_by_id[p.settlement_id]['fee_total'] += p.fee
            settlements_by_id[p.settlement_id]['refund_total'] += p.refund_amount
            settlements_by_id[p.settlement_id]['payments'].append(p.payment_id)
    
    settlements = []
    for s in settlements_by_id.values():
        discrepancy = round(s['actual'] - s['expected'], 2)
        settlement = Settlement(
            settlement_id=s['settlement_id'],
            expected_amount=round(s['expected'], 2),
            actual_amount=round(s['actual'], 2),
            discrepancy=discrepancy,
            payment_count=len(s['payments']), 
            fee_total=round(s['fee_total'], 2),
            refund_total=round(s['refund_total'], 2),
            processed_at=s['processed_at'],
            status=SettlementStatus.PROCESSED if abs(discrepancy) < 0.5 else SettlementStatus.PENDING,
            is_synthetic=1
        )
        settlements.append(settlement)
    
    return settlements


def generate_synthetic_refunds(payments):
    refunds = []
    for p in payments:
        if p.refund_amount > 0:
            refund = Refund(
                refund_id=f"rfnd_{fake.unique.bothify(text='??#########')}",
                payment_id=p.payment_id,
                order_id=p.order_id,
                original_amount=p.amount,
                refund_amount=p.refund_amount,
                refund_status=p.refund_status,
                customer_email=p.customer_email,
                created_at=p.created_at + timedelta(hours=random.randint(1, 48)),
                is_synthetic=1
            )
            refunds.append(refund)
    return refunds


def seed_database():
    init_db()
    db = SessionLocal()
    
    try:
        db.query(Payment).delete()
        db.query(Settlement).delete()
        db.query(Refund).delete()
        db.query(Exc).delete()
        db.query(ReconciliationResult).delete()
        db.query(AuditLog).delete()
        db.commit()
        
        payments = generate_synthetic_payments(120)
        for p in payments:
            db.add(p)
        db.commit()
        
        settlements = generate_synthetic_settlements(payments)
        for s in settlements:
            db.add(s)
        db.commit()
        
        refunds = generate_synthetic_refunds(payments)
        for r in refunds:
            db.add(r)
        db.commit()
        
        from reconciliation import ReconciliationEngine
        engine = ReconciliationEngine(db)
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        engine.run_reconciliation(batch_id)
        
        # find_exceptions() persists new open exceptions itself (and dedupes).
        from finance_tools import FinanceTools
        tools = FinanceTools(db)
        exceptions = tools.find_exceptions()
        
        return {
            "payments": len(payments),
            "settlements": len(settlements),
            "exceptions": len(exceptions)
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = seed_database()
    print(f"Seeded: {result}")