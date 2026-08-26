from django.db import models
from accounts.models import Member


class Savings(models.Model):
    class PaymentMethod(models.TextChoices):
        MTN = 'MTN Mobile Money', 'MTN Mobile Money'
        AIRTEL = 'Airtel Money', 'Airtel Money'

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='savings')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices)
    transaction_reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.member} - {self.amount}'


from .payment_models import Payment
