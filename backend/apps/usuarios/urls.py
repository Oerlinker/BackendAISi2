from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, UserProfileView, CustomTokenObtainPairView, AdminUserDeleteView, UserListView, EstudiantesListView, AdminUserUpdateView

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('registro/', RegisterView.as_view(), name='register'),
    path('perfil/', UserProfileView.as_view(), name='user_profile'),
    path('lista/', UserListView.as_view(), name='user_list'),
    path('estudiantes/', EstudiantesListView.as_view(), name='estudiantes_list'),
    path('actualizar/<int:user_id>/', AdminUserUpdateView.as_view(), name='admin_user_update'),
    path('<int:user_id>/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
]
