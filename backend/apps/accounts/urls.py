from django.urls import path, include
from .views import SignUpView, JWTLoginView, JWTLogoutView

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', JWTLoginView.as_view(), name='login'),
    path('logout/', JWTLogoutView.as_view(), name='logout'),
    path('', include('django.contrib.auth.urls')),
]
