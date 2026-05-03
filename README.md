# CyFi - Cyberseverance Finance Tracker

CyFi is a manual personal finance tracker built with the purpose of keeping budgeting simple: create your own accounts, enter transactions by hand, track recurring bills, and review totals from a single dashboard.

## Link

You can access the application here:

# [CyFi](https://cyfi-9jzy.onrender.com/login)

## Features

- User accounts with secure password hashing
- Per-user bank account tracking
- Manual deposits and expenses
- Recurring bill management
- Recent activity & full transaction history
- Security elements like session protection, CSRF protection, and login rate limiting
- Interactive & responsive UI for desktop and mobile

## Notable Security Features

- Passwords are hashed with Werkzeug before storage
- Session cookies are hardened with `HttpOnly`, `SameSite`, and production-only `Secure`
- CSRF tokens protect form submissions and API requests
- Account's are exclusive only to the user
- Rate limitd login attempts, due to brute forcing

## Tech Stack

- Backend: Flask, Flask-Migrate, Flask-SQLAlchemy
- Database: PostgreSQL in production; SQLite for local development
- Frontend: HTML, CSS, & JavaScript
- Deployment: Render

## Local Setup

This can be run from the link above, or it can be deployed from your localhost.

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Create a `.env` file. `.env.example` is provided.
4. Run database migrations with `flask db upgrade`.
5. Start the app with `flask run`.

## Environment Variables

Create a `.env` file with the following values:

- `SECRET_KEY`
- `DATABASE_URL`

**Local Development:** SQLite is used automatically if `DATABASE_URL` is not set.

## Deployment

CyFi is set up to deploy from GitHub to Render. Whenever main is updated, Render pulls all changes and updates it to the build. 

## Project Notes

- The app is intentionally manual and does not connect to a bank.
- The security documentation in `documentation/security.md` explains the implementation details in more depth.

## License

This project is for personal and educational use. 

setzexe