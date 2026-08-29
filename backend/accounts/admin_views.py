from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from loans.models import Loan
from savings.payment_models import Payment
from savings.models import Savings
from transactions.models import Transaction
from .models import AuditLog, Member, SACCOSettings


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        members = Member.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
            new=Count('id', filter=Q(date_joined__date__gte=month_start)),
            with_loans=Count('id', filter=Q(loans__status__in=[Loan.Status.PENDING, Loan.Status.APPROVED, Loan.Status.ACTIVE], loans__outstanding_balance__gt=0), distinct=True),
        )
        savings = Savings.objects.aggregate(
            total=Sum('amount'),
            today=Sum('amount', filter=Q(created_at__date=today)),
            month=Sum('amount', filter=Q(created_at__date__gte=month_start)),
        )
        loan_queryset = Loan.objects.exclude(status=Loan.Status.REJECTED)
        loans = loan_queryset.aggregate(
            count=Count('id'),
            issued=Sum('loan_amount', filter=Q(status__in=[Loan.Status.APPROVED, Loan.Status.ACTIVE, Loan.Status.COMPLETED])),
            outstanding=Sum('outstanding_balance', filter=Q(status__in=[Loan.Status.PENDING, Loan.Status.APPROVED, Loan.Status.ACTIVE])),
            repaid=Sum('amount_paid'),
            pending=Count('id', filter=Q(status=Loan.Status.PENDING)),
        )
        payments = Payment.objects.aggregate(
            pending=Count('id', filter=Q(status=Payment.Status.PENDING)),
            verified=Count('id', filter=Q(status=Payment.Status.VERIFIED)),
            failed=Count('id', filter=Q(status=Payment.Status.FAILED)),
            duplicate=Count('id', filter=Q(status=Payment.Status.DUPLICATE)),
        )
        return Response({
            'members': {key: value or 0 for key, value in members.items()},
            'savings': {key: value or 0 for key, value in savings.items()},
            'loans': {key: value or 0 for key, value in loans.items()},
            'payments': payments,
            'total_members': members['active'] or 0,
            'total_savings': savings['total'] or 0,
            'total_loans': loans['issued'] or 0,
            'outstanding_loans': loans['outstanding'] or 0,
            'today_transactions': Transaction.objects.filter(created_at__date=today).count(),
            'pending_payments': payments['pending'],
            'failed_payments': payments['failed'] + payments['duplicate'],
        })


class AdminMembersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        query = request.query_params.get('search', '')
        members = Member.objects.all().select_related('user').prefetch_related('savings', 'loans')
        if query:
            members = members.filter(Q(full_name__icontains=query) | Q(email__icontains=query) | Q(phone_number__icontains=query) | Q(nin__icontains=query))
        return Response([admin_member_data(member) for member in members])


def admin_member_data(member):
    active_loans = [loan for loan in member.loans.all() if loan.status in [Loan.Status.PENDING, Loan.Status.APPROVED, Loan.Status.ACTIVE]]
    return {
        'id': member.id,
        'full_name': member.full_name,
        'username': member.user.username if member.user else '',
        'phone_number': member.phone_number,
        'email': member.email,
        'is_active': member.is_active,
        'savings_balance': sum((saving.amount for saving in member.savings.all()), 0),
        'loan_balance': sum((loan.outstanding_balance for loan in active_loans), 0),
        'loan_count': len(active_loans),
    }


class AdminMemberDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, member_id):
        try:
            member = Member.objects.select_related('user').prefetch_related('savings', 'loans').get(pk=member_id)
        except Member.DoesNotExist:
            return Response({'detail': 'Member not found.'}, status=404)
        active_loans = [loan for loan in member.loans.all() if loan.status in [Loan.Status.PENDING, Loan.Status.APPROVED, Loan.Status.ACTIVE]]
        return Response({
            **admin_member_data(member),
            'profile_image': request.build_absolute_uri(member.profile_image.url) if member.profile_image else None,
            'date_of_birth': member.date_of_birth,
            'gender': member.gender,
            'nin': member.nin,
            'address': member.address,
            'next_of_kin_name': member.next_of_kin_name,
            'next_of_kin_phone': member.next_of_kin_phone,
            'date_joined': member.date_joined,
            'loans': [{
                'id': loan.id,
                'loan_amount': loan.loan_amount,
                'amount_paid': loan.amount_paid,
                'outstanding_balance': loan.outstanding_balance,
                'status': loan.status,
                'created_at': loan.created_at,
                'approved_at': loan.approved_at,
                'rejection_reason': loan.rejection_reason,
            } for loan in member.loans.all()],
            'active_loan_count': len(active_loans),
        })


class AdminLoanActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, loan_id):
        try:
            loan = Loan.objects.get(pk=loan_id)
        except Loan.DoesNotExist:
            return Response({'detail': 'Loan not found.'}, status=404)
        action = request.data.get('action')
        if action not in ['approve', 'reject']:
            return Response({'detail': 'Action must be approve or reject.'}, status=400)
        if loan.status != Loan.Status.PENDING:
            return Response({'detail': 'Only pending loan applications can be reviewed.'}, status=409)
        if action == 'reject' and not request.data.get('reason', '').strip():
            return Response({'detail': 'A rejection reason is required.'}, status=400)
        loan.status = Loan.Status.APPROVED if action == 'approve' else Loan.Status.REJECTED
        loan.approved_by = request.user
        loan.approved_at = timezone.now()
        loan.rejection_reason = request.data.get('reason', '') if action == 'reject' else ''
        loan.save()
        AuditLog.objects.create(user=request.user, action=f'loan_{action}d', object_type='Loan', object_id=str(loan.id), description=f'Admin {action}d loan {loan.id}.')
        return Response({'status': loan.status, 'approved_at': loan.approved_at})


class AdminAuditView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response([{'id': log.id, 'action': log.action, 'object_type': log.object_type, 'object_id': log.object_id, 'description': log.description, 'created_at': log.created_at} for log in AuditLog.objects.select_related('user')[:100]])


class PaymentConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings = SACCOSettings.current()
        return Response({
            'sacco_name': settings.sacco_name,
            'loan_interest_rate': settings.loan_interest_rate,
            'mtn_number': settings.mtn_number,
            'airtel_number': settings.airtel_number,
            'whatsapp_group_link': settings.whatsapp_group_link,
            'mtn_ussd_template': settings.mtn_ussd_template,
            'airtel_ussd_template': settings.airtel_ussd_template,
            'pesapal_store_url': getattr(settings, 'pesapal_store_url', None) or getattr(__import__('django.conf').conf.settings, 'PESAPAL_STORE_URL', 'https://store.pesapal.com/youthsacco'),
            'pesapal_country_code': getattr(__import__('django.conf').conf.settings, 'PESAPAL_COUNTRY_CODE', 'UG'),
        })
