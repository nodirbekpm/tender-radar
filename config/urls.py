from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("tenders/", include("apps.tenders.urls")),
    path("api/", include("apps.tenders.api_urls")),
    path("", RedirectView.as_view(pattern_name="tenders:list", permanent=False)),
]
