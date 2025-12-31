# Database Configuration

Jetio uses **SQLAlchemy’s async engine** under the hood, which allows it to work
with multiple database backends using a single configuration pattern.

This guide explains how database configuration works in Jetio and how to switch
between SQLite, PostgreSQL, and MySQL.

---

## Default Database (SQLite)

Jetio uses **SQLite by default** when no database configuration is provided.

This makes it ideal for:

- Local development
- Tutorials and examples
- Small projects
- Rapid prototyping

No additional setup is required.

### Example

If no `DATABASE_URL` is set, Jetio will automatically use SQLite.

You can start your application immediately:

```bash
python app.py
```

---

## How Database Configuration Works

Jetio reads database configuration from the `DATABASE_URL` environment variable.

General format:

```
DATABASE_URL="dialect+driver://user:password@host:port/database"
```

Jetio passes this value directly to SQLAlchemy’s async engine.

---

## Using Environment Variables

You can define `DATABASE_URL` using your shell or a `.env` file.

### Example (shell)

```bash
export DATABASE_URL="sqlite+aiosqlite:///./app.db"
```

### Example (`.env` file)

```env
DATABASE_URL="sqlite+aiosqlite:///./app.db"
```

> ℹ️ Jetio automatically loads `.env` files if `python-dotenv` is installed.

---

## PostgreSQL Configuration

PostgreSQL is recommended for production deployments.

### 1. Install the driver

```bash
pip install asyncpg
```

### 2. Set `DATABASE_URL`

```env
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/mydatabase"
```

### Notes

- Jetio uses `asyncpg` for async PostgreSQL support
- The database must exist before running the app
- Connection pooling is handled automatically by SQLAlchemy

---

## MySQL Configuration

Jetio also supports MySQL via async drivers.

### 1. Install the driver

```bash
pip install aiomysql
```

### 2. Set `DATABASE_URL`

```env
DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/mydatabase"
```

### Notes

- Ensure the database exists beforehand
- MySQL 8+ is recommended
- Async performance depends on driver and server configuration

---

## Creating Database Tables

Jetio does **not** run migrations automatically.

For development, you can create tables using:

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

> ⚠️ Do not use `drop_all()` in production environments.

For production systems, consider:
- Alembic migrations
- Manual schema management

---

## Multiple Environments

A common pattern is to use different databases per environment:

| Environment | Database |
|------------|----------|
| Development | SQLite |
| Testing | SQLite / PostgreSQL |
| Production | PostgreSQL |

You can switch databases simply by changing `DATABASE_URL`.

---

## Troubleshooting

### Database connection errors

- Verify the driver is installed
- Ensure credentials are correct
- Confirm the database exists
- Check network access

### Import-time errors during documentation builds

If documentation tools import Jetio without a database available,
set a safe default:

```env
DATABASE_URL="sqlite+aiosqlite:///./docs.db"
```

---

## Summary

Jetio’s database configuration is:

- Simple
- Flexible
- Environment-driven
- Fully powered by SQLAlchemy

Start with SQLite, and scale to PostgreSQL or MySQL when needed.

---

## Next Steps

- Environment Variables
- Authentication & Security
- Deployment Guides
