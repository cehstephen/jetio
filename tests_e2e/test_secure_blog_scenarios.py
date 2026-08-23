"""Real-life scenarios against a real running app (see
apps/secure_blog_scenario_app.py) proving the class-API-via-MRO fix over
actual HTTP responses -- the wire-level bytes a real client receives, not
Pydantic schema introspection in-process (tests/test_metaclass_api_config_mro.py
already covers that).
"""

import httpx


class TestMixinDefinedExclusionAppliesOverRealHttp:
    def test_field_excluded_by_a_mixins_api_never_appears_in_a_single_item_read(self, blog_app):
        created = httpx.post(
            f"{blog_app}/posts",
            json={"title": "Launch day", "body": "public content", "internal_notes": "do not publish yet"},
        )
        assert created.status_code == 200
        post_id = created.json()["id"]

        fetched = httpx.get(f"{blog_app}/posts/{post_id}")
        assert fetched.status_code == 200
        assert "internal_notes" not in fetched.text
        assert "do not publish yet" not in fetched.text
        assert fetched.json()["title"] == "Launch day"

    def test_field_excluded_by_a_mixins_api_never_appears_in_a_list_read(self, blog_app):
        httpx.post(f"{blog_app}/posts", json={"title": "p1", "body": "b1", "internal_notes": "secret-1"})
        httpx.post(f"{blog_app}/posts", json={"title": "p2", "body": "b2", "internal_notes": "secret-2"})

        listed = httpx.get(f"{blog_app}/posts")
        assert listed.status_code == 200
        assert "secret-1" not in listed.text
        assert "secret-2" not in listed.text
        assert "internal_notes" not in listed.text


class TestModelsOwnApiTakesPriorityOverAMixins:
    def test_own_api_overrides_the_mixins_not_merges_with_it(self, blog_app):
        created = httpx.post(
            f"{blog_app}/announcements",
            json={"title": "Q3 results", "internal_notes": "visible now", "draft_text": "not yet public"},
        )
        assert created.status_code == 200
        announcement_id = created.json()["id"]

        fetched = httpx.get(f"{blog_app}/announcements/{announcement_id}")
        body = fetched.json()

        # Announcement defines its OWN `class API` (excludes draft_text),
        # which should win over InternalNotesMixin's (excludes
        # internal_notes) entirely -- not merge the two exclusion lists.
        assert "draft_text" not in body, "the model's own API.exclude_from_read should apply"
        assert body.get("internal_notes") == "visible now", (
            "the mixin's exclusion must NOT apply once the model defines its own API"
        )
