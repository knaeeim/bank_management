from django.urls import path
from .views import *

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', user_logout, name='logout'),
    path('profile_update/', UserUpdateView.as_view(), name='profile_update'),
    path('change_password/', ChangePassword.as_view(), name='change_password'),
]