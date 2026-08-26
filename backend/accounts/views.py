from decimal import Decimal

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from loans.models import Loan
from savings.models import Savings
from transactions.models import Transaction
from .models import Member
from .serializers import MemberSerializer
from transactions.serializers import TransactionSerializer


class MemberViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemberSerializer

    def get_queryset(self):
        return Member.objects.filter(user=self.request.user, is_active=True)


class DashboardView(APIView):
    def get(self, request):
        try:
            member = request.user.member_profile
        except Member.DoesNotExist:
            return Response({'detail': 'Member profile not found.'}, status=404)
        return self._dashboard_response(member)

    def _dashboard_response(self, member):
        savings_total = Savings.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        loan_total = Loan.objects.filter(member=member, status__in=[Loan.Status.PENDING, Loan.Status.APPROVED, Loan.Status.ACTIVE]).aggregate(total=Sum('outstanding_balance'))['total'] or Decimal('0')
        recent = Transaction.objects.filter(member=member)[:5]
        return Response({'member': MemberSerializer(member).data, 'current_savings': savings_total, 'loan_balance': loan_total, 'recent_transactions': TransactionSerializer(recent, many=True).data})
