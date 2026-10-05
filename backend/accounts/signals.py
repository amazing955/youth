from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import AuditLog, FinancialGoal, Notification, SupportIssue
from loans.models import Loan
from savings.models import Savings
from transactions.models import Transaction
from .realtime import broadcast_update


def publish(payload, member_id=None):
    transaction.on_commit(lambda: broadcast_update(payload, member_id))


@receiver(post_save, sender=Savings)
def savings_saved(sender, instance, created, **kwargs):
    publish({'type': 'balance_updated', 'member_id': str(instance.member_id)}, instance.member.user_id if instance.member_id else None)
    if created and instance.amount > 0:
        transaction.on_commit(lambda: check_goals(instance.member_id))


def check_goals(member_id):
    from django.core.mail import send_mail
    from django.conf import settings
    from django.db.models import Sum
    from .models import Member

    balance = Savings.objects.filter(member_id=member_id).aggregate(total=Sum('amount'))['total'] or 0
    member = Member.objects.select_related('user').get(pk=member_id)
    for goal in FinancialGoal.objects.filter(member_id=member_id, achieved_at__isnull=True):
        if balance >= goal.amount:
            goal.achieved_at = timezone.now()
            goal.save(update_fields=['achieved_at'])
            message = f'Congratulations {member.full_name}! You reached your savings goal "{goal.name}" of UGX {goal.amount:,.2f}.'
            recipient = member.email or getattr(member.user, 'email', '')
            if recipient:
                send_mail('Congratulations on reaching your savings goal!', message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
            Notification.objects.create(member=member, title='Savings goal reached', message=message, kind='Goal')


@receiver(post_save, sender=Transaction)
def transaction_saved(sender, instance, created, **kwargs):
    publish({'type': 'transaction_updated', 'member_id': str(instance.member_id)}, instance.member.user_id if instance.member_id else None)


@receiver(post_save, sender=Notification)
def notification_saved(sender, instance, created, **kwargs):
    if created:
        publish({'type': 'notification_created', 'notification_id': instance.id}, instance.member.user_id if instance.member_id else None)


@receiver(post_save, sender=Loan)
def loan_saved(sender, instance, created, **kwargs):
    publish({'type': 'loan_updated', 'loan_id': instance.id, 'member_id': str(instance.member_id)}, instance.member.user_id if instance.member_id else None)


@receiver(post_save, sender=SupportIssue)
def support_issue_saved(sender, instance, created, **kwargs):
    publish({'type': 'support_issue_updated', 'issue_id': instance.id, 'member_id': str(instance.member_id)}, instance.member.user_id if instance.member_id else None)


@receiver(post_save, sender=AuditLog)
def audit_saved(sender, instance, created, **kwargs):
    if created:
        publish({'type': 'admin_notification_created', 'audit_id': instance.id})
