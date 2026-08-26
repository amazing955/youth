from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog
from .models import Loan
from .serializers import LoanSerializer


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer

    def get_queryset(self):
        queryset = Loan.objects.select_related('member').all()
        return queryset if self.request.user.is_staff else queryset.filter(member__user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return Response({'detail': 'Loans cannot be deleted. Cancel a pending application instead.'}, status=405)


class CancelLoanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, loan_id):
        try:
            loan = Loan.objects.get(pk=loan_id, member__user=request.user, status=Loan.Status.PENDING)
        except Loan.DoesNotExist:
            return Response({'detail': 'Only your pending loan applications can be cancelled.'}, status=404)
        loan.status = Loan.Status.REJECTED
        loan.rejection_reason = 'Cancelled by member.'
        loan.approved_at = timezone.now()
        loan.save(update_fields=['status', 'rejection_reason', 'approved_at'])
        AuditLog.objects.create(user=request.user, action='loan_cancelled', object_type='Loan', object_id=str(loan.id), description=f'Member cancelled loan application {loan.id}.')
        return Response({'id': loan.id, 'status': loan.status, 'rejection_reason': loan.rejection_reason})
