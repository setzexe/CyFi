# CyFi - Cyberseverance Finance Tracker

CyFi is a manual personal finance tracker built with the purpose of keeping budgeting simple: create your own accounts, enter transactions by hand, track recurring bills, and review totals from a single dashboard.

## Link

You can access the application here:

[CyFi](https://cyfi-9jzy.onrender.com/login)

## Demo Mode / Testing

A demo mode was developed to allow users to test the site without the commitment of creating an account. The demo mode is preloaded with values and account balances meant to stimulate a real bank account. As such, you can do what any other user would do with it; add funds, add expenses, etc.

Data on the demo account is reset when the user logs off. This ensures data stays consistent.

## Recent Updates

CyFi 1.1 was deployed on the 11 August, 2026. 

This version added a maintanence mode that is used for future updates, along with the creation of a demo account for testing purposes.

## Documentation

Documentation for this application, which goes into more specifics about both general development & cybersecurity, can be found here:

[Main Documentation](documentation/documentation.md)

[Security Documentation](documentation/security.md)

## Features 

- User accounts with secure password hashing
- Per-user bank account tracking
- Temporary demo mode with sample data
- Manual deposits and expenses
- Recurring bill management
- Recent activity & full transaction history
- Security elements like session protection, CSRF protection, and login rate limiting
- Interactive & responsive UI for desktop and mobile
- Maintanence mode for updates and downtime (app becomes unusuable to the public) 

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
- `MAINTENANCE_MODE`
- `MAINTENANCE_MESSAGE`

**Local Development:** SQLite is used automatically if `DATABASE_URL` is not set.

## Deployment

CyFi is set up to deploy from GitHub to Render. Whenever main is updated, Render pulls all changes and updates it to the build. 

## Project Notes

- The app is intentionally manual and does not connect to a bank.
- The security documentation in `documentation/security.md` explains the implementation details in more depth.

## License

This project is for personal and educational use. 

setzexe
