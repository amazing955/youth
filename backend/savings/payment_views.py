import uuid
from decimal import Decimal
from urllib.parse import quote

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog, SACCOSettings
from accounts.notification_utils import notify_member
from loans.models import Loan
from transactions.models import Transaction
from .models import Savings
from .payment_models import Payment
from .payment_serializers import PaymentSerializer


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.select_related('member').all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(member__user=self.request.user)
        return queryset


class PaymentStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = request.data.get('provider')
        purpose = request.data.get('purpose', Payment.Purpose.SAVINGS)
        try:
            amount = Decimal(str(request.data.get('amount', '0')))
            member = request.user.member_profile
        except (ValueError, TypeError, AttributeError, KeyError):
            return Response({'detail': 'A valid amount and member profile are required.'}, status=400)

        if purpose == Payment.Purpose.ACCOUNT_ACTIVATION and amount != Decimal('10000'):
            return Response({'detail': 'Account activation requires a UGX 10,000 payment.'}, status=400)
        if purpose == Payment.Purpose.LOAN_REPAYMENT and amount <= 0:
            return Response({'detail': 'Loan repayment amount must be greater than zero.'}, status=400)
        if purpose not in Payment.Purpose.values:
            return Response({'detail': 'Unsupported payment purpose.'}, status=400)
        if amount <= 0 or provider not in Payment.Provider.values:
            return Response({'detail': 'Choose a supported provider and a positive amount.'}, status=400)

        settings = SACCOSettings.current()
        number = settings.mtn_number if provider == Payment.Provider.MTN else settings.airtel_number
        template = settings.mtn_ussd_template if provider == Payment.Provider.MTN else settings.airtel_ussd_template
        if not number or not template:
            return Response({'detail': 'This provider is not configured by the SACCO.'}, status=503)
        reference = f'YS-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
        payment = Payment.objects.create(member=member, purpose=purpose, provider=provider, transaction_id=None, internal_reference=reference, amount=amount, sacco_number=number)
        notify_member(member, 'Payment started', f'Your {purpose.replace("_", " ")} payment of UGX {amount:,.0f} has been started and is awaiting confirmation.')
        ussd = template.replace('{SACCO_NUMBER}', number).replace('{AMOUNT}', str(int(amount)))
        return Response({'payment': PaymentSerializer(payment).data, 'ussd_uri': f'tel:{quote(ussd, safe="*")}'}, status=status.HTTP_201_CREATED)


class ReconcilePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = request.data.get('provider')
        transaction_id = str(request.data.get('transaction_id', '')).strip()
        try:
            amount = Decimal(str(request.data.get('amount', '0')))
            member = request.user.member_profile
        except (ValueError, TypeError, AttributeError, KeyError):
            return Response({'detail': 'Invalid payment payload.'}, status=400)
        if provider not in Payment.Provider.values or not transaction_id or amount <= 0:
            return Response({'detail': 'Provider, transaction ID, and positive amount are required.'}, status=400)
        settings = SACCOSettings.current()
        sacco_number = request.data.get('sacco_number', '')
        expected_number = settings.mtn_number if provider == Payment.Provider.MTN else settings.airtel_number
        with transaction.atomic():
            existing = Payment.objects.select_for_update().filter(provider=provider, transaction_id=transaction_id).first()
            if existing:
                AuditLog.objects.create(user=request.user, action='duplicate_payment', object_type='Payment', object_id=str(existing.id), description=f'Payment {transaction_id} marked duplicate.')
                return Response(PaymentSerializer(existing).data, status=409)
            if sacco_number != expected_number:
                payment = Payment.objects.create(member=member, provider=provider, transaction_id=transaction_id, internal_reference=f'YS-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}', amount=amount, sacco_number=sacco_number, status=Payment.Status.REJECTED, sms_received=True)
                notify_member(member, 'Payment rejected', 'Your payment was rejected because the SACCO number did not match the configured account.')
                return Response({'detail': 'SACCO number does not match configured account.', 'payment': PaymentSerializer(payment).data}, status=400)
            payment = Payment.objects.create(member=member, provider=provider, transaction_id=transaction_id, internal_reference=f'YS-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}', amount=amount, sacco_number=sacco_number, status=Payment.Status.PENDING, provider_verified=False, sms_received=True, payment_time=request.data.get('payment_time') or None)
            notify_member(member, 'Payment received', f'Your payment of UGX {amount:,.0f} was received and is awaiting SACCO verification.')
            AuditLog.objects.create(user=request.user, action='payment_received', object_type='Payment', object_id=str(payment.id), description=f'Payment {transaction_id} queued for verification.')
        return Response(PaymentSerializer(payment).data, status=201)


class AdminPaymentActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, payment_id):
        action = request.data.get('action')
        if action not in ['verify', 'reject']:
            return Response({'detail': 'Action must be verify or reject.'}, status=400)
        with transaction.atomic():
            try:
                payment = Payment.objects.select_for_update().get(pk=payment_id)
            except Payment.DoesNotExist:
                return Response({'detail': 'Payment not found.'}, status=404)
            if action == 'reject' and not request.data.get('reason', '').strip():
                return Response({'detail': 'A rejection reason is required.'}, status=400)
            if action == 'verify' and payment.status in [Payment.Status.REJECTED, Payment.Status.DUPLICATE]:
                return Response({'detail': 'This payment cannot be verified.'}, status=409)
            if action == 'verify' and payment.status != Payment.Status.VERIFIED:
                payment.status = Payment.Status.VERIFIED
                payment.provider_verified = True
                payment.verified_by = request.user
                payment.verified_at = timezone.now()
                payment.save(update_fields=['status', 'provider_verified', 'verified_by', 'verified_at'])

                if payment.purpose == Payment.Purpose.ACCOUNT_ACTIVATION:
                    payment.member.is_active = True
                    payment.member.user.is_active = True
                    payment.member.save(update_fields=['is_active'])
                    payment.member.user.save(update_fields=['is_active'])
                    Transaction.objects.create(member=payment.member, transaction_type=Transaction.TransactionType.SAVINGS, amount=Decimal('0'), payment_method=payment.provider, description='Account activation fee', reference=payment.internal_reference, status=Transaction.Status.COMPLETED)
                elif payment.purpose == Payment.Purpose.LOAN_REPAYMENT:
                    active_loan = payment.member.loans.filter(status__in=[Loan.Status.ACTIVE, Loan.Status.APPROVED]).order_by('-created_at').first()
                    if active_loan:
                        active_loan.amount_paid = active_loan.amount_paid + payment.amount
                        active_loan.save(update_fields=['amount_paid', 'outstanding_balance'])
                    Transaction.objects.create(member=payment.member, transaction_type=Transaction.TransactionType.LOAN_REPAYMENT, amount=payment.amount, payment_method=payment.provider, description='Loan repayment', reference=payment.internal_reference, status=Transaction.Status.COMPLETED)
                else:
                    Savings.objects.create(member=payment.member, amount=payment.amount, payment_method='MTN Mobile Money' if payment.provider == Payment.Provider.MTN else 'Airtel Money', transaction_reference=payment.internal_reference)
                    Transaction.objects.create(member=payment.member, transaction_type=Transaction.TransactionType.SAVINGS, amount=payment.amount, payment_method=payment.provider, description='Savings payment', reference=payment.internal_reference, status=Transaction.Status.COMPLETED)
            elif action == 'reject':
                payment.status = Payment.Status.REJECTED
                payment.verified_by = request.user
                payment.verified_at = timezone.now()
                payment.save(update_fields=['status', 'verified_by', 'verified_at'])
            notify_member(payment.member, f'Payment {action}ed', f'Your payment of UGX {payment.amount:,.0f} was {action}d by the SACCO.' + (f' Reason: {request.data.get("reason")}' if action == 'reject' else ''))
            AuditLog.objects.create(user=request.user, action=f'payment_{action}d', object_type='Payment', object_id=str(payment.id), description=f'Payment {payment.transaction_id} {action}d by admin. Reason: {request.data.get("reason", "")}'.strip())
        return Response(PaymentSerializer(payment).data)


class SaccoSettingsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        settings = SACCOSettings.current()
        return Response({'sacco_name': settings.sacco_name, 'loan_interest_rate': settings.loan_interest_rate, 'mtn_number': settings.mtn_number, 'airtel_number': settings.airtel_number, 'whatsapp_group_link': settings.whatsapp_group_link, 'mtn_ussd_template': settings.mtn_ussd_template, 'airtel_ussd_template': settings.airtel_ussd_template})

    def put(self, request):
        settings = SACCOSettings.current()
        for field in ['sacco_name', 'loan_interest_rate', 'mtn_number', 'airtel_number', 'whatsapp_group_link', 'mtn_ussd_template', 'airtel_ussd_template']:
            if field in request.data:
                setattr(settings, field, request.data[field])
        settings.updated_by = request.user
        settings.save()
        AuditLog.objects.create(user=request.user, action='settings_updated', object_type='SACCOSettings', object_id=str(settings.id), description='SACCO payment settings updated.')
        return self.get(request)
