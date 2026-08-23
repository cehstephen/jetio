"""Real-life scenarios against a real running app (see
apps/audit_scenario_app.py) -- actual subprocess, actual HTTP, actual
sqlite-backed state. Complements the in-process unit tests in
tests/test_framework_fixes.py; those prove the mechanism, these prove it
holds up as a deployed app.
"""

import httpx


class TestRetryAfterReachesRealHttpResponses:
    def test_rate_limit_429_carries_a_real_retry_after_header(self, audit_app):
        for _ in range(3):
            resp = httpx.post(f"{audit_app}/log-action", json={"action": "noop"})
            assert resp.status_code == 201

        blocked = httpx.post(f"{audit_app}/log-action", json={"action": "noop"})
        assert blocked.status_code == 429
        assert blocked.headers.get("retry-after") == "30"


class TestRequestClientIsTrustworthy:
    def test_whoami_reports_the_real_connecting_address(self, audit_app):
        resp = httpx.get(f"{audit_app}/whoami")
        assert resp.status_code == 200
        assert resp.json()["client_ip"] == "127.0.0.1"

    def test_logged_events_record_the_real_ip_not_a_client_supplied_one(self, audit_app):
        # The scenario app deliberately ignores any "source_ip" in the
        # request body and uses request.client instead -- a request body
        # is caller-controlled and can lie; the actual socket peer can't.
        resp = httpx.post(f"{audit_app}/log-action", json={"action": "login", "source_ip": "203.0.113.99"})
        assert resp.status_code == 201
        assert resp.json()["source_ip"] == "127.0.0.1"

        event_id = resp.json()["id"]
        readback = httpx.get(f"{audit_app}/auditevents/{event_id}")
        assert readback.json()["source_ip"] == "127.0.0.1"


class TestStartupSurvivesNonUtf8Stdout:
    def test_app_starts_when_launched_without_forcing_utf8(self, audit_app_default_console_encoding):
        # The actual scenario the fix targets: a real subprocess launched
        # the way the default Windows console would run it, with nothing
        # forcing PYTHONIOENCODING. Before the fix, this crashed on the
        # emoji in the startup print before the server ever bound its port.
        resp = httpx.get(f"{audit_app_default_console_encoding}/whoami", timeout=2.0)
        assert resp.status_code == 200
