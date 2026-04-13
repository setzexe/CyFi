from decimal import Decimal

from app import create_app, db
from models import Account


def _build_client_and_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        account = Account(
            name="Checking",
            account_type="checking",
            starting_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )
        db.session.add(account)
        db.session.commit()

    return app.test_client(), app


def test_dashboard_page_loads():
    client, _ = _build_client_and_app()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_expense_decreases_balance():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_name": "Coffee",
            "amount": "4.50",
            "category": "Food",
            "transaction_type": "expense",
        },
    )
    assert response.status_code == 201

    with app.app_context():
        updated = db.session.get(Account, account_id)
        assert str(updated.current_balance) == "95.50"


def test_deposit_increases_balance():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_name": "Paycheck",
            "amount": "500.00",
            "category": "Income",
            "transaction_type": "deposit",
        },
    )
    assert response.status_code == 201

    with app.app_context():
        updated = db.session.get(Account, account_id)
        assert str(updated.current_balance) == "600.00"


def test_bad_input_returns_error():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_name": "",
            "amount": "-1",
            "category": "Food",
            "transaction_type": "expense",
        },
    )
    assert response.status_code == 400