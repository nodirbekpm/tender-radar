from rest_framework.routers import DefaultRouter

from .api import TenderViewSet

router = DefaultRouter()
router.register("tenders", TenderViewSet, basename="api-tender")

urlpatterns = router.urls
