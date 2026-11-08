from django.shortcuts import redirect
from django.urls import reverse
from django.db import connection
from django.utils.cache import add_never_cache_headers

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info  # Clean URL path bina parameters ke

        # Static aur Media files ko allow karein
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        try:
            login_url = reverse('login')
            logout_url = reverse('logout')
        except Exception:
            login_url = '/login/'
            logout_url = '/logout/'

        allowed_exact = {login_url, logout_url, login_url.rstrip('/'), logout_url.rstrip('/')}

        # Agar user login nahi hai aur public route par nahi hai
        if not request.user.is_authenticated:
            if path not in allowed_exact:
                return redirect('login')

        response = self.get_response(request)

        # ✅ SABSE ZAROORI LINE: Browser caching ko mukammal block karega
        # Is se Back button dabane par purana dashboard memory se nahi dikhega
        add_never_cache_headers(response)

        return response

class AuditUserMiddleware:
    """
    Har request par logged-in user ki info SQL Server ki
    Audit_User_Session table mein save karta hai
    (SQL Server 2012 compatible — SESSION_CONTEXT ke bina).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated:
            uid   = user.pk
            uname = (user.get_full_name() or user.get_username())[:120]
            role  = getattr(user, 'role', None) or (
                'Admin' if user.is_superuser else 'Staff'
            )
        else:
            uid, uname, role = None, None, None

        ip = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
              or request.META.get('REMOTE_ADDR', ''))[:45]

        try:
            with connection.cursor() as cur:
                cur.execute("""
                    EXEC dbo.usp_SetAuditUser
                        @user_id   = %s,
                        @user_name = %s,
                        @user_role = %s,
                        @ip        = %s;
                """, [uid, uname, role, ip])
        except Exception as e:
            # audit fail ho to app na rukay — bas print kar dein
            print(f"[AuditUserMiddleware] {e}")

        return self.get_response(request)    