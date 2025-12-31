# Using the CRUD Router

The **CRUD Router** is one of Jetio’s most powerful productivity features.  
It allows you to turn a data model into a complete REST API with almost no code.

This guide explains **how to use it effectively**, when it’s appropriate, and how to customize its behavior.

---

## What the CRUD Router Does

When you register a model with `CrudRouter`, Jetio automatically:

- Creates REST endpoints
- Validates request data
- Serializes responses
- Integrates with OpenAPI / Swagger
- Optionally enforces authentication and ownership

All without writing individual route handlers.

---

## The Default CRUD Pattern

For each model, Jetio generates **five standard endpoints**:

| Method | Endpoint | Purpose |
|------|---------|--------|
| GET | `/{resource}` | List all items |
| POST | `/{resource}` | Create a new item |
| GET | `/{resource}/{id}` | Retrieve one item |
| PUT | `/{resource}/{id}` | Update an item |
| DELETE | `/{resource}/{id}` | Delete an item |

Where:

- `{resource}` comes from the model’s `__tablename__`
- `{id}` is the primary key

You do **not** need to define these routes manually.

---

## Minimal Example

```python
from jetio import CrudRouter
from models import User

CrudRouter(User).register_routes(app)
```

That single line gives you a complete `/users` API.

---

## Loading Related Data

By default, responses include only the model’s own fields.

To include related objects defined with SQLAlchemy relationships:

```python
CrudRouter(
    User,
    load_relationships=["posts", "comments"]
).register_routes(app)
```

Use this when:

- You want nested data in responses
- You want to avoid N+1 query problems
- You are building read-heavy APIs

---

## Disabling Unwanted Endpoints

Not every model should support full CRUD.

You can disable specific HTTP methods:

```python
CrudRouter(
    AuditLog,
    exclude_methods=["PUT", "DELETE"]
).register_routes(app)
```

This creates a **read-only API**.

---

## Securing CRUD Routes

CRUD routes are **public by default**.

To require authentication:

```python
CrudRouter(
    User,
    secure=True,
    auth_dependency=get_current_user
).register_routes(app)
```

When security is enabled:

- All routes require authentication
- Unauthorized requests return **HTTP 401**
- The authenticated user is injected automatically

---

## Method-Level Authorization Policies

Some actions require stricter rules.

Example:

- Anyone can read
- Only owners or admins can update or delete

```python
CrudRouter(
    Post,
    secure=True,
    policy={
        "GET": get_current_user,
        "POST": get_current_user,
        "PUT": owner_or_admin,
        "DELETE": owner_or_admin,
    }
).register_routes(app)
```

This allows **fine-grained authorization** without rewriting CRUD logic.

---

## Automatic Ownership Assignment

When security is enabled, Jetio can automatically populate ownership fields.

Example model:

```python
class Post(JetioModel):
    user_id: Mapped[int]
```

Behavior:

- Clients **cannot** set `user_id`
- Jetio sets `user_id = current_user.id` automatically

This prevents common security mistakes.

You can customize which fields are treated as ownership fields:

```python
CrudRouter(
    Post,
    audit_fields=["user_id"]
).register_routes(app)
```

---

## Versioning with Prefixes

You can register routes under a prefix:

```python
CrudRouter(User).register_routes(app, prefix="/v1")
```

This produces:

```
/v1/users
/v1/users/{id}
```

Useful for:

- API versioning
- Namespacing
- Modular applications

---

## When to Use (and Not Use) CRUD Router

### Use CRUD Router when:

- Your API follows standard REST patterns
- Logic is mostly data-driven
- You want fast development
- Validation and serialization are straightforward

### Avoid CRUD Router when:

- Business logic is complex
- Workflows span multiple models
- Requests do not map cleanly to CRUD operations

Jetio allows mixing CRUD routes and custom routes freely.

---

## How CRUD Router Fits Into Jetio

CRUD Router works together with:

- `JetioModel` for schema generation
- Dependency injection for authentication
- OpenAPI for documentation
- Swagger UI for interactive exploration

It is a **productivity tool**, not a limitation.

---

## Next Steps

After understanding the CRUD Router, consider:

- 🔐 Securing routes with authentication
- 🧠 Enforcing ownership and permissions
- 🧩 Combining CRUD with custom endpoints
- 🚀 Deploying a Jetio API

➡️ Continue with **Authentication & Authorization**.

---

## Final Note

This guide explains **how to think about CRUD in Jetio**.

The exact API details live in **API Reference → CRUD** and are generated directly from the code.  
This separation is intentional and professional.
