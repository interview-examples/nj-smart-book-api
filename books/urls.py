from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, EnrichmentViewSet, StatsView

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"books", BookViewSet, basename="books")
router.register(r"enrichment", EnrichmentViewSet, basename="enrichment")

# The API URLs are determined automatically by the router
urlpatterns = [
    # API endpoints
    path("", include(router.urls)),
    path("stats/", StatsView.as_view({"get": "get"}), name="book-stats"),
]
