import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class JWTCookieMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # If already authenticated by Session (e.g. admin), skip
        if request.user.is_authenticated:
            return

        access_token = None
        refresh_token = request.COOKIES.get('refresh_token')

        # 1. Check Authorization Header (API/Mobile)
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
        
        # 2. Fallback to Cookie (Web UI)
        if not access_token:
            access_token = request.COOKIES.get('access_token')

        if access_token:
            try:
                # Decode access token
                payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
                user_id = payload.get('user_id')
                user = User.objects.get(id=user_id)
                request.user = user
                return
            except jwt.ExpiredSignatureError:
                # Access token expired, try refresh
                if refresh_token:
                    try:
                        refresh = RefreshToken(refresh_token)
                        new_access_token = str(refresh.access_token)
                        
                        # Attach new token to request for View to set cookie
                        request.new_access_token = new_access_token
                        
                        # Decode new token to get user
                        payload = jwt.decode(new_access_token, settings.SECRET_KEY, algorithms=['HS256'])
                        user_id = payload.get('user_id')
                        user = User.objects.get(id=user_id)
                        request.user = user
                        return
                    except Exception as e:
                        print(f"Refresh failed: {e}")
            except Exception as e:
                print(f"Token error: {e}")

        # Fallback to AnonymousUser
        request.user = AnonymousUser()

    def process_response(self, request, response):
        # If a new access token was generated during request processing, set it
        if hasattr(request, 'new_access_token'):
            response.set_cookie(
                'access_token',
                request.new_access_token,
                httponly=True,
                samesite='Lax'
            )
        return response
