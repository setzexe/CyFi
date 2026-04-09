"""
CyFi Supabase setup playbook.

Instruction-only file: use this as your runbook while implementing.
"""


OVERVIEW = """
Preferred flow for your project:

1) Supabase hosts PostgreSQL.
2) Flask API connects with SQLAlchemy + psycopg.
3) Browser/phone talks only to Flask API over HTTPS.

Important:
- You do NOT need Supabase anon/service keys for this backend-only approach.
- You mainly need PostgreSQL connection strings.
"""


STEP_1_SUPABASE_PROJECT = """
Step 1: Create Supabase project

1) Create a new Supabase project.
2) Wait until database status is healthy.
3) Open Project Settings -> Database -> Connection string.
4) Copy TWO URLs:
   - Transaction pooler URL (runtime)
   - Direct connection URL (migrations)

Store them as:
- DATABASE_URL=<pooler URL>
- DATABASE_URL_DIRECT=<direct URL>

Why two URLs:
- Pooler is best for app runtime.
- Direct is more reliable for migration operations.
"""


STEP_2_DEPENDENCIES = """
Step 2: Dependencies (already mostly present in your repo)

Required packages:
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- SQLAlchemy
- psycopg[binary]
- python-dotenv
- gunicorn

Install/update:
./.venv/bin/python -m pip install -r requirements.txt
"""


STEP_3_ENV = """
Step 3: Local environment

Create .env in project root:

SECRET_KEY=replace-with-long-random-string
DATABASE_URL=postgresql://...pooler...
DATABASE_URL_DIRECT=postgresql://...direct...

Notes:
- Keep sslmode=require in the URL.
- Do not commit .env.
"""


APP_PY_MINIMAL = """
Suggested app.py structure:

import os
from flask import Flask, jsonify
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
        url = url.replace("postgres://", "postgresql://", 1)
    return url


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

    from models import Account, Transaction  # noqa: F401

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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
"""


MODELS_PY_STARTER = """
Suggested models.py starter schema:

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


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
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
"""


STEP_4_MIGRATIONS = """
Step 4: Run migrations

Initialize migration folder once:
./.venv/bin/flask --app app:create_app db init

Create migration file:
./.venv/bin/flask --app app:create_app db migrate -m "init schema"

Apply migrations using DIRECT URL for better reliability:
DATABASE_URL="$DATABASE_URL_DIRECT" ./.venv/bin/flask --app app:create_app db upgrade

Alternative if DATABASE_URL_DIRECT is only in .env:
1) export DATABASE_URL_DIRECT=...
2) export DATABASE_URL="$DATABASE_URL_DIRECT"
3) ./.venv/bin/flask --app app:create_app db upgrade
"""


STEP_5_MINIMUM_VERIFY = """
Step 5: Least possible verification

Option A: direct Python smoke test
./.venv/bin/python -c "import os,psycopg;from dotenv import load_dotenv;load_dotenv('.env');u=os.getenv('DATABASE_URL');assert u,'DATABASE_URL missing';psycopg.connect(u).execute('select 1');print('DB_OK')"

Option B: app endpoint verification
1) Start app: ./.venv/bin/flask --app app:create_app run --debug
2) Call /health/db
3) Expect response: {\"database\": \"ok\"}

If it fails on school wifi with timeout/refused, test again on home/hotspot or from deployed API.
"""


STEP_6_DEPLOY = """
Step 6: Deploy backend

Render/Railway/Fly all work.

Environment variables in deployment:
- SECRET_KEY
- DATABASE_URL (pooler URL)
- DATABASE_URL_DIRECT (direct URL, optional but recommended)

After deploy:
1) Open service shell.
2) Run migration upgrade once.
3) Verify deployed /health/db is ok.

This is the network-resilient path because client devices only need HTTPS access.
"""


CARD_CHECKLIST = """
Acceptance criteria mapping

1) Create basic schema for database
- Add models.py with accounts and transactions
- Generate and run migration files

2) Figure out and connect a database system
- Supabase project configured
- DATABASE_URL wired into Flask SQLAlchemy

3) Ensure connection/workability
- SELECT 1 smoke test passes
- /health/db returns ok
- Migration upgrade completes
"""
