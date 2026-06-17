from django.urls import path

from . import views

app_name = "tenders"

urlpatterns = [
    path("", views.tender_list, name="list"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("<int:pk>/", views.tender_detail, name="detail"),
]
