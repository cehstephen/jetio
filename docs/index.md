# Jetio Documentation

**Jetio** is a zero-boilerplate Python framework that turns SQLAlchemy models into production-ready APIs with minimal code — working seamlessly with SQLite, PostgreSQL, MySQL, and any database supported by SQLAlchemy.

- **Model-driven**: your SQLAlchemy models are the single source of truth  
- **Automatic CRUD**: generate REST endpoints in one line  
- **Async-first**: built for speed and scalability  
- **Secure-by-design**: dependency-based security + policy overrides  
- **Automatic docs**: Swagger UI and OpenAPI out of the box  

---

## Quickstart

### 1) Install

```bash
pip install jetio
```

### 2) Define your models

Jetio automatically generates table names for you based on your model names.

For example, a `User` model will map to a `users` table **without any configuration**.

```python
# models.py
from sqlalchemy.orm import Mapped
from jetio import JetioModel

class User(JetioModel):
    username: Mapped[str]
    email: Mapped[str]
```

➡️ The table name will automatically be **`users`**.

#### Overriding the table name (optional)

If you want a custom table name (for example, when integrating with an existing database),
you can explicitly declare `__tablename__`. Jetio will always respect your declaration.

```python
class User(JetioModel):
    __tablename__ = "accounts"  # Overrides the default

    username: Mapped[str]
    email: Mapped[str]
```

---

### 3) Create the app + generate CRUD routes

```python
# app.py
from jetio import Jetio, CrudRouter, add_swagger_ui
from models import User

app = Jetio(title="My Jetio API")

# Optional but recommended: interactive API documentation at /docs
add_swagger_ui(app)

# Automatically generates 5 REST endpoints for the model
CrudRouter(model=User).register_routes(app)

if __name__ == "__main__":
    app.run()
```

Run it:

```bash
python app.py
```

- API is live at: `http://127.0.0.1:8000`
- Swagger UI at: `http://127.0.0.1:8000/docs`

---

## What Jetio Generates

For each model registered with `CrudRouter`, Jetio generates five standard endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/{resource}` | List all records |
| POST | `/{resource}` | Create a record |
| GET | `/{resource}/{id}` | Retrieve a record |
| PUT | `/{resource}/{id}` | Update a record |
| DELETE | `/{resource}/{id}` | Delete a record |

- `{resource}` is derived from the model’s `__tablename__`
- `{id}` is the model’s primary key

---

## Documentation Structure

Jetio documentation is organized into three layers:

- **Guides** → learn workflows and patterns (CRUD, authentication, tutorials)
- **Configuration** → environment variables, database setup, mail settings
- **Reference** → auto-generated API reference from the source code

This keeps guides approachable while ensuring the reference stays accurate.

---

## Where to Start

If you’re new to Jetio:

1. **Guides → CRUD Router**  
   Learn how models become APIs.

2. **Guides → Authentication**  
   Secure your app using the official `jetio-auth` plugin.

3. **Configuration → Database Setup**  
   Switch from SQLite to PostgreSQL or MySQL.

4. **Configuration → Environment Variables**  
   Configure settings cleanly using `.env` files.

---

## Authentication (Optional, Recommended)

Jetio integrates seamlessly with the official **`jetio-auth`** package for JWT-based authentication.

Install:

```bash
pip install jetio-auth
```

Register authentication routes:

```python
from jetio_auth import AuthRouter
from models import User

auth = AuthRouter(user_model=User)
auth.register_routes(app)         # /register, /login
auth.register_admin_routes(app)   # /admin/{id}/make-admin
```

Secure CRUD routes:

```python
from jetio import CrudRouter

CrudRouter(
    model=Post,
    secure=True,
    auth_dependency=auth.get_auth_dependency(),
    policy={
        "PUT": auth.owner_or_admin(Post),
        "DELETE": auth.admin_only(),
    }
).register_routes(app)
```

---

## Philosophy

Jetio follows **convention over configuration**:

- sensible defaults
- minimal boilerplate
- explicit overrides when needed

If you’re building APIs where development speed and clarity matter, Jetio is designed to help you ship faster—without sacrificing structure.

---

## Links

- Website: https://jetio.org  
- GitHub: https://github.com/cehstephen/jetio  
- PyPI: https://pypi.org/project/jetio/
