import pytest
from django.urls import reverse

from apps.tenders.models import Tender

pytestmark = pytest.mark.django_db


def _make_tender(source, external_id, title):
    return Tender.objects.create(
        source=source, external_id=external_id, title=title, fz_type="44"
    )


def test_list_requires_login(client):
    resp = client.get(reverse("tenders:list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]


def test_demo_user_sees_only_permitted_source(client, demo_user, eis_source, commercial_source):
    _make_tender(eis_source, "E1", "EIS tender")
    _make_tender(commercial_source, "C1", "Commercial tender")

    client.force_login(demo_user)
    resp = client.get(reverse("tenders:list"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "EIS tender" in body
    assert "Commercial tender" not in body


def test_detail_forbidden_for_unpermitted_source(client, demo_user, commercial_source):
    tender = _make_tender(commercial_source, "C1", "Commercial tender")
    client.force_login(demo_user)
    resp = client.get(reverse("tenders:detail", args=[tender.pk]))
    assert resp.status_code == 404


def test_api_scoped_to_visible_sources(client, demo_user, eis_source, commercial_source):
    _make_tender(eis_source, "E1", "EIS tender")
    _make_tender(commercial_source, "C1", "Commercial tender")

    client.force_login(demo_user)
    resp = client.get("/api/tenders/")
    assert resp.status_code == 200
    data = resp.json()
    titles = [t["title"] for t in data["results"]]
    assert "EIS tender" in titles
    assert "Commercial tender" not in titles
