import os
import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


def _parse_occurred_at(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = f"{cleaned[:-1]}+00:00"

        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
    except ValueError:
        return None


def _money(value: Decimal) -> str:
    return format(value, ".2f")


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _safe_day(year: int, month: int, due_day: int) -> int:
    max_day = calendar.monthrange(year, month)[1]
    return max(1, min(due_day, max_day))


def _next_monthly_due(due_day: int, today: date) -> date:
    this_month_due = date(today.year, today.month, _safe_day(today.year, today.month, due_day))
    if this_month_due >= today:
        return this_month_due

    if today.month == 12:
        next_year, next_month = today.year + 1, 1
    else:
        next_year, next_month = today.year, today.month + 1

    return date(next_year, next_month, _safe_day(next_year, next_month, due_day))


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-key-change-me"),
        SQLALCHEMY_DATABASE_URI=_database_url(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register model metadata for migrations.
    from models import Account, RecurringBill, Transaction  # noqa: F401

    @app.get("/")
    def home():
        return "CyFi, active!"

    @app.get("/health/db")
    def db_health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"database": "ok"}), 200
        except Exception as exc:
            return jsonify({"database": "error", "detail": str(exc)}), 500

    @app.post("/api/transactions")
    def add_transaction():
        payload = request.get_json(silent=True) or {}
        required_fields = ["account_id", "transaction_name", "amount", "category", "transaction_type"]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        account = db.session.get(Account, payload["account_id"])
        if account is None:
            return jsonify({"error": "Account not found"}), 404

        try:
            amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "amount must be numeric"}), 400

        if amount <= 0:
            return jsonify({"error": "amount must be greater than zero"}), 400

        transaction_type = str(payload["transaction_type"]).strip().lower()
        if transaction_type in {"expense", "debit"}:
            balance_delta = -amount
        elif transaction_type in {"income", "credit", "deposit"}:
            balance_delta = amount
        else:
            return jsonify({"error": "transaction_type must be expense/debit or income/credit/deposit"}), 400

        occurred_at = _parse_occurred_at(payload.get("occurred_at"))
        if payload.get("occurred_at") and occurred_at is None:
            return jsonify({"error": "occurred_at must be valid ISO datetime"}), 400

        transaction = Transaction(
            account_id=account.id,
            transaction_name=str(payload["transaction_name"]).strip(),
            amount=amount,
            category=str(payload["category"]).strip(),
            transaction_type=transaction_type,
            note=str(payload.get("note", "")).strip() or None,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )

        account.current_balance = (account.current_balance or Decimal("0.00")) + balance_delta

        db.session.add(transaction)
        db.session.commit()

        return (
            jsonify(
                {
                    "transaction": {
                        "id": transaction.id,
                        "account_id": transaction.account_id,
                        "transaction_name": transaction.transaction_name,
                        "amount": _money(transaction.amount),
                        "category": transaction.category,
                        "transaction_type": transaction.transaction_type,
                        "note": transaction.note,
                        "occurred_at": _serialize_datetime(transaction.occurred_at),
                    },
                    "account": {
                        "id": account.id,
                        "name": account.name,
                        "current_balance": _money(account.current_balance),
                    },
                }
            ),
            201,
        )

    @app.get("/api/transactions/recent")
    def list_recent_transactions():
        limit = request.args.get("limit", default=20, type=int)
        if limit is None or limit < 1:
            limit = 20
        limit = min(limit, 100)

        items = (
            Transaction.query.order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .limit(limit)
            .all()
        )

        return jsonify(
            {
                "transactions": [
                    {
                        "id": tx.id,
                        "account_id": tx.account_id,
                        "transaction_name": tx.transaction_name,
                        "amount": _money(tx.amount),
                        "category": tx.category,
                        "transaction_type": tx.transaction_type,
                        "note": tx.note,
                        "occurred_at": _serialize_datetime(tx.occurred_at),
                    }
                    for tx in items
                ]
            }
        )

    @app.get("/api/accounts/summary")
    def account_summaries():
        accounts = Account.query.order_by(Account.name.asc()).all()
        total_balance = sum((account.current_balance or Decimal("0.00") for account in accounts), Decimal("0.00"))

        return jsonify(
            {
                "total_balance": _money(total_balance),
                "accounts": [
                    {
                        "id": account.id,
                        "name": account.name,
                        "account_type": account.account_type,
                        "starting_balance": _money(account.starting_balance),
                        "current_balance": _money(account.current_balance),
                    }
                    for account in accounts
                ],
            }
        )

    @app.get("/api/bills/upcoming")
    def upcoming_bills():
        days = request.args.get("days", default=30, type=int)
        if days is None or days < 1:
            days = 30
        days = min(days, 365)

        today = date.today()
        window_end = today + timedelta(days=days)

        bills = RecurringBill.query.filter_by(active=True).order_by(RecurringBill.due_day.asc()).all()

        upcoming = []
        for bill in bills:
            next_due = _next_monthly_due(bill.due_day, today)
            if next_due > window_end:
                continue

            upcoming.append(
                {
                    "id": bill.id,
                    "account_id": bill.account_id,
                    "name": bill.name,
                    "amount": _money(bill.amount),
                    "category": bill.category,
                    "frequency": bill.frequency,
                    "due_day": bill.due_day,
                    "next_due_date": next_due.isoformat(),
                    "days_until_due": (next_due - today).days,
                }
            )

        upcoming.sort(key=lambda item: item["next_due_date"])
        return jsonify({"days": days, "bills": upcoming})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
