"""End-to-end password reset and login test.

This test simulates the complete user flow:
1. User requests password reset
2. Token is generated
3. User clicks link and submits new password
4. User logs in with new password
"""

from datetime import datetime, timezone

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from core.email import create_password_reset_token


def test_complete_password_reset_and_login_flow(client: TestClient, db_session: Session):
    """Test the complete password reset and login flow end-to-end.

    This is the CRITICAL test that simulates exactly what production users do.
    """
    # Create test user with old password
    old_password = "OldPassword999!"
    old_password_hash = bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode()

    user = Angler(
        name="Production Test User",
        email="prodtest@example.com",
        password_hash=old_password_hash,
        member=True,
        is_admin=False,
        created_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    print(f"\n1. Created user with email: {user.email}")

    # Step 1: User requests password reset
    # (In production, this sends email. In test, we just verify endpoint works)
    reset_request = client.post(
        "/forgot-password",
        data={"email": "prodtest@example.com"},
        follow_redirects=False,
    )
    assert reset_request.status_code in [
        302,
        303,
    ], f"Password reset request failed: {reset_request.status_code}"
    print("2. Password reset requested successfully")

    # Step 2: Generate token (simulates clicking email link)
    assert user.email is not None
    token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]
    assert token is not None, "Failed to create password reset token"
    print(f"3. Generated reset token: {token[:20]}...")

    # Step 3: User visits reset password form
    get_form = client.get(f"/reset-password?token={token}")
    assert get_form.status_code == 200, f"Failed to load reset form: {get_form.status_code}"
    assert "Reset Your Password" in get_form.text, "Reset form didn't render"
    print("4. Reset password form loaded successfully")

    # Step 4: User submits new password
    new_password = "NewSecurePassword999!"
    reset_response = client.post(
        "/reset-password",
        data={
            "token": str(token),
            "password": new_password,
            "password_confirm": new_password,
        },
        follow_redirects=False,
    )

    print(f"5. Password reset POST response: {reset_response.status_code}")
    print(f"   Location: {reset_response.headers.get('location', 'None')}")

    assert reset_response.status_code in [302, 303], (
        f"Password reset failed with status {reset_response.status_code}. "
        f"Location: {reset_response.headers.get('location')}"
    )

    assert "/login" in reset_response.headers.get("location", ""), (
        f"Password reset didn't redirect to login. Location: {reset_response.headers.get('location')}"
    )

    print("6. Password reset completed, redirected to login")

    # Step 5: Verify password was actually changed in database
    db_session.refresh(user)
    assert user.password_hash is not None
    password_changed = bcrypt.checkpw(new_password.encode(), user.password_hash.encode())
    assert password_changed, "Password was NOT changed in database! This is the bug!"
    print("7. ✅ Password verified changed in database")

    # Step 6: Verify old password no longer works
    old_password_still_works = bcrypt.checkpw(old_password.encode(), user.password_hash.encode())
    assert not old_password_still_works, (
        "Old password still works! Password wasn't actually changed!"
    )
    print("8. ✅ Old password no longer works")

    # Step 7: User attempts to login with NEW password
    login_response = client.post(
        "/login",
        data={
            "email": "prodtest@example.com",
            "password": new_password,
        },
        follow_redirects=False,
    )

    print(f"9. Login POST response: {login_response.status_code}")
    print(f"   Location: {login_response.headers.get('location', 'None')}")
    print(f"   Cookies: {login_response.cookies}")

    # Login should redirect to home page
    assert login_response.status_code in [302, 303], (
        f"Login failed with status {login_response.status_code}. "
        f"This means users CANNOT login after password reset!"
    )

    # Should redirect to home page, not back to login
    location = login_response.headers.get("location", "")
    assert location == "/" or "login" not in location.lower(), (
        f"Login failed - redirected back to login page. Location: {location}"
    )

    # Should have session cookie
    assert "sabc_session" in login_response.cookies, "No session cookie set - login failed!"

    print("10. ✅✅✅ LOGIN SUCCESSFUL! User can login with new password!")
    print("\n" + "=" * 70)
    print("END-TO-END TEST PASSED: Password reset and login flow works!")
    print("=" * 70 + "\n")
