import os
import calendar
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from functools import wraps
from hmac import compare_digest

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import inspect, text
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

DEFAULT_SECRET_KEY = "dev-key-change-me"
MAX_USERNAME_LENGTH = 30
MAX_ACCOUNT_NAME_LENGTH = 50
MAX_TRANSACTION_NAME_LENGTH = 50
MAX_CATEGORY_LENGTH = 25
MAX_NOTE_LENGTH = 255


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()

    if not url:
        return "sqlite:///cyfi_local.db"

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


def _parse_due_date(value: str | None) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value.strip())
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


def _safe_next_url(value: str | None) -> str | None:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return None


def _validate_max_length(field_name: str, value: str, max_length: int) -> str | None:
    if len(value) > max_length:
        return f"{field_name} must be {max_length} characters or fewer"
    return None


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


def _is_production() -> bool:
    return os.getenv("FLASK_ENV") == "production"


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
        SQLALCHEMY_DATABASE_URI=_database_url(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_is_production(),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        LOGIN_RATE_LIMIT_ATTEMPTS=5,
        LOGIN_RATE_LIMIT_WINDOW=timedelta(minutes=15),
    )

    if test_config:
        app.config.update(test_config)

    if _is_production() and app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set to a strong random value in production.")

    db.init_app(app)
    migrate.init_app(app, db)

    # Register model metadata for migrations.
    from models import Account, AccountHistoryEvent, RecurringBill, Transaction, User  # noqa: F401

    login_attempts: dict[str, list[datetime]] = {}

    def normalize_username(value: str) -> str:
        return value.strip().lower()

    def login_rate_limit_key(username: str) -> str:
        remote_addr = request.remote_addr or "unknown"
        return f"{remote_addr}:{username or 'blank'}"

    def recent_login_failures(username: str) -> list[datetime]:
        window = app.config["LOGIN_RATE_LIMIT_WINDOW"]
        now = datetime.now(timezone.utc)
        key = login_rate_limit_key(username)
        failures = [failed_at for failed_at in login_attempts.get(key, []) if now - failed_at < window]
        login_attempts[key] = failures
        return failures

    def login_is_rate_limited(username: str) -> bool:
        return len(recent_login_failures(username)) >= app.config["LOGIN_RATE_LIMIT_ATTEMPTS"]

    def record_failed_login(username: str):
        key = login_rate_limit_key(username)
        failures = recent_login_failures(username)
        failures.append(datetime.now(timezone.utc))
        login_attempts[key] = failures

    def clear_failed_logins(username: str):
        login_attempts.pop(login_rate_limit_key(username), None)

    def load_current_user():
        user_id = session.get("user_id")
        if user_id is None:
            return None
        return db.session.get(User, user_id)

    def csrf_token() -> str:
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def submitted_csrf_token() -> str:
        return request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")

    @app.before_request
    def attach_current_user():
        g.user = load_current_user()

    @app.before_request
    def protect_from_csrf():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        if request.path.startswith("/api/") and g.get("user") is None:
            return None

        expected_token = session.get("csrf_token", "")
        sent_token = submitted_csrf_token()
        if expected_token and sent_token and compare_digest(expected_token, sent_token):
            return None

        if request.path.startswith("/api/"):
            return jsonify({"error": "CSRF token missing or invalid"}), 400

        abort(400)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        return response

    @app.context_processor
    def inject_current_user():
        return {"current_user": g.get("user"), "csrf_token": csrf_token}

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if g.user is not None:
                return view(*args, **kwargs)

            if request.path.startswith("/api/"):
                return jsonify({"error": "Login required"}), 401

            return redirect(url_for("login_page", next=request.path))

        return wrapped_view

    def can_record_account_events() -> bool:
        try:
            return inspect(db.session.connection()).has_table("account_history_events")
        except SQLAlchemyError:
            return False

    def record_account_event(action: str, account_name: str, account_balance: Decimal, note: str | None = None):
        if not can_record_account_events():
            return

        db.session.add(
            AccountHistoryEvent(
                user_id=g.user.id if g.get("user") is not None else None,
                action=action,
                account_name=account_name,
                account_balance=account_balance,
                note=note,
            )
        )

    def claim_legacy_data_for_first_user(user: User):
        if User.query.count() != 1:
            return

        Account.query.filter_by(user_id=None).update({"user_id": user.id})
        if can_record_account_events():
            AccountHistoryEvent.query.filter_by(user_id=None).update({"user_id": user.id})

    @app.route("/signup", methods=["GET", "POST"])
    def signup_page():
        if g.user is not None:
            return redirect(url_for("home"))

        error = ""
        if request.method == "POST":
            username = normalize_username(request.form.get("username", ""))
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not username:
                error = "Username is required."
            elif len(username) < 3:
                error = "Username must be at least 3 characters."
            elif len(username) > MAX_USERNAME_LENGTH:
                error = f"Username must be {MAX_USERNAME_LENGTH} characters or fewer."
            elif not username.replace("_", "").replace("-", "").isalnum():
                error = "Username can only use letters, numbers, dashes, and underscores."
            elif len(password) < 8:
                error = "Password must be at least 8 characters."
            elif password != confirm_password:
                error = "Passwords must match."
            else:
                user = User(username=username, password_hash=generate_password_hash(password))
                db.session.add(user)
                try:
                    db.session.flush()
                    user_id = user.id
                    claim_legacy_data_for_first_user(user)
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    error = "That username is already taken."
                else:
                    session.clear()
                    session.permanent = True
                    session["user_id"] = user_id
                    return redirect(url_for("home"))

        return render_template("signup.html", error=error)

    @app.route("/login", methods=["GET", "POST"])
    def login_page():
        if g.user is not None:
            return redirect(url_for("home"))

        error = ""
        if request.method == "POST":
            username = normalize_username(request.form.get("username", ""))
            password = request.form.get("password", "")

            if login_is_rate_limited(username):
                error = "Too many login attempts. Please wait and try again."
            else:
                user = User.query.filter_by(username=username).first()

            if not error and (user is None or not check_password_hash(user.password_hash, password)):
                record_failed_login(username)
                error = "Username or password is incorrect."
            elif not error:
                clear_failed_logins(username)
                session.clear()
                session.permanent = True
                session["user_id"] = user.id
                return redirect(_safe_next_url(request.args.get("next")) or url_for("home"))

        return render_template("login.html", error=error)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login_page"))

    @app.get("/")
    @login_required
    def home():
        return render_template("dashboard.html")

    @app.get("/accounts/manage")
    @login_required
    def manage_accounts_page():
        return render_template("accounts_manage.html")

    @app.get("/accounts/<int:account_id>/transactions")
    @login_required
    def account_transactions_page(account_id: int):
        account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()
        if account is None:
            abort(404)

        return render_template(
            "account_transactions.html",
            account_id=account.id,
            account_name=account.name,
            account_balance=_money(account.current_balance or Decimal("0.00")),
        )

    @app.get("/transactions")
    @login_required
    def all_transactions_page():
        return render_template("transactions.html")

    @app.get("/health/db")
    def db_health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"database": "ok"}), 200
        except Exception:
            app.logger.exception("Database health check failed")
            return jsonify({"database": "error"}), 500

    @app.post("/api/transactions")
    @login_required
    def add_transaction():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        required_fields = ["account_id", "transaction_name", "amount", "category", "transaction_type"]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        try:
            account_id = int(payload["account_id"])
        except (TypeError, ValueError):
            return jsonify({"error": "account_id must be an integer"}), 400

        account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()
        if account is None:
            return jsonify({"error": "Account not found"}), 404

        transaction_name = str(payload["transaction_name"]).strip()
        if not transaction_name:
            return jsonify({"error": "transaction_name cannot be empty"}), 400
        length_error = _validate_max_length("transaction_name", transaction_name, MAX_TRANSACTION_NAME_LENGTH)
        if length_error:
            return jsonify({"error": length_error}), 400

        category = str(payload["category"]).strip()
        if not category:
            return jsonify({"error": "category cannot be empty"}), 400
        length_error = _validate_max_length("category", category, MAX_CATEGORY_LENGTH)
        if length_error:
            return jsonify({"error": length_error}), 400

        note = str(payload.get("note", "")).strip()
        length_error = _validate_max_length("note", note, MAX_NOTE_LENGTH)
        if length_error:
            return jsonify({"error": length_error}), 400

        try:
            amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "amount must be numeric"}), 400

        if amount <= 0:
            return jsonify({"error": "amount must be greater than zero"}), 400

        transaction_type = str(payload["transaction_type"]).strip().lower()
        if transaction_type in {"expense", "debit"}:
            balance_delta = -amount
        elif transaction_type == "recurring":
            balance_delta = -amount
        elif transaction_type in {"income", "credit", "deposit"}:
            balance_delta = amount
        else:
            return jsonify({"error": "transaction_type must be expense/debit/recurring or income/credit/deposit"}), 400

        occurred_at = _parse_occurred_at(payload.get("occurred_at"))
        if payload.get("occurred_at") and occurred_at is None:
            return jsonify({"error": "occurred_at must be valid ISO datetime"}), 400

        is_recurring_type = transaction_type == "recurring"
        recurring_due_date = _parse_due_date(payload.get("recurring_due_date"))
        if is_recurring_type and recurring_due_date is None:
            return jsonify({"error": "recurring_due_date must be valid YYYY-MM-DD when type is Recurring"}), 400

        transaction = Transaction(
            account_id=account.id,
            transaction_name=transaction_name,
            amount=amount,
            category=category,
            transaction_type=transaction_type,
            note=note or None,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )

        next_balance = (account.current_balance or Decimal("0.00")) + balance_delta
        if next_balance < Decimal("0.00"):
            return jsonify({"error": "Insufficient funds: transaction would make this account balance negative."}), 400

        account.current_balance = next_balance

        if is_recurring_type and recurring_due_date is not None:
            due_day = recurring_due_date.day
            existing_bill = (
                RecurringBill.query.filter_by(
                    account_id=account.id,
                    name=transaction_name,
                    due_day=due_day,
                    active=True,
                )
                .order_by(RecurringBill.id.desc())
                .first()
            )
            if existing_bill is None:
                db.session.add(
                    RecurringBill(
                        account_id=account.id,
                        name=transaction_name,
                        amount=amount,
                        category="Recurring",
                        due_day=due_day,
                        frequency="monthly",
                        active=True,
                    )
                )

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
    @login_required
    def list_recent_transactions():
        limit = request.args.get("limit", default=20, type=int)
        if limit is None or limit < 1:
            limit = 20
        limit = min(limit, 100)

        items = (
            Transaction.query.join(Account)
            .filter(Account.user_id == g.user.id)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .limit(limit)
            .all()
        )

        return jsonify(
            {
                "transactions": [
                    {
                        "id": tx.id,
                        "account_id": tx.account_id,
                        "account_name": tx.account.name if tx.account is not None else "Unknown",
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

    @app.get("/api/transactions")
    @login_required
    def list_all_transactions():
        items = (
            Transaction.query.join(Account)
            .filter(Account.user_id == g.user.id)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .all()
        )

        return jsonify(
            {
                "transactions": [
                    {
                        "id": tx.id,
                        "account_id": tx.account_id,
                        "account_name": tx.account.name if tx.account is not None else "Unknown",
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

    @app.get("/api/accounts/<int:account_id>/transactions")
    @login_required
    def list_account_transactions(account_id: int):
        account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()
        if account is None:
            return jsonify({"error": "Account not found"}), 404

        items = (
            Transaction.query.filter_by(account_id=account_id)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .all()
        )

        return jsonify(
            {
                "account": {
                    "id": account.id,
                    "name": account.name,
                    "current_balance": _money(account.current_balance or Decimal("0.00")),
                },
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
                ],
            }
        )

    @app.get("/api/accounts/summary")
    @login_required
    def account_summaries():
        accounts = Account.query.filter_by(user_id=g.user.id).order_by(Account.name.asc()).all()
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

    @app.get("/api/accounts/history")
    @login_required
    def account_history():
        limit = request.args.get("limit", default=50, type=int)
        if limit is None or limit < 1:
            limit = 50
        limit = min(limit, 200)

        try:
            entries = (
                AccountHistoryEvent.query.filter_by(user_id=g.user.id)
                .order_by(AccountHistoryEvent.created_at.desc(), AccountHistoryEvent.id.desc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError:
            # Keep account management usable if migrations have not yet been applied.
            return jsonify({"events": []})

        return jsonify(
            {
                "events": [
                    {
                        "id": event.id,
                        "action": event.action,
                        "account_name": event.account_name,
                        "account_balance": _money(event.account_balance),
                        "note": event.note,
                        "created_at": _serialize_datetime(event.created_at),
                    }
                    for event in entries
                ]
            }
        )

    @app.post("/api/accounts")
    @login_required
    def create_account():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        name = str(payload.get("name", "")).strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        length_error = _validate_max_length("name", name, MAX_ACCOUNT_NAME_LENGTH)
        if length_error:
            return jsonify({"error": length_error}), 400

        try:
            starting_balance = Decimal(str(payload.get("starting_balance", "0")))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "starting_balance must be numeric"}), 400

        note = str(payload.get("note", "")).strip() or None
        if note:
            length_error = _validate_max_length("note", note, MAX_NOTE_LENGTH)
            if length_error:
                return jsonify({"error": length_error}), 400

        account = Account(
            user_id=g.user.id,
            name=name,
            account_type="custom",
            starting_balance=starting_balance,
            current_balance=starting_balance,
        )

        db.session.add(account)
        record_account_event("created", account.name, account.current_balance, note)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Account name already exists"}), 409

        return (
            jsonify(
                {
                    "account": {
                        "id": account.id,
                        "name": account.name,
                        "account_type": account.account_type,
                        "starting_balance": _money(account.starting_balance),
                        "current_balance": _money(account.current_balance),
                    }
                }
            ),
            201,
        )

    @app.delete("/api/accounts/<int:account_id>")
    @login_required
    def delete_account(account_id: int):
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        confirm = payload.get("confirm")
        if confirm is not True:
            return jsonify({"error": "confirm must be true to delete an account"}), 400

        account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()
        if account is None:
            return jsonify({"error": "Account not found"}), 404

        reason = str(payload.get("reason", "")).strip() or None
        if reason:
            length_error = _validate_max_length("reason", reason, MAX_NOTE_LENGTH)
            if length_error:
                return jsonify({"error": length_error}), 400
        account_name = account.name
        account_balance = account.current_balance or Decimal("0.00")

        record_account_event("deleted", account_name, account_balance, reason)
        db.session.delete(account)
        db.session.commit()

        return jsonify({"deleted": {"id": account_id, "name": account_name}}), 200

    @app.get("/api/bills/upcoming")
    @login_required
    def upcoming_bills():
        days = request.args.get("days", default=30, type=int)
        if days is None or days < 1:
            days = 30
        days = min(days, 365)

        today = date.today()
        window_end = today + timedelta(days=days)

        bills = (
            RecurringBill.query.join(Account)
            .filter(RecurringBill.active.is_(True), Account.user_id == g.user.id)
            .order_by(RecurringBill.due_day.asc())
            .all()
        )

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

    @app.get("/api/bills/recurring")
    @login_required
    def list_recurring_bills():
        bills = (
            RecurringBill.query.join(Account)
            .filter(RecurringBill.active.is_(True), Account.user_id == g.user.id)
            .order_by(RecurringBill.name.asc(), RecurringBill.id.asc())
            .all()
        )

        return jsonify(
            {
                "bills": [
                    {
                        "id": bill.id,
                        "account_id": bill.account_id,
                        "name": bill.name,
                        "amount": _money(bill.amount),
                        "due_day": bill.due_day,
                        "frequency": bill.frequency,
                    }
                    for bill in bills
                ]
            }
        )

    @app.delete("/api/bills/<int:bill_id>")
    @login_required
    def delete_recurring_bill(bill_id: int):
        bill = (
            RecurringBill.query.join(Account)
            .filter(RecurringBill.id == bill_id, RecurringBill.active.is_(True), Account.user_id == g.user.id)
            .first()
        )
        if bill is None or not bill.active:
            return jsonify({"error": "Recurring bill not found"}), 404

        bill.active = False
        db.session.commit()

        return jsonify({"deleted": {"id": bill.id, "name": bill.name}}), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
