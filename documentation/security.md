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
- Improper password storage / hashing
- Session Hijacking
- Malicious injection
- Requests from outside sources
- Cookie / session failure

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

**Login rate limiting** slows down password guessing. If someone repeatedly enters the wrong password for the same username from the same IP address, the app temporarily blocks more login attempts. This prevents **brute force attacks.**

*Code Implementation:*

- Rate limit settings: [`LOGIN_RATE_LIMIT_ATTEMPTS=5` and `LOGIN_RATE_LIMIT_WINDOW=timedelta(minutes=15)`](../app.py#L118).
- Login attempts are tracked with [`login_attempts: dict[str, list[datetime]] = {}`](../app.py#L134).
- The rate limit key combines IP address and username through [`def login_rate_limit_key(username: str) -> str:`](../app.py#L139).
- Old failures are cleaned out by [`def recent_login_failures(username: str) -> list[datetime]:`](../app.py#L143).
- Failed logins are recorded with [`record_failed_login(username)`](../app.py#L321).
- Successful logins clear previous failed attempts with [`clear_failed_logins(username)`](../app.py#L324).
- Blocked users get the error: [`Too many login attempts. Please wait and try again.`](../app.py#L316)

___

We implement **session cookies** for browsers. On future requests, Flask reads the cookie and knows which user is logged in based on this session cookie. 

*Code Implementation:*

- Session setup on signup: [`session.clear()` and `session["user_id"] = user_id`](../app.py#L180-L181)
- Session setup on login: [`session.clear()` and `session["user_id"] = user.id`](../app.py#L200-L201)
- Session cleared on logout: [`session.clear()`](../app.py#L206). Sessions should NOT stick if logging out. Why would a user wanna be on the account when they access the page again when they had logged out prior?
- Current user loaded from session: [`user_id = session.get("user_id")`](../app.py#L137)
- User attached to request context: [`g.user = load_current_user()`](../app.py#L149).

**Session cookie hardening** is used so that browser session cookies are harder to steal or abuse. A stolen cookie = potential malicious redirections.

*Code Implementation:*

- Cookie hardening settings: [`SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_SECURE=_is_production()`, and `PERMANENT_SESSION_LIFETIME=timedelta(hours=8)`](../app.py#L114).
- Session lifetime activation after login/signup: [`session.permanent = True`](../app.py#L299) and [`session.permanent = True`](../app.py#L326).

___

**Secret key protection** protects Flask sessions. Flask signs session cookies with `SECRET_KEY`, which means the browser can store session data but cannot safely change it without the key. If everyone uses the same default key, an attacker could potentially tamper with proper session cookies.

*Code Implementation:*

- Default development key: [`DEFAULT_SECRET_KEY = "dev-key-change-me"`](../app.py#L23).
- Flask reads the real key from the environment with [`SECRET_KEY=os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)`](../app.py#L111).
- Production mode is checked with [`def _is_production() -> bool:`](../app.py#L104).
- Production startup fails if the real key was not configured: [`raise RuntimeError("SECRET_KEY must be set to a strong random value in production.")`](../app.py#L126).

___

**CSRF Protection** protects the user's session from sending malicious requests from a seperate site. Since Flask sessions use browser cookies, a malicious site could try to make a logged-in user's browser send a request to CyFi. CSRF tokens stop that because the attacker does not know the secret token stored in the user's session.

CSRF stands for **Cross-site Request Forgery.** CSRF Tokens in particular are unique (unpredictable) and secretive value's generated by the server-side, given to the client. Attackers can't make malicious requests without this token.

*Code Implementation:*

- CSRF token generation and storage: [`def csrf_token() -> str:` and `session["csrf_token"] = token`](../app.py#L132).
- CSRF validation in the request pipeline: [`@app.before_request` / `def protect_from_csrf():`](../app.py#L142) and the token comparison with `compare_digest`](../app.py#L154).
- Forms that include the hidden token field: [`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />`](../templates/signup.html#L18) and the same pattern in [`login.html`](../templates/login.html#L18).
- Pages that expose the token to JavaScript through a meta tag: [`<meta name="csrf-token" content="{{ csrf_token() }}" />`](../templates/dashboard.html#L6).
- JavaScript requests that send the token in the `X-CSRF-Token` header: [`return token ? { "X-CSRF-Token": token } : {};`](../static/dashboard.js#L69) and the same helper in [`account_manage.js`](../static/account_manage.js#L70).
- Missing or invalid API tokens return [`{"error": "CSRF token missing or invalid"}`](../app.py#L159) with a `400` status.

___

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

___

**IDOR (Insecure Direct Object Reference)** is a vital cybersecurity concept. Similar to the authorization related ideas above, this is a vulnerability that happens when an unauthorized user is allowed to change certain parameters (like the URL) to access certain material. If anyone could simply access another user's information by just changing the URL to have the other user's username, that is a huge security risk.

*Code Implementation:*

- Account endpoint / end security checks user ownership: [`account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()` then `if account is None: abort(404)`](../app.py#L217-L219). Before allowing user to see certain material, it checks the user's authorization. No authorization, no access.
- Transaction endpoint checks user ownership: [`account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()` then `if account is None: return jsonify(...), 404`](../app.py#L407-L409)
- Delete endpoint validates ownership: [`account = Account.query.filter_by(id=account_id, user_id=g.user.id).first()` then `if account is None: return jsonify(...), 404`](../app.py#L656-L658)

Even though URLs contain IDs, changing them to access other users' data returns 404 instead of the data.

___

**Redirect's are closed.** Redirects are pre-coded and are determined by user behavior, not their input. Allowing redirects / link changes based on input could cause malicious injection.

*Code Implementation:*

- Validation function: [`def _safe_next_url(value: str | None) -> str | None:` checks if URL starts with `/` but not `//`](../app.py#L76-L79)
- Applied to login redirect: [`return redirect(_safe_next_url(request.args.get("next")) or url_for("home"))`](../app.py#L202)

This prevents open redirects where an attacker could redirect users to malicious sites.

___

**Security headers** are extra browser instructions that reduce common web attacks. They do not replace authentication, authorization, or CSRF protection, but they add another layer of protection.

*Code Implementation:*

- Security headers are added to every response through [`@app.after_request` and `def add_security_headers(response):`](../app.py#L201).
- [`X-Content-Type-Options: nosniff`](../app.py#L203) tells the browser not to guess content types.
- [`X-Frame-Options: DENY`](../app.py#L204) helps prevent clickjacking by blocking the app from being placed in an iframe.
- [`Referrer-Policy: same-origin`](../app.py#L205) limits how much URL information is sent as referrer data.
- [`Content-Security-Policy`](../app.py#L206) limits what scripts, styles, images, forms, and frames the browser should allow.
- The current CSP allows `'unsafe-inline'` for scripts and styles because some templates currently use inline CSS and small inline scripts. This could be tightened later by moving all inline code into static files.
