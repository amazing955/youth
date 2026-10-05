from decimal import Decimal, InvalidOperation
import uuid

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from loans.models import Loan
from savings.payment_models import Payment
from savings.models import Savings
from transactions.models import Transaction
from .models import AuditLog, Member, SACCOSettings, WithdrawalRequest
from .notification_utils import notify_member


def expire_withdrawal_requests(queryset):
    now = timezone.now()
    due_requests = list(queryset.filter(status=WithdrawalRequest.Status.PENDING, expires_at__lte=now).select_related('member'))
    for withdrawal_request in due_requests:
        updated = WithdrawalRequest.objects.filter(
            pk=withdrawal_request.pk,
            status=WithdrawalRequest.Status.PENDING,
            expires_at__lte=now,
        ).update(status=WithdrawalRequest.Status.EXPIRED, responded_at=now)
        if updated:
            AuditLog.objects.create(
                action='member_withdrawal_expired',
                object_type='WithdrawalRequest',
                object_id=str(withdrawal_request.id),
                description=f'Withdrawal request for UGX {withdrawal_request.amount:,.2f} for {withdrawal_request.member.full_name} expired without member approval; no funds were withdrawn.',
            )
            notify_member(withdrawal_request.member, 'Withdrawal request expired', 'The withdrawal request expired without your approval. No funds were withdrawn.', 'Withdrawal approval')


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
        'loan_balance': sum((loan.calculated_outstanding_balance() for loan in active_loans), 0),
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
        manual_deposits = [saving for saving in member.savings.all() if saving.payment_method == Savings.PaymentMethod.MANUAL and saving.amount > 0]
        manual_reversal_references = set(Savings.objects.filter(member=member, transaction_reference__startswith='REVERSAL-').values_list('transaction_reference', flat=True))
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
            'manual_deposits': [{
                'amount': saving.amount,
                'reference': saving.transaction_reference,
                'created_at': saving.created_at,
                'reversed': f'REVERSAL-{saving.transaction_reference}' in manual_reversal_references,
            } for saving in manual_deposits],
            'loans': [{
                'id': loan.id,
                'loan_amount': loan.loan_amount,
                'amount_paid': loan.amount_paid,
                'outstanding_balance': loan.calculated_outstanding_balance(),
                'status': loan.status,
                'created_at': loan.created_at,
                'approved_at': loan.approved_at,
                'rejection_reason': loan.rejection_reason,
            } for loan in member.loans.all()],
            'active_loan_count': len(active_loans),
        })


class AdminMemberDepositView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, member_id):
        raw_amount = request.data.get('amount')
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Enter a valid deposit amount.'}, status=400)
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2 or amount >= Decimal('1000000000000'):
            return Response({'detail': 'Deposit amount must be positive and have no more than two decimal places.'}, status=400)

        with transaction.atomic():
            try:
                member = Member.objects.select_for_update().get(pk=member_id)
            except Member.DoesNotExist:
                return Response({'detail': 'Member not found.'}, status=404)
            previous_balance = Savings.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            reference = f'MANUAL-{uuid.uuid4().hex.upper()}'
            Savings.objects.create(
                member=member,
                amount=amount,
                payment_method=Savings.PaymentMethod.MANUAL,
                transaction_reference=reference,
            )
            Transaction.objects.create(
                member=member,
                transaction_type=Transaction.TransactionType.SAVINGS,
                amount=amount,
                payment_method=Savings.PaymentMethod.MANUAL,
                description='Manual savings deposit',
                reference=reference,
                status=Transaction.Status.COMPLETED,
            )
            new_balance = previous_balance + amount
            AuditLog.objects.create(
                user=request.user,
                action='member_balance_updated',
                object_type='Member',
                object_id=str(member.id),
                description=(
                    f'Manual deposit for {member.full_name}: deposited UGX {amount:,.2f}; '
                    f'previous balance UGX {previous_balance:,.2f}; new balance UGX {new_balance:,.2f}; '
                    f'reference {reference}.'
                ),
            )

        return Response({'member_id': member.id, 'amount': amount, 'previous_balance': previous_balance, 'new_balance': new_balance, 'transaction_reference': reference}, status=201)


class AdminMemberDepositReverseView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, member_id, reference):
        with transaction.atomic():
            try:
                member = Member.objects.select_for_update().get(pk=member_id)
                saving = Savings.objects.select_for_update().get(
                    member=member,
                    transaction_reference=reference,
                    payment_method=Savings.PaymentMethod.MANUAL,
                )
            except (Member.DoesNotExist, Savings.DoesNotExist):
                return Response({'detail': 'Manual deposit not found.'}, status=404)
            if saving.amount <= 0:
                return Response({'detail': 'Only original manual deposits can be reversed.'}, status=409)

            reversal_reference = f'REVERSAL-{saving.transaction_reference}'
            if Savings.objects.filter(transaction_reference=reversal_reference).exists():
                return Response({'detail': 'This manual deposit has already been reversed.'}, status=409)

            previous_balance = Savings.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            new_balance = previous_balance - saving.amount
            if new_balance < 0:
                return Response({'detail': 'This deposit cannot be reversed because the member balance has already been used.'}, status=409)
            Savings.objects.create(
                member=member,
                amount=-saving.amount,
                payment_method=Savings.PaymentMethod.MANUAL,
                transaction_reference=reversal_reference,
            )
            Transaction.objects.create(
                member=member,
                transaction_type=Transaction.TransactionType.SAVINGS,
                amount=-saving.amount,
                payment_method=Savings.PaymentMethod.MANUAL,
                description='Reversal of manual savings deposit',
                reference=reversal_reference,
                status=Transaction.Status.COMPLETED,
            )
            AuditLog.objects.create(
                user=request.user,
                action='member_balance_reversed',
                object_type='Member',
                object_id=str(member.id),
                description=(
                    f'Reversed manual deposit for {member.full_name}: reversed UGX {saving.amount:,.2f}; '
                    f'previous balance UGX {previous_balance:,.2f}; new balance UGX {new_balance:,.2f}; '
                    f'original reference {saving.transaction_reference}; reversal reference {reversal_reference}.'
                ),
            )

        return Response({'member_id': member.id, 'amount': saving.amount, 'previous_balance': previous_balance, 'new_balance': new_balance, 'transaction_reference': reversal_reference}, status=201)


class AdminMemberWithdrawalView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, member_id):
        raw_amount = request.data.get('amount')
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Enter a valid withdrawal amount.'}, status=400)
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2 or amount >= Decimal('1000000000000'):
            return Response({'detail': 'Withdrawal amount must be positive and have no more than two decimal places.'}, status=400)

        with transaction.atomic():
            try:
                member = Member.objects.select_for_update().get(pk=member_id)
            except Member.DoesNotExist:
                return Response({'detail': 'Member not found.'}, status=404)
            previous_balance = Savings.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            if amount > previous_balance:
                return Response({'detail': f'Withdrawal cannot exceed the current balance of UGX {previous_balance:,.2f}.'}, status=400)
            expire_withdrawal_requests(WithdrawalRequest.objects.filter(member=member))
            if WithdrawalRequest.objects.filter(member=member, status=WithdrawalRequest.Status.PENDING).exists():
                return Response({'detail': 'This member already has a pending withdrawal request.'}, status=409)
            withdrawal_request = WithdrawalRequest.objects.create(
                member=member,
                requested_by=request.user,
                amount=amount,
                expires_at=timezone.now() + timezone.timedelta(minutes=3),
            )
            AuditLog.objects.create(
                user=request.user,
                action='member_withdrawal_requested',
                object_type='WithdrawalRequest',
                object_id=str(withdrawal_request.id),
                description=f'Admin {request.user} requested a withdrawal of UGX {amount:,.2f} for {member.full_name}; member approval expires at {withdrawal_request.expires_at.isoformat()}.',
            )
            notify_member(
                member,
                'Withdrawal approval required',
                f'An admin requested a withdrawal of UGX {amount:,.2f} from your savings. Approve or cancel it in the app within 3 minutes. No funds will be withdrawn without your approval.',
                'Withdrawal approval',
            )
        return Response({
            'id': withdrawal_request.id,
            'member_id': member.id,
            'amount': amount,
            'previous_balance': previous_balance,
            'status': withdrawal_request.status,
            'expires_at': withdrawal_request.expires_at,
        }, status=202)


class MemberWithdrawalRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = WithdrawalRequest.objects.filter(member__user=request.user).select_related('member')
        expire_withdrawal_requests(queryset)
        pending = queryset.filter(status=WithdrawalRequest.Status.PENDING)
        return Response([{
            'id': item.id,
            'amount': item.amount,
            'status': item.status,
            'expires_at': item.expires_at,
            'created_at': item.created_at,
        } for item in pending])

    def post(self, request, request_id):
        action = request.data.get('action')
        if action not in ['approve', 'cancel']:
            return Response({'detail': 'Action must be approve or cancel.'}, status=400)
        with transaction.atomic():
            try:
                withdrawal_request = WithdrawalRequest.objects.select_for_update().select_related('member').get(
                    pk=request_id,
                    member__user=request.user,
                )
            except WithdrawalRequest.DoesNotExist:
                return Response({'detail': 'Withdrawal request not found.'}, status=404)
            if withdrawal_request.status != WithdrawalRequest.Status.PENDING:
                return Response({'detail': 'This withdrawal request is no longer pending.'}, status=409)
            if withdrawal_request.expires_at <= timezone.now():
                withdrawal_request.status = WithdrawalRequest.Status.EXPIRED
                withdrawal_request.responded_at = timezone.now()
                withdrawal_request.save(update_fields=['status', 'responded_at'])
                AuditLog.objects.create(
                    action='member_withdrawal_expired',
                    object_type='WithdrawalRequest',
                    object_id=str(withdrawal_request.id),
                    description=f'Withdrawal request for UGX {withdrawal_request.amount:,.2f} for {withdrawal_request.member.full_name} expired without member approval; no funds were withdrawn.',
                )
                notify_member(withdrawal_request.member, 'Withdrawal request expired', 'The withdrawal request expired without your approval. No funds were withdrawn.', 'Withdrawal approval')
                return Response({'detail': 'This withdrawal request has expired. No funds were withdrawn.'}, status=409)

            if action == 'approve':
                member = Member.objects.select_for_update().get(pk=withdrawal_request.member_id)
                previous_balance = Savings.objects.filter(member=member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                if withdrawal_request.amount > previous_balance:
                    withdrawal_request.status = WithdrawalRequest.Status.CANCELLED
                    withdrawal_request.responded_at = timezone.now()
                    withdrawal_request.save(update_fields=['status', 'responded_at'])
                    AuditLog.objects.create(
                        user=request.user,
                        action='member_withdrawal_cancelled',
                        object_type='WithdrawalRequest',
                        object_id=str(withdrawal_request.id),
                        description='Member approval could not be completed because the available savings balance changed; no funds were withdrawn.',
                    )
                    return Response({'detail': 'The available balance has changed. No funds were withdrawn.'}, status=409)
                reference = f'WITHDRAWAL-{uuid.uuid4().hex.upper()}'
                Savings.objects.create(member=member, amount=-withdrawal_request.amount, payment_method=Savings.PaymentMethod.ADMIN_WITHDRAWAL, transaction_reference=reference)
                Transaction.objects.create(
                    member=member,
                    transaction_type=Transaction.TransactionType.WITHDRAWAL,
                    amount=-withdrawal_request.amount,
                    payment_method=Savings.PaymentMethod.ADMIN_WITHDRAWAL,
                    description='Member-approved admin savings withdrawal',
                    reference=reference,
                    status=Transaction.Status.COMPLETED,
                )
                withdrawal_request.status = WithdrawalRequest.Status.APPROVED
                withdrawal_request.transaction_reference = reference
                withdrawal_request.responded_at = timezone.now()
                withdrawal_request.save(update_fields=['status', 'transaction_reference', 'responded_at'])
                new_balance = previous_balance - withdrawal_request.amount
                audit_action = 'member_withdrawal_approved'
                audit_description = f'{member.full_name} approved withdrawal of UGX {withdrawal_request.amount:,.2f}; previous balance UGX {previous_balance:,.2f}; new balance UGX {new_balance:,.2f}; reference {reference}.'
            else:
                withdrawal_request.status = WithdrawalRequest.Status.CANCELLED
                withdrawal_request.responded_at = timezone.now()
                withdrawal_request.save(update_fields=['status', 'responded_at'])
                audit_action = 'member_withdrawal_cancelled'
                audit_description = f'{withdrawal_request.member.full_name} cancelled withdrawal request for UGX {withdrawal_request.amount:,.2f}; no funds were withdrawn.'
                new_balance = None
                reference = ''

            AuditLog.objects.create(
                user=request.user,
                action=audit_action,
                object_type='WithdrawalRequest',
                object_id=str(withdrawal_request.id),
                description=audit_description,
            )
            notify_member(
                withdrawal_request.member,
                'Withdrawal approved' if action == 'approve' else 'Withdrawal cancelled',
                f'The withdrawal request for UGX {withdrawal_request.amount:,.2f} was {"approved" if action == "approve" else "cancelled"}. {"Your savings balance was updated." if action == "approve" else "No funds were withdrawn."}',
                'Withdrawal approval',
            )
        return Response({
            'id': withdrawal_request.id,
            'status': withdrawal_request.status,
            'amount': withdrawal_request.amount,
            'new_balance': new_balance,
            'transaction_reference': reference,
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


class AdminLoanRepaymentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, loan_id):
        try:
            amount = Decimal(str(request.data.get('amount')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'detail': 'Enter a valid cleared amount.'}, status=400)
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            return Response({'detail': 'Cleared amount must be positive and have no more than two decimal places.'}, status=400)

        with transaction.atomic():
            try:
                loan = Loan.objects.select_for_update().select_related('member').get(pk=loan_id)
            except Loan.DoesNotExist:
                return Response({'detail': 'Loan not found.'}, status=404)
            previous_balance = loan.calculated_outstanding_balance()
            if loan.status in [Loan.Status.PENDING, Loan.Status.REJECTED] or previous_balance <= 0:
                return Response({'detail': 'Only an outstanding approved or active loan can be cleared.'}, status=409)
            if amount > previous_balance:
                return Response({'detail': f'Cleared amount cannot exceed the outstanding balance of UGX {previous_balance:,.2f}.'}, status=400)
            loan.amount_paid += amount
            if loan.amount_paid >= loan.loan_amount + (loan.loan_amount * loan.interest_rate / Decimal('100')).quantize(Decimal('0.01')):
                loan.status = Loan.Status.COMPLETED
            loan.save(update_fields=['amount_paid', 'outstanding_balance', 'status'])
            reference = f'MANUAL-LOAN-{uuid.uuid4().hex.upper()}'
            Transaction.objects.create(
                member=loan.member,
                transaction_type=Transaction.TransactionType.LOAN_REPAYMENT,
                amount=amount,
                payment_method='Manual admin entry',
                description='Manual loan repayment',
                reference=reference,
                status=Transaction.Status.COMPLETED,
            )
            AuditLog.objects.create(
                user=request.user,
                action='loan_repayment_recorded',
                object_type='Loan',
                object_id=str(loan.id),
                description=(
                    f'Admin recorded a loan repayment of UGX {amount:,.2f} for {loan.member.full_name}; '
                    f'previous balance UGX {previous_balance:,.2f}; new balance UGX {loan.outstanding_balance:,.2f}; '
                    f'reference {reference}.'
                ),
            )
        return Response({'id': loan.id, 'amount_paid': loan.amount_paid, 'outstanding_balance': loan.outstanding_balance, 'status': loan.status, 'transaction_reference': reference}, status=201)


class AdminLoanForcePayView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, loan_id):
        with transaction.atomic():
            try:
                loan = Loan.objects.select_for_update().select_related('member').get(pk=loan_id)
            except Loan.DoesNotExist:
                return Response({'detail': 'Loan not found.'}, status=404)
            outstanding = loan.calculated_outstanding_balance()
            if loan.status in [Loan.Status.PENDING, Loan.Status.REJECTED] or outstanding <= 0:
                return Response({'detail': 'Only an outstanding approved or active loan can be force paid.'}, status=409)
            savings_balance = Savings.objects.filter(member=loan.member).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            if savings_balance < outstanding:
                return Response({'detail': f'{loan.member.full_name} has insufficient savings to force pay UGX {outstanding:,.2f}.'}, status=400)
            loan.amount_paid += outstanding
            loan.status = Loan.Status.COMPLETED
            loan.save(update_fields=['amount_paid', 'outstanding_balance', 'status'])
            reference = f'FORCE-LOAN-{uuid.uuid4().hex.upper()}'
            Savings.objects.create(member=loan.member, amount=-outstanding, payment_method=Savings.PaymentMethod.MANUAL, transaction_reference=reference)
            Transaction.objects.create(member=loan.member, transaction_type=Transaction.TransactionType.LOAN_REPAYMENT, amount=-outstanding, payment_method='Forced admin entry', description='Loan force paid from savings', reference=reference, status=Transaction.Status.COMPLETED)
            AuditLog.objects.create(user=request.user, action='loan_force_paid', object_type='Loan', object_id=str(loan.id), description=f'Admin force paid {loan.member.full_name} loan from savings: UGX {outstanding:,.2f}. Previous savings balance UGX {savings_balance:,.2f}; new savings balance UGX {savings_balance - outstanding:,.2f}; reference {reference}.')
        return Response({'id': loan.id, 'amount_paid': loan.amount_paid, 'outstanding_balance': loan.outstanding_balance, 'status': loan.status, 'transaction_reference': reference}, status=201)


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
