import sys
from pathlib import Path
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app, db
from models import Account, RecurringBill

app = create_app()

with app.app_context():
    if Account.query.first():
        print("Accounts already exist; skipping seed.")
    else:
        checking = Account(
            name="Checking",
            account_type="checking",
            starting_balance=Decimal("1200.00"),
            current_balance=Decimal("1200.00"),
        )
        savings = Account(
            name="Savings",
            account_type="savings",
            starting_balance=Decimal("5000.00"),
            current_balance=Decimal("5000.00"),
        )
        db.session.add_all([checking, savings])
        db.session.commit()

        db.session.add_all(
            [
                RecurringBill(
                    account_id=checking.id,
                    name="Spotify",
                    amount=Decimal("10.99"),
                    category="Subscription",
                    due_day=13,
                    frequency="monthly",
                ),
                RecurringBill(
                    account_id=checking.id,
                    name="Rent",
                    amount=Decimal("900.00"),
                    category="Housing",
                    due_day=1,
                    frequency="monthly",
                ),
            ]
        )
        db.session.commit()
        print("Seed data created.")
