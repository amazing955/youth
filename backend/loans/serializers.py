from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from accounts.models import SACCOSettings
from savings.models import Savings
from .models import Loan


class LoanSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)

    def validate_loan_amount(self, value):
        member = self.context['request'].user.member_profile
        savings = Savings.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        maximum = max(savings - Decimal('20000'), Decimal('0'))
        if value > maximum:
            raise serializers.ValidationError(f'Loan amount cannot exceed {maximum:,.0f} UGX. Keep at least UGX 20,000 in savings.')
        if value <= 0:
            raise serializers.ValidationError('Enter a loan amount greater than zero.')
        return value

    def create(self, validated_data):
        request = self.context['request']
        member = request.user.member_profile
        validated_data['member'] = member
        validated_data['status'] = Loan.Status.PENDING
        validated_data['interest_rate'] = SACCOSettings.current().loan_interest_rate
        return super().create(validated_data)

    class Meta:
        model = Loan
        fields = ['id', 'member', 'member_name', 'loan_amount', 'interest_rate', 'amount_paid', 'outstanding_balance', 'status', 'approved_by', 'approved_at', 'rejection_reason', 'created_at']
        read_only_fields = ['id', 'member', 'member_name', 'interest_rate', 'outstanding_balance', 'status', 'approved_by', 'approved_at', 'created_at']
