import os
import asyncio

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./example_basic_auth.db")
os.environ.setdefault("DOMAIN", "http://127.0.0.1:8000")

from jetio import Base, CrudRouter, Jetio, Request, SessionLocal, add_swagger_ui, engine
from jetio.framework import Depends, JsonResponse
from jetio_auth import AuthRouter

from models import Post, User


app = Jetio(title="Jetio Example - Basic Auth CRUD")
add_swagger_ui(app)

auth = AuthRouter(user_model=User)
auth.register_routes(app)
auth.register_admin_routes(app)

CrudRouter(
    model=Post,
    secure=True,
    auth_dependency=auth.get_auth_dependency(),
    policy={
        "PUT": auth.owner_or_admin(Post),
        "DELETE": auth.owner_or_admin(Post),
    },
).register_routes(app)


@app.route("/me", methods=["GET"])
async def me(user=Depends(auth.get_auth_dependency())):
    return {
        "id": int(user.id),
        "username": user.username,
        "email": user.email,
        "is_admin": bool(user.is_admin),
    }

# Not to be used in production
@app.route("/bootstrap-admin", methods=["POST"])
async def bootstrap_admin(request: Request):
    payload = await request.json()
    username = payload.get("username", "admin")
    password = payload.get("password", "admin123")
    email = payload.get("email", "admin@example.com")

    async with SessionLocal() as db:
        admin = await auth.ensure_admin(db=db, username=username, password=password, email=email)

    return JsonResponse(
        {
            "message": "Admin account created",
            "username": username,
            "is_admin": bool(admin.is_admin),
        },
        status_code=200,
    )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
    app.run()
