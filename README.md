# Digital Library Management System

A production-style college library web app: **Django** (Python) backend, **Bootstrap 5** frontend, **MySQL** (or **SQLite** for a quick local run). Features include student registration, admin catalog control, issue approval workflow, reservations with email notifications, overdue fines (₹5/day), and scheduled due-date reminders.

## Requirements

- Python 3.10+
- Optional: MySQL 8.x (for production-like setup)
- Optional: SMTP credentials for real email (otherwise emails print to the console in development)

## Quick start (SQLite, no MySQL)

From the `library_system` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file (copy from `.env.example`) or set environment variables:

```env
USE_SQLITE=true
DJANGO_DEBUG=true
```

Run migrations and create an administrator:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

`createsuperuser` asks for **username**, **email**, and **password** (and any other prompted fields). Superusers are created with **staff** and **superuser**.

Start the server:

```powershell
python manage.py runserver
```

Open **http://127.0.0.1:8000/**. Django admin (optional) is at **http://127.0.0.1:8000/admin/django/**.

Students register at **/register/**. All users sign in at **/login/** using an **OTP sent to their email**.

## MySQL setup

1. Create a database and user (example):

   ```sql
   CREATE DATABASE library_db CHARACTER SET utf8mb4;
   CREATE USER 'libuser'@'localhost' IDENTIFIED BY 'yourpassword';
   GRANT ALL ON library_db.* TO 'libuser'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. Set in `.env` (do **not** set `USE_SQLITE`, or set `USE_SQLITE=false`):

   ```env
   MYSQL_DATABASE=library_db
   MYSQL_USER=libuser
   MYSQL_PASSWORD=yourpassword
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   ```

3. On Windows, the project uses **PyMySQL** as a `mysqlclient` substitute (see `library_system/__init__.py`). On Linux/macOS, `mysqlclient` is recommended; install system MySQL dev headers if needed.

4. Run `python manage.py migrate`.

## Email (reminders & reservations)

By default, `EMAIL_BACKEND` is Django’s **console** backend (messages appear in the terminal).

For SMTP (e.g. Gmail with an app password), set in `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Library <your@gmail.com>
```

### Due-date reminders (2 days before)

Run daily (Task Scheduler on Windows, `cron` on Linux):

```powershell
python manage.py send_due_reminders
```

### Overdue notifications (includes fine estimate)

Run daily:

```powershell
python manage.py notify_overdue_books
```

## Optional demo books

```powershell
python manage.py seed_books
```

## Project layout

- `library_system/` — settings, root URLs
- `accounts/` — custom user (email login, roles), home, dashboards, registration
- `books/` — catalog CRUD, list/search/detail, covers in `media/book_covers/`
- `issues/` — requests, approval, returns, fines, admin queues
- `reservations/` — waitlist and notifications when a copy is returned
- `templates/` — HTML templates
- `static/` — CSS and JS (including dark mode toggle)

## Security notes for real deployment

- Set `DJANGO_SECRET_KEY` and `DJANGO_DEBUG=false`
- Configure `DJANGO_ALLOWED_HOSTS`
- Use HTTPS and a proper SMTP provider
- Run `collectstatic` and serve static/media with your web server
