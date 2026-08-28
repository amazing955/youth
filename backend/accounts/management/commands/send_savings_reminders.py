from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone

from accounts.models import Member, Notification
from accounts.notification_utils import notify_member


class Command(BaseCommand):
    help = 'Send savings reminders to members who have not saved for seven days.'

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(days=7)
        members = Member.objects.filter(is_active=True).annotate(last_saving=Max('savings__created_at')).filter(
            Q(last_saving__isnull=True) | Q(last_saving__lte=cutoff)
        )
        sent = 0
        for member in members:
            already_reminded = Notification.objects.filter(
                member=member,
                kind='Savings reminder',
                created_at__gte=cutoff,
            ).exists()
            if already_reminded:
                continue
            notify_member(
                member,
                'Keep your savings goal moving',
                'You have not made a saving in the last seven days. A small contribution today can help you move closer to your financial goal.',
                'Savings reminder',
            )
            sent += 1
        self.stdout.write(self.style.SUCCESS(f'Sent {sent} savings reminder(s).'))
