# Security Documentation

As the app grew to become beyond just a localhost tool, it became apparent that security would be an important layer. As I am also taking cybersecurity for my college major, it would make sense to treat this like a proper security system, as it handles real user data.

## Security Scope

Dealing with information like:

- Account Balanaces & History
- Transactions
- User passwords

**This does not directly connect to a bank. User's simply manually input and set up bank info.**

User's should be registered via User and Password. 

Main risks include:

- User's shouldn't be able to see or modify other user's data
- Bad password storage / hashing
- Session Hijacking
- Bad injection

## Security Implementation

When creating the log in / sign up system, that required users to have their own data and login. 

**Authentication** is key, we need to verify a user is who they say they are. A sign up page / log in page is used for account creation and verification, as long as a logout ability.

**A hash generator is used via Werkzeug** to hash passwords. It is important to NEVER store raw passwords.

*Code Implementation:*

- Import: [`from werkzeug.security import check_password_hash, generate_password_hash`](../app.py#L14). This allows us to use the hash ability.
- Password hashing on signup: [`user = User(username=username, password_hash=generate_password_hash(password))`](../app.py#L177). Essential for validation & security.
- Password verification on login: [`if user is None or not check_password_hash(user.password_hash, password):`](../app.py#L198)
- Password stored in database: [`password_hash = db.Column(db.String(255), nullable=False)`](../models.py#L128). It is stored as a hashed password. No real passwords are stored.

**Hashing** is better than encrypting in this case because encrypting is reversible. Hashing stores passwords with a "hashed fingerprint". When the security checks if passwords match when logging in, it is not checking the actual password itself. It checks the hashed fingerprint.

We implement **session cookies** for browsers. On future requests, Flask reads the cookie and knows which user is logged in based on this session cookie. 

*Code Implementation:*

- Session setup on signup: [`session.clear()` and `session["user_id"] = user_id`](../app.py#L180-L181)
- Session setup on login: [`session.clear()` and `session["user_id"] = user.id`](../app.py#L200-L201)
- Session cleared on logout: [`session.clear()`](../app.py#L206). Sessions should NOT stick if logging out. Why would a user wanna be on the account when they access the page again when they had logged out prior?
- Current user loaded from session: [`user_id = session.get("user_id")`](../app.py#L137)
- User attached to request context: [`g.user = load_current_user()`](../app.py#L149).

**Login Required Protection** is the way we make protected pages. Certain pages and transactions should only be accessible by the user. If an unauthorized user tries to accessing information for another user, they get hit with a 4xx HTTP error.

*Code Implementation:*

- Login required decorator: [`def login_required(view):`](../app.py#L153-L162) checks if `g.user is not None`. 
- Applied to necessary routes: [`@login_required` decorator on routes like `def home():`](../app.py#L226-L227), [`def add_transaction():`](../app.py#L275), [`def list_recent_transactions():`](../app.py#L416)

**Authorization** asks what an authenticated user is allowed to access and use. In this case, accounts and transactions. 

*Code Implementation:*

- All account queries filter by user: [`Account.query.filter_by(user_id=g.user.id)`](../app.py#L509). This is essential. This is the thing that differeniates what users can see. Same for everything below.
- Transactions filtered through user's accounts: [`Transaction.query.join(Account).filter(Account.user_id == g.user.id)`](../app.py#L422)
- Account history filtered by user: [`AccountHistoryEvent.query.filter_by(user_id=g.user.id)`](../app.py#L532)
- Recurring bills filtered by user: [`RecurringBill.query.join(Account).filter(..., Account.user_id == g.user.id)`](../app.py#L669)

As this was really just a one person localhost app before, data would simply be stored to one database set. In the case of multiple people, this would make no sense.

**Access control** is server side. There are no (easily accessible) ways for a standard user to escalate their privileges or abilities on the user side.

**IDOR (Insecure Direct Object Reference)** is a vital cybersecurity concept. Similar to the authorization related ideas above, this is a vulnerability that happens when an unauthorized user is allowed to change certain parameters (like the URL) to access certain material. If anyone could simply access another user's information by just changing the URL to have the other user's username, that is a huge security risk.

*Code Implementation:*

- Account endpoint / end security checks user ownership: [`account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()` then `if account is None: abort(404)`](../app.py#L217-L219). Before allowing user to see certain material, it checks the user's authorization. No authorization, no access.
- Transaction endpoint checks user ownership: [`account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()` then `if account is None: return jsonify(...), 404`](../app.py#L407-L409)
- Delete endpoint validates ownership: [`account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()` then `if account is None: return jsonify(...), 404`](../app.py#L656-L658)

Even though URLs contain IDs, changing them to access other users' data returns 404 instead of the data.

**Redirect's are closed.** Redirects are pre-coded and are determined by user behavior, not their input. Allowing redirects / link changes based on input could cause malicious injection.

*Code Implementation:*

- Validation function: [`def _safe_next_url(value: str | None) -> str | None:` checks if URL starts with `/` but not `//`](../app.py#L76-L79)
- Applied to login redirect: [`return redirect(_safe_next_url(request.args.get("next")) or url_for("home"))`](../app.py#L202)

This prevents open redirects where an attacker could redirect users to malicious sites.

