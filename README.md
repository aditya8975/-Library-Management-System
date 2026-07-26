# Library Management System

A production-style REST API for managing a library's book catalog, user accounts, and the full book issue/return workflow — built with **FastAPI**, **SQLAlchemy**, and **MySQL**.

Built as a backend portfolio project to demonstrate Python, SQL, REST API design, clean OOP structure, and JWT-based auth in a real (not toy) codebase.

## Features

- **JWT Authentication** — register, login, `/auth/me`, token-based route protection
- **Role-based access control** — `admin` and `student` roles enforced at the endpoint level
- **Book management (CRUD)** — admins manage the catalog; everyone can browse/search it
- **Issue / Return workflow** — copy-count tracking, duplicate-issue prevention, due dates
- **Fine calculation** — configurable per-day fine, automatically computed on overdue returns
- **Search & filtering** — by title, author, category, availability
- **Pagination** — on books, users, and issue records
- **Clean layered architecture** — routers / schemas / models / security are fully separated

## Tech Stack

| Layer          | Technology                     |
|----------------|---------------------------------|
| Language       | Python 3.11+                   |
| Framework      | FastAPI                        |
| Database       | MySQL (via PyMySQL)            |
| ORM            | SQLAlchemy 2.0                 |
| Auth           | JWT (python-jose) + bcrypt     |
| Validation     | Pydantic v2                    |
| Server         | Uvicorn                        |

> The app also runs against SQLite with zero code changes — handy for quickly trying it out without setting up MySQL. See [Quick local test](#quick-local-test-no-mysql-needed).

## Project Structure

```
library-management-system/
├── app/
│   ├── main.py            # FastAPI app, startup bootstrap, CORS
│   ├── config.py          # Settings loaded from environment / .env
│   ├── database.py        # SQLAlchemy engine & session
│   ├── models.py          # ORM models: User, Book, IssueRecord
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── security.py        # Password hashing + JWT helpers
│   ├── dependencies.py    # Auth guards (get_current_user, require_admin)
│   ├── seed.py            # Sample book data loader
│   └── routers/
│       ├── auth.py        # /auth/register, /auth/login, /auth/me
│       ├── users.py       # Admin user management
│       ├── books.py       # Book catalog CRUD + search/filter/pagination
│       └── issues.py      # Issue / return / fines
├── requirements.txt
├── .env.example
└── .gitignore
```

## Data Model

**User** — `id, username, email, full_name, hashed_password, role, is_active, created_at`

**Book** — `id, title, author, isbn, category, published_year, description, total_copies, available_copies, created_at`

**IssueRecord** — `id, book_id, user_id, issue_date, due_date, return_date, fine_amount, fine_paid, status, created_at`

## Setup (MySQL / Production)

1. **Clone and enter the project**
   ```bash
   git clone <your-repo-url>
   cd library-management-system
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create the MySQL database**
   ```sql
   CREATE DATABASE library_db CHARACTER SET utf8mb4;
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # edit .env — set DATABASE_URL, SECRET_KEY, etc.
   ```
   Generate a real secret key:
   ```bash
   openssl rand -hex 32
   ```

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```
   Tables are created automatically on first startup, and a default admin account is bootstrapped from the `DEFAULT_ADMIN_*` values in `.env` (only if no users exist yet — change that password immediately after first login).

6. **(Optional) Load sample books**
   ```bash
   python -m app.seed
   ```

7. **Open the interactive docs**
   - Swagger UI → http://localhost:8000/docs
   - ReDoc → http://localhost:8000/redoc

## Quick local test (no MySQL needed)

For a fast try-it-out loop without installing MySQL:

```bash
pip install -r requirements.txt
DATABASE_URL="sqlite:///./library.db" python -m app.seed
DATABASE_URL="sqlite:///./library.db" uvicorn app.main:app --reload
```

Everything — auth, CRUD, issue/return, fines — behaves identically; only the connection string changes. Switch back to a `mysql+pymysql://...` URL for production.

## API Overview

| Method | Endpoint                     | Access        | Description                          |
|--------|-------------------------------|----------------|---------------------------------------|
| POST   | `/auth/register`              | Public         | Self-register as a student           |
| POST   | `/auth/login`                 | Public         | Get a JWT access token               |
| GET    | `/auth/me`                    | Authenticated  | Current user's profile               |
| GET    | `/users`                      | Admin          | List/search/paginate users           |
| POST   | `/users/admin-create`         | Admin          | Create a user with any role          |
| PATCH  | `/users/{id}`                 | Admin          | Update a user                        |
| DELETE | `/users/{id}`                 | Admin          | Delete a user                        |
| GET    | `/books`                      | Public         | Browse/search/filter/paginate books  |
| POST   | `/books`                      | Admin          | Add a book                           |
| PUT    | `/books/{id}`                 | Admin          | Update a book                        |
| DELETE | `/books/{id}`                 | Admin          | Delete a book (if none are issued)   |
| POST   | `/issues`                     | Authenticated  | Issue a book                         |
| POST   | `/issues/return`              | Authenticated  | Return a book (fine auto-calculated) |
| GET    | `/issues`                     | Authenticated  | Own history (student) / all (admin)  |
| POST   | `/issues/{id}/pay-fine`       | Admin          | Mark a fine as paid                  |

Full interactive documentation with request/response schemas is available at `/docs` once the server is running.

## Business Rules

- Issue period and fine rate are configurable via `.env`: `ISSUE_PERIOD_DAYS` (default 14 days) and `FINE_PER_DAY` (default ₹5).
- A student cannot hold two copies of the same book at once.
- A book cannot be deleted while any copy is currently issued out.
- Overdue fines are calculated by rounding up to the next full day past the due date.

## Notes on Design Decisions

- **Regex email validation instead of `EmailStr`**: Pydantic's `EmailStr` (via `email-validator`) performs live DNS/MX lookups to check deliverability. That makes signups fail unpredictably on any host without outbound DNS access (e.g. sandboxed CI, offline demos). This project uses a simple, dependency-free email pattern check instead — sufficient for this use case and fully self-contained.
- **SQLite fallback**: `DATABASE_URL` is the single source of truth for the DB backend, so the same code works against MySQL or SQLite without branching logic.

## License

MIT — free to use for learning, portfolio, or as a base for further projects.
