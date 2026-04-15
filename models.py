from datetime import datetime, timezone
from decimal import Decimal

from app import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    account_type = db.Column(db.String(30), nullable=False)
    starting_balance = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    current_balance = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    transactions = db.relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    recurring_bills = db.relationship(
        "RecurringBill",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class AccountHistoryEvent(db.Model):
    __tablename__ = "account_history_events"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(80), nullable=False)
    account_balance = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    transaction_name = db.Column(db.String(120), nullable=False, server_default="Transaction")
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    note = db.Column(db.String(255), nullable=True)
    occurred_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    account = db.relationship("Account", back_populates="transactions")


class RecurringBill(db.Model):
    __tablename__ = "recurring_bills"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    due_day = db.Column(db.Integer, nullable=False)
    frequency = db.Column(db.String(20), nullable=False, default="monthly")
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    account = db.relationship("Account", back_populates="recurring_bills")
