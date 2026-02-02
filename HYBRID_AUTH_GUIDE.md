# Hybrid Stateless JWT Authentication Guide

This project implements a **Hybrid JWT Authentication** system. It combines the security and statelessness of JWTs with the convenience of Browser Cookies for the UI, while supporting standard Bearer Tokens for API clients.

## Architecture

1.  **Dual Token Retrieval**:
    *   **API Clients**: Send `Authorization: Bearer <token>` header.
    *   **Browser UI**: Tokens are stored in **HttpOnly, Secure, SameSite=Lax** cookies (`access_token`, `refresh_token`). The Middleware automatically extracts them.

2.  **Stateless User (Database Optimization)**:
    *   The `User` object is reconstructed directly from the JWT payload (`user_id`, `username`, `email`) in the middleware.
    *   **Optimization**: This avoids a database query (`SELECT * FROM auth_user`) on every request.
    *   **Session Bypass**: For non-admin paths, we explicitly bypass Django's default Session-based `AuthenticationMiddleware` to ensure zero DB queries.

---

## 1. Configuration (`settings.py`)

Ensure `SimpleJWT` is installed and configured, and add the custom middleware.

```python
# backend/settings/base.py

INSTALLED_APPS = [
    # ...
    'rest_framework',
    'rest_framework_simplejwt',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', # Required for Admin
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Required for Admin
    'accounts.middleware.JWTCookieMiddleware',  # <--- OUR CUSTOM MIDDLEWARE
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

---

## 2. Views (`apps/accounts/views.py`)

The Login view generates tokens and sets them as HttpOnly cookies. Crucially, it **does not** create a Django Session (`login(request, user)` removed).

```python
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

# 1. Custom Token Generator with Claims
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    
    # Add custom claims (Required for Stateless Middleware)
    refresh['username'] = user.username
    refresh['email'] = user.email
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# 2. Login View
class JWTLoginView(View):
    template_name = 'accounts/login.html'
    
    def get(self, request):
        form = AuthenticationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # NOTE: We DO NOT call login(request, user) here.
            # This prevents Django from creating a server-side Session.
            
            # Generate JWT Tokens
            tokens = get_tokens_for_user(user)
            
            response = redirect('/')
            
            # Set HttpOnly Cookies
            response.set_cookie('access_token', tokens['access'], httponly=True, samesite='Lax')
            response.set_cookie('refresh_token', tokens['refresh'], httponly=True, samesite='Lax')
            
            return response
        return render(request, self.template_name, {'form': form})

# 3. Logout View
class JWTLogoutView(View):
    def post(self, request):
        logout(request) # Clears any accidental session
        response = redirect('/')
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response
```

---

## 3. Middleware (`apps/accounts/middleware.py`)

This is the core logic. It intercepts requests, finds the token, and creates a stateless user.

```python
import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class JWTCookieMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_token = None
        refresh_token = request.COOKIES.get('refresh_token')

        # 1. Check Authorization Header (Prioritized for API)
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        
        # 2. Fallback to Cookie (For Web UI)
        if not access_token:
            access_token = request.COOKIES.get('access_token')

        if access_token:
            try:
                # Decode access token (No DB Verify, just Signature verify)
                payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
                
                # OPTIMIZATION: Stateless User Construction
                # We instantiate the User model but do NOT save it or fetch from DB.
                user = User(
                    id=payload.get('user_id'),
                    username=payload.get('username', ''),
                    email=payload.get('email', '')
                )
                user.is_active = True
                user.is_authenticated = True 
                
                request.user = user
                return # User successfully set, exit middleware
                
            except jwt.ExpiredSignatureError:
                # OPTIONAL: Handle Token Refresh logic here (omitted for brevity)
                pass
            except Exception as e:
                pass

        # 3. Fallback & Optimization (CRITICAL)
        # If no valid token found, we must prevent Django's default AuthenticationMiddleware
        # from checking the Session (which triggers a DB query).
        
        # We only allow Session auth for the Admin panel.
        if not request.path.startswith('/admin/'):
             request.user = AnonymousUser()
        
        # If path starts with /admin/, we do nothing, letting default middleware handle sessions.
```
