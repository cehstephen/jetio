"""Scenario app: a tiny audit-log API exercising the three PR #3 fixes
together in a realistic feature, not in isolation.

- A hand-rolled rate-limit dependency raises HTTPException(429,
  headers={"Retry-After": ...}) -- proves the header actually reaches a
  real HTTP response (not just an in-process ASGITransport call).
- /log-action determines the caller's IP from request.client rather than
  trusting a client-supplied value in the body -- the realistic reason
  Request.client needs to be public: request bodies can lie, the real
  socket peer can't.
- Just running this file at all (via app.run()) exercises the startup
  banner fix; tests_e2e/conftest.py can launch it without forcing
  PYTHONIOENCODING=utf-8 to reproduce the actual default-Windows-console
  condition.
"""

import os
import time
from collections import defaultdict, deque

from jetio import Jetio, Request, JsonResponse, Depends, CrudRouter, JetioModel, add_swagger_ui, Base, engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from starlette.exceptions import HTTPException


class AuditEvent(JetioModel):
    action: Mapped[str]
    source_ip: Mapped[str]


app = Jetio(title="Audit scenario")
add_swagger_ui(app)

# Deliberately hand-rolled rather than using jetio-ratelimit, to keep this
# scenario self-contained within the jetio repo and focused on the two
# fixes it's proving out.
_hits = defaultdict(deque)
WINDOW_SECONDS = 60
LIMIT = 3


async def rate_limit(request: Request):
    now = time.monotonic()
    key = request.client[0] if request.client else "unknown"
    hits = _hits[key]
    while hits and now - hits[0] > WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= LIMIT:
        raise HTTPException(status_code=429, detail="slow down", headers={"Retry-After": "30"})
    hits.append(now)
    return True


@app.route("/whoami", methods=["GET"])
async def whoami(request: Request):
    return JsonResponse({"client_ip": request.client[0] if request.client else None})


@app.route("/log-action", methods=["POST"])
async def log_action(request: Request, db: AsyncSession, ok=Depends(rate_limit)):
    body = await request.json()
    real_ip = request.client[0] if request.client else "unknown"
    # Server-determined IP, NOT the (possibly spoofed) one a caller could
    # put in the request body -- this is the point of the scenario.
    action = body.get("action", "unknown")
    event = AuditEvent(action=action, source_ip=real_ip)
    db.add(event)
    await db.flush()
    event_id = event.id
    await db.commit()
    return JsonResponse({"id": event_id, "action": action, "source_ip": real_ip}, status_code=201)


CrudRouter(model=AuditEvent, exclude_methods=["POST"]).register_routes(app)


@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ["JETIO_APP_PORT"]))
