from decimal import Decimal

from app import create_app, db
from models import Account, AccountHistoryEvent


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
    assert b"Add / Remove Account" in response.data


def test_manage_accounts_page_loads():
    client, _ = _build_client_and_app()
    response = client.get("/accounts/manage")
    assert response.status_code == 200
    assert b"Manage Accounts" in response.data


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


def test_create_account_adds_history_event():
    client, app = _build_client_and_app()

    response = client.post(
        "/api/accounts",
        json={
            "name": "Travel",
            "starting_balance": "250.00",
            "note": "Created for trips",
        },
    )
    assert response.status_code == 201

    with app.app_context():
        account = Account.query.filter_by(name="Travel").first()
        assert account is not None
        assert str(account.current_balance) == "250.00"

        event = AccountHistoryEvent.query.order_by(AccountHistoryEvent.id.desc()).first()
        assert event is not None
        assert event.action == "created"
        assert event.account_name == "Travel"
        assert str(event.account_balance) == "250.00"
        assert event.note == "Created for trips"


def test_delete_account_requires_confirmation():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.delete(
        f"/api/accounts/{account_id}",
        json={"confirm": False},
    )
    assert response.status_code == 400

    with app.app_context():
        still_there = db.session.get(Account, account_id)
        assert still_there is not None


def test_delete_account_removes_account_and_logs_history():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.delete(
        f"/api/accounts/{account_id}",
        json={"confirm": True, "reason": "Consolidated"},
    )
    assert response.status_code == 200

    with app.app_context():
        deleted = db.session.get(Account, account_id)
        assert deleted is None

        event = AccountHistoryEvent.query.order_by(AccountHistoryEvent.id.desc()).first()
        assert event is not None
        assert event.action == "deleted"
        assert event.account_name == "Checking"
        assert event.note == "Consolidated"


def test_create_account_works_without_history_table():
    client, app = _build_client_and_app()

    with app.app_context():
        db.session.execute(db.text("DROP TABLE account_history_events"))
        db.session.commit()

    response = client.post(
        "/api/accounts",
        json={
            "name": "Vacation",
            "starting_balance": "50.00",
        },
    )
    assert response.status_code == 201

    with app.app_context():
        account = Account.query.filter_by(name="Vacation").first()
        assert account is not None
        assert str(account.current_balance) == "50.00"


def test_delete_account_works_without_history_table():
    client, app = _build_client_and_app()

    with app.app_context():
        db.session.execute(db.text("DROP TABLE account_history_events"))
        db.session.commit()
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.delete(
        f"/api/accounts/{account_id}",
        json={"confirm": True},
    )
    assert response.status_code == 200

    with app.app_context():
        deleted = db.session.get(Account, account_id)
        assert deleted is None
