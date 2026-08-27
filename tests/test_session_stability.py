from __future__ import annotations


def test_login_always_requests_remember_cookie(client, app):
    from app.extensions import db
    from app.models import Role, User

    with app.app_context():
        user = User(
            email="field@example.org",
            mobile="+919999999999",
            role=Role.ADMIN,
            display_name="Field User",
        )
        user.set_password("StrongPass123!")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={
            "identifier": "field@example.org",
            "password": "StrongPass123!",
        },
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}

    cookies = response.headers.getlist("Set-Cookie")

    remember_cookies = [
        cookie
        for cookie in cookies
        if cookie.startswith("remember_token=")
    ]

    # A successful persistent login must create Flask-Login's
    # long-lived remember cookie.
    assert remember_cookies, cookies

    remember_cookie = remember_cookies[0]

    # Flask-Login uses an expiry timestamp for the persistent
    # remember cookie. Max-Age is not guaranteed to be present.
    assert "Expires=" in remember_cookie

    # The authentication cookie must not be accessible to
    # application JavaScript.
    assert "HttpOnly" in remember_cookie

    # The application config should explicitly define the
    # cross-site cookie policy.
    assert "SameSite=" in remember_cookie


def test_remember_cookie_configuration(app):
    """Persistent-login configuration should remain enabled."""

    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] is True

    duration = app.config["REMEMBER_COOKIE_DURATION"]

    # The configured duration must be positive.
    assert duration.total_seconds() > 0


def test_logout_clears_authenticated_session(client, app):
    """Explicit logout must still terminate a remembered login."""
    from app.extensions import db
    from app.models import Role, User

    with app.app_context():
        user = User(
            email="logout-test@example.org",
            mobile="+919999999998",
            role=Role.ADMIN,
            display_name="Logout Test User",
        )
        user.set_password("StrongPass123!")
        db.session.add(user)
        db.session.commit()

    login_response = client.post(
        "/login",
        data={
            "identifier": "logout-test@example.org",
            "password": "StrongPass123!",
        },
        follow_redirects=False,
    )

    assert login_response.status_code in {302, 303}

    login_cookies = login_response.headers.getlist("Set-Cookie")

    assert any(
        cookie.startswith("remember_token=")
        for cookie in login_cookies
    )

    logout_response = client.post(
        "/logout",
        follow_redirects=False,
    )

    assert logout_response.status_code in {302, 303}

    logout_cookies = logout_response.headers.getlist("Set-Cookie")

    # Flask-Login should expire/remove the remember cookie
    # when the user explicitly signs out.
    cleared_remember_cookie = [
        cookie
        for cookie in logout_cookies
        if cookie.startswith("remember_token=")
    ]

    assert cleared_remember_cookie

    cleared_cookie = cleared_remember_cookie[0]

    assert (
        "Expires=Thu, 01 Jan 1970" in cleared_cookie
        or "Max-Age=0" in cleared_cookie
        or "remember_token=;" in cleared_cookie
    )
