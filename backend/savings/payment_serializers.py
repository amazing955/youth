from rest_framework import serializers
from .payment_models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'member', 'provider', 'transaction_id', 'internal_reference', 'amount', 'sacco_number', 'status', 'source', 'provider_verified', 'sms_received', 'payment_time', 'verified_at', 'created_at']
        read_only_fields = ['id', 'member', 'internal_reference', 'sacco_number', 'status', 'source', 'provider_verified', 'sms_received', 'verified_at', 'created_at']

    def validate_provider(self, value):
        if value not in Payment.Provider.values:
            raise serializers.ValidationError('Unsupported payment provider.')
        return value
