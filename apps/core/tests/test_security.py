import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_security_headers(client):
    response = client.get(reverse("account_login"))
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "'unsafe-eval'" not in csp
    assert "script-src 'self' 'nonce-" in csp
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.django_db
def test_import_map_carries_the_csp_nonce(client):
    response = client.get(reverse("account_login"))
    nonce = response.headers["Content-Security-Policy"].split("'nonce-")[1].split("'")[0]
    assert f'<script type="importmap" nonce="{nonce}">' in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("cookie", ['"><script>alert(1)</script>', "neon", ""])
def test_theme_cookie_only_accepts_known_themes(client, cookie):
    client.cookies["theme"] = cookie
    html = client.get(reverse("account_login")).content.decode()
    assert '<html lang="sl" data-theme="dark">' in html
    assert "<script>alert(1)</script>" not in html


@pytest.mark.django_db
def test_logout_requires_post(auth_client):
    response = auth_client.get(reverse("account_logout"))
    # allauth shows a confirmation page on GET instead of signing out.
    assert response.status_code == 200
    assert auth_client.get(reverse("core:dashboard")).status_code == 200
