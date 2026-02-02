import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.deprecation import MiddlewareMixin

User = get_user_model()

class JWTCookieMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # We generally expect AuthenticationMiddleware to have run, but since we removed 
        # session login, request.user should be AnonymousUser initially.
        # We proceed to check for JWT.

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
                
                # Stateless User Construction (Optimized - No DB Query)
                user = User(
                    id=payload.get('user_id'),
                    username=payload.get('username', ''),
                    email=payload.get('email', '')
                )
                user.is_active = True
                # user.is_authenticated returns True by default
                # user.is_staff = payload.get('is_staff', False) # If we added this claim
                
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
                        
                        # Decode new token to get user properties
                        # Note: We need to ensure refresh.access_token has the same claims! 
                        # SimpleJWT copies claims from refresh to access usually, 
                        # but custom claims added to refresh above should persist.
                        payload = jwt.decode(new_access_token, settings.SECRET_KEY, algorithms=['HS256'])
                        
                        user = User(
                            id=payload.get('user_id'),
                            username=payload.get('username', ''),
                            email=payload.get('email', '')
                        )
                        user.is_active = True
                        # user.is_authenticated returns True by default
                        
                        request.user = user
                        return
                    except Exception as e:
                        # print(f"Refresh failed: {e}")
                        pass
            except Exception as e:
                # print(f"Token error: {e}")
                pass

        # If no valid token was found/processed:
        # Optimization: For non-admin paths, forcefully set AnonymousUser to avoid 
        # AuthenticationMiddleware's lazy DB lookup from checking session.
        if not request.path.startswith('/admin/'):
             request.user = AnonymousUser()
        
        # For admin paths, we leave request.user alone (it might be a lazy session user)

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
