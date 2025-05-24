from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ParticipacionViewSet

router = DefaultRouter()
router.register(r'', ParticipacionViewSet, basename='participacion')

urlpatterns = [
    path('', include(router.urls)),
]
