"""Email notification preferences: news recipient filtering + profile toggles.

Covers the opt-in flags added to ``anglers`` (email_opt_in / notify_news /
notify_replies) as they affect the news blast recipient list and the profile
settings form. Reply-notification behavior lives in test_poll_discussion.py.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from tests.conftest import post_with_csrf


class TestNewsRecipientFiltering:
    def test_opted_out_members_excluded(
        self, admin_client: TestClient, db_session: Session, monkeypatch
    ):
        captured: dict = {}
        monkeypatch.setattr(
            "routes.admin.core.news.send_news_notification",
            lambda emails, *a, **k: captured.setdefault("emails", emails) is None,
        )
        db_session.add_all(
            [
                Angler(name="In", email="in@example.com", member=True),
                Angler(
                    name="MasterOff", email="masteroff@example.com", member=True, email_opt_in=False
                ),
                Angler(name="NewsOff", email="newsoff@example.com", member=True, notify_news=False),
            ]
        )
        db_session.commit()

        post_with_csrf(
            admin_client, "/admin/news/create", data={"title": "Big News", "content": "Body"}
        )

        emails = captured.get("emails", [])
        assert "in@example.com" in emails
        assert "masteroff@example.com" not in emails
        assert "newsoff@example.com" not in emails


class TestProfileNotificationSettings:
    def test_view_shows_instant_save_switches(self, member_client: TestClient, member_user: Angler):
        # Switches live in the always-visible view and post to the instant-save
        # endpoint — no Edit mode needed.
        resp = member_client.get("/profile")
        assert resp.status_code == 200
        assert 'hx-post="/profile/notifications"' in resp.text
        assert 'id="notifMaster"' in resp.text  # master switch, wired for JS greying
        assert "notif-subtoggles" in resp.text  # News/Discussion indented under it
        assert 'name="email_opt_in"' in resp.text
        assert 'name="notify_news"' in resp.text
        assert 'name="notify_replies"' in resp.text

    def test_switches_reflect_saved_state(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        member_user.notify_news = False
        db_session.commit()
        resp = member_client.get("/profile")
        # notify_news off -> that switch is not checked; the others still are.
        assert 'name="notify_news" value="1" checked' not in resp.text
        assert 'name="notify_replies" value="1" checked' in resp.text
        assert 'name="email_opt_in" value="1" checked' in resp.text

    def test_toggle_saves_instantly(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        # Master + news checked, replies omitted (unchecked) -> saved right away.
        resp = post_with_csrf(
            member_client,
            "/profile/notifications",
            data={"email_opt_in": "1", "notify_news": "1"},
        )
        assert resp.status_code == 200
        assert "Saved" in resp.text
        db_session.expire_all()
        angler = db_session.query(Angler).filter(Angler.id == member_user.id).one()
        assert angler.email_opt_in is True
        assert angler.notify_news is True
        assert angler.notify_replies is False

    def test_master_switch_off_saved(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        post_with_csrf(
            member_client,
            "/profile/notifications",
            data={"notify_news": "1", "notify_replies": "1"},  # master omitted
        )
        db_session.expire_all()
        angler = db_session.query(Angler).filter(Angler.id == member_user.id).one()
        assert angler.email_opt_in is False

    def test_all_on_saved(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        member_user.email_opt_in = False
        member_user.notify_news = False
        member_user.notify_replies = False
        db_session.commit()

        post_with_csrf(
            member_client,
            "/profile/notifications",
            data={"email_opt_in": "1", "notify_news": "1", "notify_replies": "1"},
        )
        db_session.expire_all()
        angler = db_session.query(Angler).filter(Angler.id == member_user.id).one()
        assert angler.email_opt_in is True
        assert angler.notify_news is True
        assert angler.notify_replies is True

    def test_update_profile_leaves_notifications_untouched(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        # Saving the main profile form must not clobber notification prefs
        # (they're owned by /profile/notifications now).
        post_with_csrf(
            member_client,
            "/profile/update",
            data={"email": member_user.email, "phone": "", "year_joined": 2024},
        )
        db_session.expire_all()
        angler = db_session.query(Angler).filter(Angler.id == member_user.id).one()
        assert angler.email_opt_in is True
        assert angler.notify_news is True
        assert angler.notify_replies is True
