from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, UserProfileView

urlpatterns = [

    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    path('registro/', RegisterView.as_view(), name='register'),
    path('perfil/', UserProfileView.as_view(), name='user_profile'),
]
