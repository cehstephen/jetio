# Example: Basic Auth + Secured CRUD

This app demonstrates the baseline integration of `jetio-auth` with jetio, it auto creates secured CRUD.

## Features

- `POST /register`, `POST /login` via `AuthRouter`
- `POST /admin/{item_id}/make-admin` via `register_admin_routes`
- Secured CRUD for `Post`
- Owner-or-admin policy on `PUT`/`DELETE`
- Custom `GET /me` endpoint
- Admin bootstrap endpoint (`POST /bootstrap-admin`)

## Run

```bash
cd examples/jetio-basic-auth
python app.py
```

## Typical Flow

1. Register user
2. Login and copy token
3. Create post with `Authorization: Bearer <token>`
4. Update/delete own post
5. Promote another user using admin route
