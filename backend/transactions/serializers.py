from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'member', 'transaction_type', 'amount', 'payment_method', 'description', 'reference', 'status', 'created_at']
        read_only_fields = ['id', 'member', 'created_at']
