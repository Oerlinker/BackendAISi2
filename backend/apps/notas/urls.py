from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PeriodoViewSet, NotaViewSet

router = DefaultRouter()
router.register(r'periodos', PeriodoViewSet)
router.register(r'calificaciones', NotaViewSet, basename='nota')

urlpatterns = [
    path('', include(router.urls)),
]
