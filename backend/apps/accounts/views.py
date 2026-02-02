from django.shortcuts import render, redirect
from django.views import generic, View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from rest_framework_simplejwt.tokens import RefreshToken
from .forms import SignUpForm

# Helper to get tokens
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class SignUpView(generic.CreateView):
    form_class = SignUpForm
    success_url = '/accounts/login/?next=/' # Redirect to login
    template_name = 'accounts/signup.html'

class JWTLoginView(View):
    template_name = 'accounts/login.html'
    
    def get(self, request):
        form = AuthenticationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Standard Django login (for session-based messages/compatibility if needed)
            login(request, user)
            
            # Generate JWT Tokens
            tokens = get_tokens_for_user(user)
            
            response = redirect('/')
            
            # Set cookies
            response.set_cookie('access_token', tokens['access'], httponly=True, samesite='Lax')
            response.set_cookie('refresh_token', tokens['refresh'], httponly=True, samesite='Lax')
            
            return response
        return render(request, self.template_name, {'form': form})

class JWTLogoutView(View):
    def post(self, request):
        logout(request)
        response = redirect('/')
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

    def get(self, request):
        # Optional: Redirect to home or show a confirmation page if accessed via GET
        # For simplicity in this hybrid app, we can just treat it same as post or redirect
        # But to be strict/secure, we stick to POST, maybe redirecting GET to home.
        return redirect('/')
