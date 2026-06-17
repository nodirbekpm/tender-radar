import pytest
from django.contrib.auth.models import User

from apps.sources.models import Source, UserSourcePermission


@pytest.fixture
def eis_source(db):
    return Source.objects.create(code="eis", name="ЕИС", adapter_key="eis", is_enabled=True)


@pytest.fixture
def commercial_source(db):
    return Source.objects.create(
        code="b2b_center", name="B2B-Center", adapter_key="b2b_center", is_enabled=True
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser("admin", "admin@example.local", "pw")


@pytest.fixture
def demo_user(db, eis_source):
    user = User.objects.create_user("demo", "demo@example.local", "pw")
    UserSourcePermission.objects.create(user=user, source=eis_source, can_view=True)
    return user
