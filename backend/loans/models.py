from decimal import Decimal
from django.db import models
from django.conf import settings
from accounts.models import Member


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        ACTIVE = 'Active', 'Active'
        COMPLETED = 'Completed', 'Completed'
        REJECTED = 'Rejected', 'Rejected'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    outstanding_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_loans')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.outstanding_balance = self.calculated_outstanding_balance()
        super().save(*args, **kwargs)

    def calculated_outstanding_balance(self):
        interest = (self.loan_amount * self.interest_rate / Decimal('100')).quantize(Decimal('0.01'))
        return max(self.loan_amount + interest - self.amount_paid, Decimal('0'))

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.member} - {self.loan_amount}'
