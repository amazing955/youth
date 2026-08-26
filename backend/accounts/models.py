import uuid

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
    sacco_name = models.CharField(max_length=150, default='Youth Savings')
    loan_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    mtn_number = models.CharField(max_length=30)
    airtel_number = models.CharField(max_length=30)
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
