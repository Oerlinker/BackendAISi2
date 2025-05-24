from django.urls import path
from .views import DashboardGeneralView, DashboardEstudianteView, ComparativoRendimientoView

urlpatterns = [
    path('general/', DashboardGeneralView.as_view(), name='dashboard_general'),
    path('estadisticas/', DashboardGeneralView.as_view(), name='dashboard_estadisticas'),
    path('estudiante/<int:estudiante_id>/', DashboardEstudianteView.as_view(), name='dashboard_estudiante'),
    path('estudiante/', DashboardEstudianteView.as_view(), name='dashboard_estudiante_propio'),
    path('comparativo/', ComparativoRendimientoView.as_view(), name='comparativo_rendimiento'),
]
