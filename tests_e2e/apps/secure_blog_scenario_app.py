"""Scenario app: a small blog API with a mixin-provided `class API`
(exclude_from_read defined on a mixin, not the model itself) -- the exact
shape jetio-auth's JetioAuthMixin uses to hide hashed_password. Proves the
MRO-lookup fix over real HTTP responses, not just Pydantic schema
introspection.
"""

import os

from jetio import Jetio, CrudRouter, JetioModel, add_swagger_ui, Base, engine
from sqlalchemy.orm import Mapped


class InternalNotesMixin:
    class API:
        exclude_from_read = ["internal_notes"]


class Post(InternalNotesMixin, JetioModel):
    title: Mapped[str]
    body: Mapped[str]
    internal_notes: Mapped[str]


class Announcement(InternalNotesMixin, JetioModel):
    # Defines its own API -- this should take priority over the mixin's,
    # per normal Python attribute-resolution semantics (most-derived
    # class wins), not merge with it.
    class API:
        exclude_from_read = ["draft_text"]

    title: Mapped[str]
    internal_notes: Mapped[str]
    draft_text: Mapped[str]


app = Jetio(title="Secure blog scenario")
add_swagger_ui(app)

CrudRouter(model=Post).register_routes(app)
CrudRouter(model=Announcement).register_routes(app)


@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ["JETIO_APP_PORT"]))
