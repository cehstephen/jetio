# Authentication with Jetio

Jetio provides first-class authentication support through the official
**`jetio-auth`** package. This plugin offers a secure, zero-configuration
authentication system that integrates directly with your Jetio models
and CRUD APIs.

This guide explains how to add authentication to your Jetio application
using `jetio-auth`, from basic setup to securing CRUD routes.

---

## What Is `jetio-auth`?

`jetio-auth` is an official Jetio plugin that provides:

- User registration and login
- Secure password hashing
- JWT-based authentication
- Role and permission enforcement
- Ownership-based access control

It is designed to work *with* Jetio’s philosophy:
**models are the single source of truth**.

---

## Installation

Install the package from PyPI:

```bash
pip install jetio-auth
```

No additional configuration is required to get started.

---

## Defining a User Model

To enable authentication, your User model must inherit from
`JetioAuthMixin`.

This mixin automatically adds:

- `hashed_password`
- Admin / permission flags (e.g. `is_admin`)

### Example

```python
# models.py
from jetio import JetioModel
from jetio_auth import JetioAuthMixin
from sqlalchemy.orm import Mapped, mapped_column

class User(JetioModel, JetioAuthMixin):
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    age: Mapped[int] = mapped_column(default=18)
```

You only define identity and profile fields.
Authentication fields are handled by the mixin.

---

## Putting It All Together (A Working `app.py`)

Below is a minimal but complete example that:

- creates a Jetio app
- enables Swagger UI (`/docs`)
- registers authentication routes (`/register`, `/login`)
- registers admin routes (`/admin/{id}/make-admin`)

```python
# app.py
from jetio import Jetio, add_swagger_ui
from jetio_auth import AuthRouter
from models import User

# Create the Jetio application
app = Jetio(title="Jetio Blog")

# Optional but recommended: interactive API documentation at /docs
add_swagger_ui(app)

# Initialize authentication using the User model
auth = AuthRouter(user_model=User)

# Register authentication endpoints (/register, /login)
auth.register_routes(app)

# Register admin management endpoints (/admin/{id}/make-admin)
auth.register_admin_routes(app)

if __name__ == "__main__":
    app.run()
```

> ℹ️ If you do not call `add_swagger_ui(app)`, your endpoints still work normally,
> but `/docs` will not be available.

---

## Registering and Logging In

### Register a User

```bash
POST /register
Content-Type: application/json

{
  "username": "alice",
  "email": "alice@example.com",
  "password": "secret123",
  "age": 25
}
```

Fields are validated dynamically based on your User model.

### Login

```bash
POST /login
Content-Type: application/json

{
  "username": "alice",
  "password": "secret123"
}
```

Successful login returns a JWT access token.

---

## Protecting CRUD Routes

`jetio-auth` integrates seamlessly with Jetio’s `CrudRouter`.

### Basic Protection

```python
from jetio import CrudRouter

CrudRouter(
    model=Post,
    secure=True,
    auth_dependency=auth.get_auth_dependency()
).register_routes(app)
```

This ensures:

- Only authenticated users can access the routes
- JWT tokens are validated automatically

---

## Ownership and Role-Based Policies

### Owner or Admin

```python
CrudRouter(
    model=Post,
    secure=True,
    auth_dependency=auth.get_auth_dependency(),
    policy={
        "PUT": auth.owner_or_admin(Post),
        "DELETE": auth.owner_or_admin(Post),
    }
).register_routes(app)
```

- Owners can modify their own records
- Admins can modify any record

### Admin-Only Access

```python
policy={
    "DELETE": auth.admin_only()
}
```

Only admin users may perform the action.

---

## Creating the First Admin

For security reasons, users cannot register themselves as admins.

Use `ensure_admin` during application startup:

```python
async def init_db():
    async with AsyncSession(engine) as session:
        await auth.ensure_admin(
            db=session,
            username="admin",
            password="securePassword123",
            email="admin@jetio.org"
        )
```

This operation is **idempotent** and safe to run on every startup.

---

## How Permissions Are Detected

`jetio-auth` automatically discovers admin flags in your User model.
It checks for the following fields (in order):

1. `is_admin`
2. `is_superuser`
3. `is_staff`
4. `is_master`

The first match becomes the authority for admin-only policies.

No configuration is required.

---

## Security Guarantees

`jetio-auth` is secure by default:

- Passwords are hashed using **bcrypt**
- Mass assignment is prevented
- Admin fields are excluded from registration
- JWTs follow standard signing and expiration practices

---

## When to Use `jetio-auth`

Use `jetio-auth` when:

- You need standard authentication quickly
- You want minimal configuration
- Your app follows REST + JWT patterns
- You want ownership and admin controls

For custom authentication flows, Jetio still allows manual implementations.

---

## Summary

`jetio-auth` provides:

- Plug-and-play authentication
- Secure defaults
- Tight integration with CRUD routes
- Minimal boilerplate

It is the recommended way to add authentication to Jetio applications.

---

## Next Steps

- Securing APIs with CRUD Router
- Email verification and password resets
- Deploying authenticated Jetio apps
