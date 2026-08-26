from django.conf import settings
from django.db import models
from accounts.models import Member


class Payment(models.Model):
    class Provider(models.TextChoices):
        MTN = 'MTN', 'MTN Mobile Money'
        AIRTEL = 'Airtel', 'Airtel Money'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        VERIFIED = 'Verified', 'Verified'
        FAILED = 'Failed', 'Failed'
        DUPLICATE = 'Duplicate', 'Duplicate'
        REJECTED = 'Rejected', 'Rejected'

    class Source(models.TextChoices):
        SMS = 'SMS', 'SMS'
        PROVIDER_API = 'Provider API', 'Provider API'
        ADMIN = 'Admin verification', 'Admin verification'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    internal_reference = models.CharField(max_length=32, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    sacco_number = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.SMS)
    provider_verified = models.BooleanField(default=False)
    sms_received = models.BooleanField(default=False)
    payment_time = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_payments')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['provider', 'transaction_id'], name='unique_provider_transaction')]
        ordering = ['-created_at']

    def __str__(self):
        return self.internal_reference
