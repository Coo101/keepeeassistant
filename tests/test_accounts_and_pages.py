"""Accounts, invitations and the public pages (docs/spec/accounts.md)."""

import datetime
import re

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import Chiro, Invitation, Membership, RateLimitHit
from accounts.ratelimit import (
    MAX_FAILS_PER_ACCOUNT,
    MAX_FAILS_PER_ADDRESS,
    MAX_RESETS_PER_ADDRESS,
    MAX_RESETS_PER_EMAIL,
    client_address,
)
from pages.models import Post
from pages.views import DOCS
from tests.factories import account_client, make_camp, member_client

pytestmark = pytest.mark.django_db

PASSWORD = "soep-en-brood-42"


@pytest.fixture
def chiro() -> Chiro:
    return Chiro.objects.create(name="Chiro Testdorp")


@pytest.fixture
def invitation(chiro: Chiro) -> Invitation:
    return Invitation.objects.create(chiro=chiro, email="jan@example.com")


def _url(invitation: Invitation) -> str:
    return reverse("invitation_accept", args=[invitation.token])


def _signup_data() -> dict:
    return {"username": "jan", "password1": PASSWORD, "password2": PASSWORD}


def test_home_news_and_docs_are_public() -> None:
    client = Client()
    assert client.get(reverse("home")).status_code == 200
    assert client.get(reverse("post_list")).status_code == 200
    for slug in DOCS:
        response = client.get(reverse("doc", args=[slug]))
        assert response.status_code == 200
        assert "<h1>" in response.content.decode()


def test_unknown_doc_is_not_found() -> None:
    assert Client().get(reverse("doc", args=["nope"])).status_code == 404


def test_only_published_posts_show() -> None:
    Post.objects.create(title="Klaar", slug="klaar", body="**vet**")
    Post.objects.create(title="Concept", slug="concept", body="x", is_published=False)
    Post.objects.create(
        title="Later",
        slug="later",
        body="x",
        published_at=timezone.now() + datetime.timedelta(days=1),
    )
    client = Client()
    home = client.get(reverse("home")).content.decode()
    assert "Klaar" in home and "Concept" not in home and "Later" not in home
    detail = client.get(reverse("post_detail", args=["klaar"])).content.decode()
    assert "<strong>vet</strong>" in detail
    assert client.get(reverse("post_detail", args=["concept"])).status_code == 404


def test_app_links_only_show_when_logged_in() -> None:
    anonymous = Client().get(reverse("home")).content.decode()
    assert reverse("recipe_list") not in anonymous
    logged_in = account_client().get(reverse("home")).content.decode()
    assert reverse("recipe_list") in logged_in


def test_camps_moved_off_the_home_page() -> None:
    assert reverse("camp_list") == "/camps/"
    response = Client().get(reverse("camp_list"))
    assert response.status_code == 302


def test_login_with_email_or_username() -> None:
    User.objects.create_user("kok", email="Kok@Example.com", password=PASSWORD)
    assert Client().login(username="kok", password=PASSWORD)
    assert Client().login(username="kok@example.com", password=PASSWORD)
    assert not Client().login(username="kok@example.com", password="fout")
    assert not Client().login(username="nobody@example.com", password=PASSWORD)


def test_shared_email_address_does_not_log_in() -> None:
    User.objects.create_user("a", email="same@example.com", password=PASSWORD)
    User.objects.create_user("b", email="same@example.com", password=PASSWORD)
    assert not Client().login(username="same@example.com", password=PASSWORD)


def test_inactive_user_cannot_log_in_by_email() -> None:
    User.objects.create_user(
        "kok", email="kok@example.com", password=PASSWORD, is_active=False
    )
    assert not Client().login(username="kok@example.com", password=PASSWORD)


def test_password_reset_flow() -> None:
    user = User.objects.create_user("kok", email="kok@example.com", password=PASSWORD)
    client = Client()
    assert client.get(reverse("password_reset")).status_code == 200
    response = client.post(reverse("password_reset"), {"email": "kok@example.com"})
    assert response.status_code == 302
    link = re.search(r"https?://\S+", mail.outbox[0].body).group()
    path = link.split("testserver", 1)[1]

    form_page = client.get(path, follow=True)
    assert form_page.status_code == 200
    new = "nieuw-wachtwoord-77"
    done = client.post(
        form_page.redirect_chain[-1][0],
        {"new_password1": new, "new_password2": new},
    )
    assert done.status_code == 302
    user.refresh_from_db()
    assert user.check_password(new)


def test_password_change_needs_a_login() -> None:
    assert Client().get(reverse("password_change")).status_code == 302
    assert account_client().get(reverse("password_change")).status_code == 200


def test_account_page_shows_chiros_and_saves_details() -> None:
    camp = make_camp()
    client = member_client(camp)
    url = reverse("account")
    assert camp.chiro.name in client.get(url).content.decode()

    user = User.objects.get(username="kok")
    user.set_password(PASSWORD)
    user.save()
    client.force_login(user)

    response = client.post(
        url,
        {
            "first_name": "Jan",
            "email": "jan@example.com",
            "current_password": PASSWORD,
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert (user.first_name, user.email) == ("Jan", "jan@example.com")


def test_changing_the_email_needs_the_password() -> None:
    client = account_client()
    user = User.objects.get(username="kok")
    user.set_password(PASSWORD)
    user.save()
    client.force_login(user)
    url = reverse("account")

    response = client.post(url, {"email": "jan@example.com", "current_password": "x"})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == ""
    # other details don't need it
    assert client.post(url, {"first_name": "Jan"}).status_code == 302


def test_invited_address_cannot_be_claimed(invitation) -> None:
    client = account_client()
    user = User.objects.get(username="kok")
    user.set_password(PASSWORD)
    user.save()
    client.force_login(user)
    response = client.post(
        reverse("account"),
        {"email": "jan@example.com", "current_password": PASSWORD},
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == ""


def test_account_email_must_be_free() -> None:
    User.objects.create_user("ander", email="jan@example.com")
    response = account_client().post(reverse("account"), {"email": "JAN@example.com"})
    assert response.status_code == 200
    assert "Another account" in response.content.decode()


def test_account_needs_a_login() -> None:
    assert Client().get(reverse("account")).status_code == 302


def test_invitation_creates_account_joins_chiro_and_logs_in(invitation, chiro) -> None:
    client = Client()
    url = _url(invitation)
    assert chiro.name in client.get(url).content.decode()

    response = client.post(url, _signup_data())

    assert response["Location"] == reverse("camp_list")
    user = User.objects.get(username="jan")
    assert user.email == "jan@example.com"
    assert not user.is_staff
    assert Membership.objects.filter(user=user, chiro=chiro).exists()
    assert client.get(reverse("camp_list")).status_code == 200
    invitation.refresh_from_db()
    assert invitation.accepted_at is not None


def test_invitation_works_only_once(invitation) -> None:
    Client().post(_url(invitation), _signup_data())
    response = Client().post(
        _url(invitation),
        {"username": "piet", "password1": PASSWORD, "password2": PASSWORD},
    )
    assert response.status_code == 410
    assert not User.objects.filter(username="piet").exists()


def test_expired_invitation_is_refused(invitation) -> None:
    Invitation.objects.filter(pk=invitation.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=15)
    )
    assert Client().get(_url(invitation)).status_code == 410


def test_unknown_token_is_not_found() -> None:
    url = reverse("invitation_accept", args=["verzonnen"])
    assert Client().get(url).status_code == 404


def test_logged_in_user_joins_with_a_button(invitation, chiro) -> None:
    client = account_client()
    User.objects.filter(username="kok").update(email="JAN@example.com")
    assert client.get(_url(invitation)).status_code == 200
    assert not Membership.objects.exists()  # opening the link changes nothing

    assert client.post(_url(invitation)).status_code == 302

    assert Membership.objects.get().chiro == chiro


def test_existing_address_must_log_in_first(invitation) -> None:
    User.objects.create_user("jan", email="JAN@example.com", password=PASSWORD)
    client = Client()
    assert "Log in" in client.get(_url(invitation)).content.decode()
    response = client.post(
        _url(invitation),
        {"username": "dubbel", "password1": PASSWORD, "password2": PASSWORD},
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="dubbel").exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


def test_saving_an_invitation_in_the_admin_mails_the_link(chiro) -> None:
    client = Client()
    client.force_login(User.objects.create_superuser("baas"))
    response = client.post(
        "/admin/accounts/invitation/add/",
        {"chiro": chiro.pk, "email": "jan@example.com", "role": "member"},
    )
    assert response.status_code == 302
    invitation = Invitation.objects.get()
    assert invitation.invited_by.username == "baas"
    assert invitation.token in mail.outbox[0].body
    assert mail.outbox[0].to == ["jan@example.com"]
    page = client.get(f"/admin/accounts/invitation/{invitation.pk}/change/")
    assert invitation.token in page.content.decode()


def test_another_account_cannot_use_the_invitation(invitation) -> None:
    client = account_client("piet")
    assert client.get(_url(invitation)).status_code == 403
    assert client.post(_url(invitation)).status_code == 403
    assert not Membership.objects.exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


def test_send_again_skips_used_invitations(invitation) -> None:
    Invitation.objects.filter(pk=invitation.pk).update(accepted_at=timezone.now())
    client = Client()
    client.force_login(User.objects.create_superuser("baas"))
    response = client.post(
        "/admin/accounts/invitation/",
        {"action": "send_again", "_selected_action": [invitation.pk]},
    )
    assert response.status_code == 302
    assert mail.outbox == []


def _try_login(client: Client, username: str, password: str):
    return client.post(reverse("login"), {"username": username, "password": password})


def test_login_locks_after_too_many_failures() -> None:
    User.objects.create_user("kok", password=PASSWORD)
    client = Client()
    for _ in range(MAX_FAILS_PER_ACCOUNT):
        assert _try_login(client, "kok", "fout").status_code == 200

    # even the right password now has to wait, without saying which it was
    response = _try_login(client, "KOK", PASSWORD)
    assert response.status_code == 200
    assert "Too many failed attempts" in response.content.decode()
    assert RateLimitHit.objects.exclude(key__regex="^[0-9a-f]{64}$").count() == 0


def test_other_accounts_stay_open_and_success_resets_the_count() -> None:
    User.objects.create_user("kok", password=PASSWORD)
    User.objects.create_user("ander", password=PASSWORD)
    client = Client()
    for _ in range(MAX_FAILS_PER_ACCOUNT - 1):
        _try_login(client, "kok", "fout")
    assert _try_login(Client(), "ander", PASSWORD).status_code == 302
    assert _try_login(Client(), "kok", PASSWORD).status_code == 302
    assert _try_login(Client(), "kok", "fout").status_code == 200
    assert _try_login(Client(), "kok", PASSWORD).status_code == 302


def test_old_failures_no_longer_count() -> None:
    User.objects.create_user("kok", password=PASSWORD)
    for _ in range(MAX_FAILS_PER_ACCOUNT):
        _try_login(Client(), "kok", "fout")
    RateLimitHit.objects.update(at=timezone.now() - datetime.timedelta(hours=1))
    assert _try_login(Client(), "kok", PASSWORD).status_code == 302


def test_admin_login_is_limited_too() -> None:
    User.objects.create_superuser("baas", password=PASSWORD)
    for _ in range(MAX_FAILS_PER_ACCOUNT):
        Client().post("/admin/login/", {"username": "baas", "password": "fout"})
    response = Client().post(
        "/admin/login/", {"username": "baas", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert "Too many failed attempts" in response.content.decode()


def test_addresses_are_limited_behind_a_configured_header(settings) -> None:
    settings.CLIENT_IP_HEADER = "HTTP_CF_CONNECTING_IP"
    for number in range(MAX_FAILS_PER_ADDRESS):
        Client(HTTP_CF_CONNECTING_IP="1.2.3.4").post(
            reverse("login"), {"username": f"gok{number}", "password": "x"}
        )
    User.objects.create_user("kok", password=PASSWORD)
    blocked = Client(HTTP_CF_CONNECTING_IP="1.2.3.4").post(
        reverse("login"), {"username": "kok", "password": PASSWORD}
    )
    assert blocked.status_code == 200
    allowed = Client(HTTP_CF_CONNECTING_IP="5.6.7.8").post(
        reverse("login"), {"username": "kok", "password": PASSWORD}
    )
    assert allowed.status_code == 302


def test_reset_mails_are_limited_without_saying_so() -> None:
    User.objects.create_user("kok", email="kok@example.com", password=PASSWORD)
    for _ in range(MAX_RESETS_PER_EMAIL + 2):
        response = Client().post(
            reverse("password_reset"), {"email": "kok@example.com"}
        )
        assert response.status_code == 302
    assert len(mail.outbox) == MAX_RESETS_PER_EMAIL


def test_blank_password_does_not_reset_the_count() -> None:
    User.objects.create_user("kok", password=PASSWORD)
    for _ in range(MAX_FAILS_PER_ACCOUNT - 1):
        _try_login(Client(), "kok", "fout")
    _try_login(Client(), "kok", "")
    _try_login(Client(), "kok", "fout")
    response = _try_login(Client(), "kok", PASSWORD)
    assert "Too many failed attempts" in response.content.decode()


def test_all_spellings_of_an_account_share_one_count() -> None:
    User.objects.create_user("kok", email="kok@example.com", password=PASSWORD)
    spellings = ["kok", "KOK", "ｋok", "kok@example.com"]
    for number in range(MAX_FAILS_PER_ACCOUNT):
        _try_login(Client(), spellings[number % len(spellings)], "fout")
    response = _try_login(Client(), "kok@example.com", PASSWORD)
    assert "Too many failed attempts" in response.content.decode()


def test_password_reset_lifts_the_lock() -> None:
    User.objects.create_user("kok", email="kok@example.com", password=PASSWORD)
    for _ in range(MAX_FAILS_PER_ACCOUNT):
        _try_login(Client(), "kok", "fout")
    client = Client()
    client.post(reverse("password_reset"), {"email": "kok@example.com"})
    link = re.search(r"https?://\S+", mail.outbox[0].body).group()
    form_page = client.get(link.split("testserver", 1)[1], follow=True)
    new = "nieuw-wachtwoord-77"
    client.post(
        form_page.redirect_chain[-1][0],
        {"new_password1": new, "new_password2": new},
    )
    assert _try_login(Client(), "kok", new).status_code == 302


def test_reset_mails_are_limited_per_address() -> None:
    for number in range(MAX_RESETS_PER_ADDRESS + 2):
        User.objects.create_user(f"k{number}", email=f"k{number}@example.com")
        Client().post(reverse("password_reset"), {"email": f"k{number}@example.com"})
    assert RateLimitHit.objects.count() == 2 * MAX_RESETS_PER_ADDRESS


def test_only_the_address_added_by_the_nearest_proxy_counts(settings) -> None:
    settings.CLIENT_IP_HEADER = "HTTP_X_FORWARDED_FOR"
    factory = RequestFactory()
    request = factory.get("/", HTTP_X_FORWARDED_FOR="9.9.9.9, 1.2.3.4")
    assert client_address(request) == "1.2.3.4"
