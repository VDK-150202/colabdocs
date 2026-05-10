from django.urls import path
from .views import LoginView, LogoutView, RegisterView, UserProfileView

urlpatterns = [
    path("", RegisterView.as_view(), name="auth-register"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("profile/", UserProfileView.as_view(), name="auth-profile"),
]
