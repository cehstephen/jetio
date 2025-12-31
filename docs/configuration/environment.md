# Environment Configuration

Jetio uses a **typed settings model** (Pydantic Settings) to manage configuration in a
clean, safe, and production-friendly way. Settings can be provided via:

- **Environment variables**
- A local **`.env` file**
- Defaults defined in `jetio/config.py`

This page documents Jetio’s built-in settings and how to configure them across
development, testing, and production.

---

## How Jetio Loads Settings

Jetio defines a `Settings` class in `jetio.config` and creates a single shared instance:

```python
from jetio.config import settings
```

Jetio reads settings in this order:

1. **Environment variables** (highest priority)
2. Values from a **`.env` file**
3. **Defaults** defined in `Settings`

This means you can keep sensible defaults for development while safely overriding
values in production.

---

## `.env` File Location

Jetio looks for a `.env` file at your **project root** (relative to Jetio’s package):

- `PROJECT_ROOT = Path(__file__).resolve().parent.parent`
- `.env` path: `PROJECT_ROOT / ".env"`

### Recommended: Do not commit `.env`

Add this to `.gitignore`:

```gitignore
.env
```

---

## Built-in Settings Reference

These are the settings currently defined in `jetio/config.py`.

> Tip: Environment variables use the same names as the fields below
> (e.g. `DATABASE_URL`, `MAIL_MODE`, `MAIL_PORT`).

---

### Database

#### `DATABASE_URL`

SQLAlchemy connection string used by Jetio’s async engine.

Default:

```env
DATABASE_URL="sqlite+aiosqlite:///./jetio.db"
```

Examples:

**SQLite (development)**

```env
DATABASE_URL="sqlite+aiosqlite:///./app.db"
```

**PostgreSQL**

```env
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/mydb"
```

**MySQL**

```env
DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/mydb"
```

See also: *Configuration → Database Setup*.

---

### Security

#### `SECRET_KEY`

Secret used for cryptographic signing (e.g., JWT signing).

Default: a fixed string in `jetio/config.py` (safe for local development only).

**Production requirement:**
Set a strong secret via environment variable or `.env`:

```env
SECRET_KEY="your-long-random-secret"
```

> ⚠️ Never use the default `SECRET_KEY` in production.

---

### Domain / Base URL

#### `DOMAIN`

Base URL used by Jetio for building absolute URLs in places like:
- emails (verification links, password reset links)
- callbacks or externally visible URLs

Default:

```env
DOMAIN="http://127.0.0.1:8000"
```

Example (production):

```env
DOMAIN="https://api.example.com"
```

---

## Mail Configuration

Jetio includes built-in mail configuration to support features like:

- account verification
- password reset
- notification emails

### `MAIL_MODE`

Controls how mail is delivered.

- `console` (default): prints emails to console (development-friendly)
- `smtp`: sends real emails via an SMTP server

Example:

```env
MAIL_MODE="smtp"
```

---

### SMTP Credentials and Settings

These settings are used when `MAIL_MODE="smtp"`:

- `MAIL_USERNAME` (default: `default_user`)
- `MAIL_PASSWORD` (default: `default_pass`)
- `MAIL_FROM` (default: `default@example.com`)
- `MAIL_SERVER` (default: `smtp.example.com`)
- `MAIL_PORT` (default: `587`)

Example SMTP configuration:

```env
MAIL_MODE="smtp"
MAIL_SERVER="smtp.gmail.com"
MAIL_PORT=587
MAIL_USERNAME="your-email@gmail.com"
MAIL_PASSWORD="your-app-password"
MAIL_FROM="your-email@gmail.com"
```

> ℹ️ For Gmail and many providers, you should use an **App Password** instead of your normal password.

---

### TLS / SSL Options

Jetio exposes common SMTP security flags:

- `MAIL_STARTTLS` (default: `True`)
- `MAIL_SSL_TLS` (default: `False`)

Typical settings:

- Port `587` → `MAIL_STARTTLS=True`
- Port `465` → `MAIL_SSL_TLS=True`

Example (TLS / 587):

```env
MAIL_PORT=587
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
```

Example (SSL / 465):

```env
MAIL_PORT=465
MAIL_STARTTLS=False
MAIL_SSL_TLS=True
```

---

### Advanced Mail Options

Jetio also supports:

- `MAIL_USE_CREDENTIALS` (default: `True`)
- `MAIL_VALIDATE_CERTS` (default: `True`)

In production you generally want:

```env
MAIL_USE_CREDENTIALS=True
MAIL_VALIDATE_CERTS=True
```

---

## Example `.env` Files

### Minimal Development (`console` mail + SQLite)

```env
DATABASE_URL="sqlite+aiosqlite:///./jetio.db"
SECRET_KEY="dev-only-secret"
DOMAIN="http://127.0.0.1:8000"
MAIL_MODE="console"
```

### Production Example (PostgreSQL + SMTP)

```env
DATABASE_URL="postgresql+asyncpg://user:password@db-host:5432/proddb"
SECRET_KEY="very-long-random-production-secret"
DOMAIN="https://api.example.com"

MAIL_MODE="smtp"
MAIL_SERVER="smtp.example.com"
MAIL_PORT=587
MAIL_USERNAME="smtp-user"
MAIL_PASSWORD="smtp-password"
MAIL_FROM="no-reply@example.com"
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
MAIL_USE_CREDENTIALS=True
MAIL_VALIDATE_CERTS=True
```

---

## Extra Environment Variables

Jetio’s settings config uses:

- `extra="ignore"`

Meaning: extra env vars that are not defined in `Settings` are ignored.
This is helpful when deploying in environments that inject many unrelated vars.

---

## Troubleshooting

### “My `.env` changes aren’t applied”

- Ensure `.env` is located at the expected project root
- Restart your process (settings are loaded at import time)
- Check for typos in variable names (must match exactly)


---

## Summary

Jetio configuration is:

- **Typed** (Pydantic Settings)
- **Environment-first**
- `.env` friendly for development
- Safe defaults for local use
- Easy to override for production

---

## Next Steps

- Database Configuration
- Authentication & Security
- Deployment Guides
