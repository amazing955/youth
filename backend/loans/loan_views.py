from decimal import Decimal

from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import SACCOSettings
from savings.models import Savings


class LoanTermsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        savings = Savings.objects.filter(member=request.user.member_profile).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return Response({'current_savings': savings, 'minimum_savings_reserve': 20000, 'maximum_loan_amount': max(savings - Decimal('20000'), Decimal('0')), 'interest_rate': SACCOSettings.current().loan_interest_rate})
