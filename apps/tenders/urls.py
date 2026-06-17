from django.urls import path

from . import views

app_name = "tenders"

urlpatterns = [
    path("", views.tender_list, name="list"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("scan/", views.scan_now, name="scan_now"),
    path("<int:pk>/", views.tender_detail, name="detail"),
]
