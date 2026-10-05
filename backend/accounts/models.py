import uuid
from django.utils import timezone

from django.conf import settings
from django.db import models


class Member(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='member_profile', null=True, blank=True)
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    profile_image = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    nin = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=255, blank=True)
    next_of_kin_name = models.CharField(max_length=150, blank=True)
    next_of_kin_phone = models.CharField(max_length=30, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class SACCOSettings(models.Model):
    sacco_name = models.CharField(max_length=150, default='Coins and Dreams')
    loan_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    mtn_number = models.CharField(max_length=30)
    airtel_number = models.CharField(max_length=30)
    whatsapp_group_link = models.URLField(blank=True, default='')
    mtn_ussd_template = models.CharField(max_length=255, default='*165*1*{SACCO_NUMBER}*{AMOUNT}#')
    airtel_ussd_template = models.CharField(max_length=255, default='*185*1*{SACCO_NUMBER}*{AMOUNT}#')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sacco_name

    @classmethod
    def current(cls):
        instance = cls.objects.first()
        return instance or cls.objects.create(mtn_number='', airtel_number='')


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Notice(models.Model):
    class Kind(models.TextChoices):
        GENERAL = 'General', 'General notice'
        DEMAND = 'Demand', 'Demand note'
        REMINDER = 'Reminder', 'Loan reminder'

    title = models.CharField(max_length=180)
    message = models.TextField()
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.GENERAL)
    member = models.ForeignKey(Member, null=True, blank=True, on_delete=models.CASCADE, related_name='notices')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='created_notices')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=180)
    message = models.TextField()
    kind = models.CharField(max_length=30, default='General')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        CANCELLED = 'Cancelled', 'Cancelled'
        EXPIRED = 'Expired', 'Expired'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='withdrawal_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='withdrawal_requests')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class PushDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_devices')
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class SupportIssue(models.Model):
    class Status(models.TextChoices):
        OPEN = 'Open', 'Open'
        RESOLVED = 'Resolved', 'Resolved'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='support_issues')
    title = models.CharField(max_length=180, default='Support issue')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    report = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='resolved_support_issues')

    class Meta:
        ordering = ['-created_at']


class AdminLoginOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_login_otps')
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return self.verified_at is None and self.attempts < 5 and timezone.now() < self.expires_at


class FinancialGoal(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='financial_goals')
    name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    achieved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
