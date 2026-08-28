from django.conf import settings
from django.core.mail import send_mail

from .models import Member, Notification


def notify_member(member, title, message, kind='General'):
    Notification.objects.create(member=member, title=title, message=message, kind=kind)
    recipient = member.email or getattr(member.user, 'email', '')
    if recipient:
        send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)


def notify_members(title, message, kind='General'):
    for member in Member.objects.select_related('user').all():
        notify_member(member, title, message, kind)