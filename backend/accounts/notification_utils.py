from django.conf import settings
from django.core.mail import send_mail
from django.conf import settings

from .models import Member, Notification, PushDevice


def _send_push(user, title, message):
    service_account = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', '')
    if not service_account or not user:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(credentials.Certificate(service_account))
        devices = list(PushDevice.objects.filter(user=user).values_list('token', flat=True))
        stale_tokens = []
        for token in devices:
            try:
                messaging.send(messaging.Message(notification=messaging.Notification(title=title, body=message), token=token), app=app)
            except Exception as error:
                if 'registration-token-not-registered' in str(error).lower() or 'not a valid fcm registration token' in str(error).lower():
                    stale_tokens.append(token)
        if stale_tokens:
            PushDevice.objects.filter(token__in=stale_tokens).delete()
    except Exception:
        return


def notify_member(member, title, message, kind='General'):
    Notification.objects.create(member=member, title=title, message=message, kind=kind)
    _send_push(getattr(member, 'user', None), title, message)
    recipient = member.email or getattr(member.user, 'email', '')
    if recipient:
        send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)


def notify_members(title, message, kind='General'):
    for member in Member.objects.select_related('user').all():
        notify_member(member, title, message, kind)