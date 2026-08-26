from django.db import models
from accounts.models import Member


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        SAVINGS = 'Savings', 'Savings'
        LOAN = 'Loan', 'Loan'
        LOAN_REPAYMENT = 'Loan Repayment', 'Loan Repayment'
        WITHDRAWAL = 'Withdrawal', 'Withdrawal'
        TRANSFER = 'Transfer', 'Transfer'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        COMPLETED = 'Completed', 'Completed'
        FAILED = 'Failed', 'Failed'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=30, blank=True)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_type} - {self.reference}'
