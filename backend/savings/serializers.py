from rest_framework import serializers
from .models import Savings


class SavingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Savings
        fields = ['id', 'member', 'amount', 'payment_method', 'transaction_reference', 'created_at']
        read_only_fields = ['id', 'member', 'created_at']
