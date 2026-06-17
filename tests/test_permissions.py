import pytest
from django.contrib.auth.models import AnonymousUser

from apps.sources.permissions import visible_source_ids, visible_sources

pytestmark = pytest.mark.django_db


def test_anonymous_sees_nothing(eis_source):
    assert visible_source_ids(AnonymousUser()) == set()


def test_superuser_sees_all_enabled(admin_user, eis_source, commercial_source):
    assert visible_source_ids(admin_user) == {eis_source.id, commercial_source.id}


def test_superuser_excludes_disabled(admin_user, eis_source, commercial_source):
    commercial_source.is_enabled = False
    commercial_source.save()
    assert visible_source_ids(admin_user) == {eis_source.id}


def test_demo_user_sees_only_granted(demo_user, eis_source, commercial_source):
    # demo_user was granted EIS only.
    assert visible_source_ids(demo_user) == {eis_source.id}
    assert list(visible_sources(demo_user)) == [eis_source]


def test_grant_commercial_source(demo_user, eis_source, commercial_source):
    from apps.sources.models import UserSourcePermission

    UserSourcePermission.objects.create(
        user=demo_user, source=commercial_source, can_view=True
    )
    assert visible_source_ids(demo_user) == {eis_source.id, commercial_source.id}


def test_can_view_false_hides_source(demo_user, eis_source):
    perm = eis_source.user_permissions.get(user=demo_user)
    perm.can_view = False
    perm.save()
    assert visible_source_ids(demo_user) == set()
