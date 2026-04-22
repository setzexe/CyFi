from datetime import date
from decimal import Decimal

from app import create_app, db
from models import Account, AccountHistoryEvent, RecurringBill, Transaction


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
    assert b"Recent Transactions" in response.data
    assert b"See All Transactions" in response.data


def test_all_transactions_page_loads():
    client, _ = _build_client_and_app()
    response = client.get("/transactions")
    assert response.status_code == 200
    assert b"All Transactions" in response.data


def test_manage_accounts_page_loads():
    client, _ = _build_client_and_app()
    response = client.get("/accounts/manage")
    assert response.status_code == 200
    assert b"Manage Accounts" in response.data


def test_account_transactions_page_loads():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.get(f"/accounts/{account_id}/transactions")
    assert response.status_code == 200
    assert b"Transactions" in response.data


def test_account_transactions_api_filters_to_account_only():
    client, app = _build_client_and_app()

    with app.app_context():
        checking = Account.query.filter_by(name="Checking").first()
        savings = Account(
            name="Savings",
            account_type="savings",
            starting_balance=Decimal("250.00"),
            current_balance=Decimal("250.00"),
        )
        db.session.add(savings)
        db.session.commit()

        db.session.add(
            Transaction(
                account_id=checking.id,
                transaction_name="Coffee",
                amount=Decimal("4.00"),
                category="Food",
                transaction_type="expense",
            )
        )
        db.session.add(
            Transaction(
                account_id=savings.id,
                transaction_name="Interest",
                amount=Decimal("5.00"),
                category="Income",
                transaction_type="deposit",
            )
        )
        db.session.commit()

        checking_id = checking.id

    response = client.get(f"/api/accounts/{checking_id}/transactions")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["account"]["name"] == "Checking"
    assert len(payload["transactions"]) == 1
    assert payload["transactions"][0]["transaction_name"] == "Coffee"


def test_account_transactions_api_empty_list_for_new_account():
    client, app = _build_client_and_app()

    with app.app_context():
        savings = Account(
            name="Savings",
            account_type="savings",
            starting_balance=Decimal("250.00"),
            current_balance=Decimal("250.00"),
        )
        db.session.add(savings)
        db.session.commit()
        savings_id = savings.id

    response = client.get(f"/api/accounts/{savings_id}/transactions")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["account"]["name"] == "Savings"
    assert payload["transactions"] == []


def test_recent_transactions_api_includes_account_name_and_newest_first():
    client, app = _build_client_and_app()

    with app.app_context():
        checking = Account.query.filter_by(name="Checking").first()

        db.session.add(
            Transaction(
                account_id=checking.id,
                transaction_name="Older",
                amount=Decimal("2.00"),
                category="Food",
                transaction_type="expense",
                occurred_at=db.func.datetime("2026-01-01 10:00:00"),
            )
        )
        db.session.add(
            Transaction(
                account_id=checking.id,
                transaction_name="Newer",
                amount=Decimal("3.00"),
                category="Food",
                transaction_type="expense",
                occurred_at=db.func.datetime("2026-01-01 11:00:00"),
            )
        )
        db.session.commit()

    response = client.get("/api/transactions/recent?limit=5")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["transactions"]) == 2
    assert payload["transactions"][0]["transaction_name"] == "Newer"
    assert payload["transactions"][0]["account_name"] == "Checking"


def test_all_transactions_api_includes_account_name_and_newest_first():
    client, app = _build_client_and_app()

    with app.app_context():
        checking = Account.query.filter_by(name="Checking").first()
        savings = Account(
            name="Savings",
            account_type="savings",
            starting_balance=Decimal("250.00"),
            current_balance=Decimal("250.00"),
        )
        db.session.add(savings)
        db.session.commit()

        db.session.add(
            Transaction(
                account_id=checking.id,
                transaction_name="First",
                amount=Decimal("2.00"),
                category="Food",
                transaction_type="expense",
                occurred_at=db.func.datetime("2026-01-01 10:00:00"),
            )
        )
        db.session.add(
            Transaction(
                account_id=savings.id,
                transaction_name="Second",
                amount=Decimal("6.00"),
                category="Income",
                transaction_type="deposit",
                occurred_at=db.func.datetime("2026-01-01 11:00:00"),
            )
        )
        db.session.commit()

    response = client.get("/api/transactions")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["transactions"]) == 2
    assert payload["transactions"][0]["transaction_name"] == "Second"
    assert payload["transactions"][0]["account_name"] == "Savings"


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


def test_transaction_cannot_make_balance_negative():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_name": "Large Purchase",
            "amount": "150.00",
            "category": "Shopping",
            "transaction_type": "expense",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Insufficient funds: transaction would make this account balance negative."

    with app.app_context():
        unchanged = db.session.get(Account, account_id)
        assert str(unchanged.current_balance) == "100.00"


def test_recurring_transaction_creates_recurring_bill():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_name": "HOA",
            "amount": "30.00",
            "category": "Bills",
            "transaction_type": "recurring",
            "recurring_due_date": "2026-04-22",
        },
    )
    assert response.status_code == 201

    with app.app_context():
        recurring = RecurringBill.query.filter_by(account_id=account_id, name="HOA", active=True).first()
        assert recurring is not None
        assert recurring.due_day == 22
        assert str(recurring.amount) == "30.00"


def test_recurring_transaction_requires_due_date():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        account_id = account.id

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_name": "HOA",
            "amount": "300.00",
            "category": "Bills",
            "transaction_type": "recurring",
        },
    )
    assert response.status_code == 400


def test_upcoming_bills_are_sorted_by_next_due_date():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        today = date.today()
        first_due_day = today.day
        second_due_day = min(today.day + 1, 28)

        db.session.add(
            RecurringBill(
                account_id=account.id,
                name="Phone",
                amount=Decimal("55.00"),
                category="Recurring",
                due_day=second_due_day,
                frequency="monthly",
                active=True,
            )
        )
        db.session.add(
            RecurringBill(
                account_id=account.id,
                name="Rent",
                amount=Decimal("900.00"),
                category="Recurring",
                due_day=first_due_day,
                frequency="monthly",
                active=True,
            )
        )
        db.session.commit()

    response = client.get("/api/bills/upcoming?days=45")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["bills"]) >= 2
    assert payload["bills"][0]["name"] == "Rent"


def test_recurring_bill_can_be_removed_and_hidden_from_active_list():
    client, app = _build_client_and_app()

    with app.app_context():
        account = Account.query.filter_by(name="Checking").first()
        bill = RecurringBill(
            account_id=account.id,
            name="Spotify",
            amount=Decimal("9.99"),
            category="Recurring",
            due_day=15,
            frequency="monthly",
            active=True,
        )
        db.session.add(bill)
        db.session.commit()
        bill_id = bill.id

    list_before = client.get("/api/bills/recurring")
    assert list_before.status_code == 200
    assert any(item["id"] == bill_id for item in list_before.get_json()["bills"])

    deleted = client.delete(f"/api/bills/{bill_id}")
    assert deleted.status_code == 200

    list_after = client.get("/api/bills/recurring")
    assert list_after.status_code == 200
    assert all(item["id"] != bill_id for item in list_after.get_json()["bills"])


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
