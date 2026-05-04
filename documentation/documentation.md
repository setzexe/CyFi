# CyFi (Cyberseverance Finance Tracker) 

**CyFi** is a flask-based manual finance tracker application with multi-user authentication + account ownership, along with proper transaction / bill / account tracking. Data does not cross between accounts, passwords are hashed, and there are security elements in play to prevent attacks like injections / hijacking.

For security’s sake, this does not connect to banks. 

The project **demonstrates** full-stack development, database modeling, secure authentication + authorization, CSRF protection, and deployment.

## Tech Stack

- Backend 
    - Python
    - Flask [+ SQLAlchemy & Migrate]
    - Werkzueg for hashing
    - Gunicorn for deployment help

- Database 
    - PostgresSQL via Supabase
    - SQLite for local
    - SQLAlchemy

- Frontend 
    - HTML via Jinja
    - CSS
    - JS

- Deployment
    - Render
    - Supabase for Database
    - Env variables

- Version Control 
    - Git / Github
        - Backlog for planning
        - Branches + pull requests for features


## Main App Flow

- User flow
    - User signs up with username + password
    - This password is hashed. Not stored raw
    - App creates a session cookie
    - User creates accounts to store balances
    - User adds transactions to these accounts, including recurring bills
        - User can view all these
    - Transactions update account balances.
    - User logs out, session cleared

- Backend flow
    - Browser requests page
    - Flask route checks session. login_required protects pages that should be private
    - API endpoints check is user is authenticated
    - Information is queried through user_id

## Database Information

- User
    - Login identity + password hash
- Account
    - Belongs to individual users
- Transactions
    - Belongs to an account.
- RecurringBill
    - Also belongs to an account.
- AccountHistoryEvent
    - Records account history

Foreign keys connect data together. user_id maintains overship. Migrations are what track schema changes over time.

## Security Concepts 

- Authentication 
    - Verifies indentity via username and password
    - Passwords are hashed via Werkzeug. Raw passwords are never stored.
- Authorization
    - Determines what a (logged in) user can access.
    - Data related to a user is filtered to that user specifically. Changing URL's does not bypass this.
    - IDOR (Insecure Direct Object Reference)
        - This is the concept of using an insecure method (url change for example) to access direct data of another user.
- Sessions
    - Flask session cookies store session data from signed users. SECRET_KEY signs these cookies.
    - Logouts clears sessions.
- Cookie Hardening
    - HttpOnly = JavaScript can't read session cookies.
    - Secure = Ensures HTTPS, not HTTP
    - Session lifetime
- CSRF (Cross-Site Request Forgery) 
    - This is an attack where another site tricks a logged in user into making a request to CyFi.
    - CSRF tokens are stored in sessions. If a request is missing this, its blocked.
- Rate limiting
    - Cannot log in for 15 minutes if 5 password attempts fail
    - This is to prevent brute forcing
- Input Validation
    - Required fields checked server side
    - Strings + Numbers are parsed and filtered accordingly.
    - Input length limits
- Error Handling
    - Raw DB errors are hidden and stay server side. This is to prevent schema info or code structure from leaking.

## Testing

Automated testing via /tests/ cover:

- Signup + hashed passwords
- Login creating sessions
- Logged out user's can not access pages with data that is not theirs
- Transactions update correctly
- CSRF rejects a lack of CSRF token
- Security headers exist
- Length validation works
- Negative balance transactions do not work
- Rate limiting works

Manual testing includes:

- Creating user, account, and transactions
- Trying to access another user's page via URL changes
- Oversized inputs do not work
- Brute forcing fails

## Deployment

This was initially created for my own use, but decided it would make more sense for web deployment.

Localhost is what is used to make it run purely on your machine. It runs off a ephemeral port and only can be seen by you. 

Public deployment required both a hosted app server and database. Render hosts the Flask app. Supabase hosts the database (PostgreSQL). 

Environmental variables store secrets and the database url for the site to access. 

## Development Workflow

Git & Github are the main blocks of development. These allow for development flows like commiting.

To make the project easier overall, I used GitHub project backlogs to break down work, breaking them down into individual tasks. This also allowed us to work feature by feature, finishing the project in increments.

Tests were made after feature implementations to verify that the code itself would even work.

Although I understand the languages and security aspects, I am not a web developer and have no actual web development language programming knowledge. For this, AI heavily assisted in formatting and understanding of the code. However, the code and project as a whole was directed by me, making sure the program, code, testing, and documentation was up to sufficient standards.

___

# Personal Questions

These are just simply brainstormed thoughts. This only really applies to the deployment of version 1.0.

## What did I learn from this? 

This project overall helped me understand the general scope of web security and software engineering as a whole. 

With web security (and this applies to other parts of cyber as well) the main security features like authorization, authentication, injection, etc become clear and actually testing this stuff, you realize how simple yet important this stuff can be. Hashing passwords, reducing IDOR risk, etc. The grand world and big parts of cyber is probably more serious than that, but the basics do not seem extremely complicated.

As for software engineering, a big mental block when it comes to doing these type of projects or this type of work is the uncertainty you get from it being just an idea. More specifically, it's harder to do something when its not formed out. "Make a finance tracker app" is so abstract. So instead, you plan and plan and break things down. Now it's "Build a web app that use's user verification to store financial information through a dashboard, like transactions, accounts, bills, etc." This is a lot easier to digest and manage.

## What should I do next?

This is a legitimate project will legitimate uses. Not only can I use this, but this is upgradeable and can do much more. It would be of benefit to utilize this project not just as a personal tool but as a whole learning area. Cybersecurity, web development, workflows, etc. 

Specifically after this, it would be best to actually get started with Cyberseverance. That relates to getting linkedin setup and all related apps to relate to my technical page.
