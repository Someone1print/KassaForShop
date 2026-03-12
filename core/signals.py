from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from .models import UserLoginLog

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserLoginLog.objects.create(
        username=user.username,
        ip_address=get_client_ip(request),
        is_success=True,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    UserLoginLog.objects.create(
        username=credentials.get('username', 'unknown'),
        ip_address=get_client_ip(request) if request else None,
        is_success=False,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
    )
