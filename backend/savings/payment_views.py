import base64
import json
import logging
import uuid
from decimal import Decimal
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog, Member, SACCOSettings
from accounts.notification_utils import notify_member
from loans.models import Loan
from transactions.models import Transaction
from .models import Savings
from .payment_models import Payment
from .payment_serializers import PaymentSerializer

logger = logging.getLogger(__name__)


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

    def _initiate_pesapal_payment(self, member, amount, purpose, phone_number=''):
        consumer_key = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
        consumer_secret = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')
        api_base_url = getattr(settings, 'PESAPAL_API_BASE_URL', 'https://cybqa.pesapal.com/pesapalv3/api').rstrip('/')
        if not consumer_key or not consumer_secret:
            raise ValueError('PesaPal sandbox credentials are not configured.')

        phone_value = (phone_number or member.phone_number or '').strip()
        if not phone_value:
            raise ValueError('A phone number is required to receive the PesaPal PIN prompt.')

        token_request = Request(
            f'{api_base_url}/Auth/RequestToken',
            data=json.dumps({'grant_type': 'client_credentials'}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Basic ' + base64.b64encode(f'{consumer_key}:{consumer_secret}'.encode('utf-8')).decode('utf-8'),
            },
            method='POST',
        )
        token_payload = json.loads(urlopen(token_request, timeout=30).read().decode('utf-8') or '{}')
        access_token = token_payload.get('access_token') or token_payload.get('token')
        if not access_token:
            raise ValueError('PesaPal token request did not return an access token.')

        reference = f'YS-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
        payment_payload = {
            'id': reference,
            'currency': 'UGX',
            'amount': str(int(amount)),
            'description': purpose.replace('_', ' ').title(),
            'callback_url': f'{settings.FRONTEND_URL}/payment/complete',
            'redirect_mode': 'TOP',
            'billing_address': {
                'email_address': member.email or 'member@example.com',
                'phone_number': phone_value,
                'country_code': getattr(settings, 'PESAPAL_COUNTRY_CODE', 'UG'),
            },
            'notification_id': str(uuid.uuid4()),
        }
        order_request = Request(
            f'{api_base_url}/Transactions/SubmitOrderRequest',
            data=json.dumps(payment_payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {access_token}',
            },
            method='POST',
        )
        order_payload = json.loads(urlopen(order_request, timeout=30).read().decode('utf-8') or '{}')
        redirect_url = order_payload.get('redirect_url') or order_payload.get('redirectUrl') or order_payload.get('url')
        if not redirect_url:
            raise ValueError('PesaPal order request did not return a redirect URL.')
        return reference, redirect_url

    def post(self, request):
        provider = str(request.data.get('provider', '')).strip()
        purpose = request.data.get('purpose', Payment.Purpose.SAVINGS)
        phone_number = str(request.data.get('phone_number', '')).strip()
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
        if amount <= 0:
            return Response({'detail': 'Choose a supported provider and a positive amount.'}, status=400)

        if provider.lower() == 'pesapal':
            if not phone_number and not member.phone_number:
                return Response({'detail': 'A phone number is required so the PIN prompt can be sent.'}, status=400)
            try:
                reference, redirect_url = self._initiate_pesapal_payment(member, amount, purpose, phone_number)
            except Exception as exc:
                logger.exception('PesaPal payment initiation failed for member %s', getattr(member, 'id', 'unknown'))
                detail = str(exc).strip() or 'PesaPal payment could not be started right now.'
                return Response({'detail': f'PesaPal payment could not be started: {detail}'}, status=503)
            payment = Payment.objects.create(
                member=member,
                purpose=purpose,
                provider=Payment.Provider.PESAPAL,
                transaction_id=reference,
                internal_reference=reference,
                amount=amount,
                sacco_number=phone_number or member.phone_number,
            )
            notify_member(member, 'Payment started', f'Your {purpose.replace("_", " ")} payment of UGX {amount:,.0f} has been started with PesaPal and is awaiting confirmation.')
            return Response({'payment': PaymentSerializer(payment).data, 'redirect_url': redirect_url}, status=status.HTTP_201_CREATED)

        if provider not in Payment.Provider.values:
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

    def _apply_verified_payment(self, payment):
        payment.status = Payment.Status.VERIFIED
        payment.provider_verified = True
        payment.source = Payment.Source.PROVIDER_API
        payment.verified_by = payment.member.user if payment.member.user else None
        payment.verified_at = timezone.now()
        if payment.purpose == Payment.Purpose.ACCOUNT_ACTIVATION:
            payment.member.is_active = True
            if payment.member.user:
                payment.member.user.is_active = True
                payment.member.user.save(update_fields=['is_active'])
            payment.member.save(update_fields=['is_active'])
            Transaction.objects.create(
                member=payment.member,
                transaction_type=Transaction.TransactionType.SAVINGS,
                amount=Decimal('0'),
                payment_method=payment.provider,
                description='Account activation fee',
                reference=payment.internal_reference,
                status=Transaction.Status.COMPLETED,
            )
        elif payment.purpose == Payment.Purpose.LOAN_REPAYMENT:
            active_loan = payment.member.loans.filter(status__in=[Loan.Status.ACTIVE, Loan.Status.APPROVED]).order_by('-created_at').first()
            if active_loan:
                active_loan.amount_paid = active_loan.amount_paid + payment.amount
                active_loan.save(update_fields=['amount_paid', 'outstanding_balance'])
            Transaction.objects.create(
                member=payment.member,
                transaction_type=Transaction.TransactionType.LOAN_REPAYMENT,
                amount=payment.amount,
                payment_method=payment.provider,
                description='Loan repayment',
                reference=payment.internal_reference,
                status=Transaction.Status.COMPLETED,
            )
        else:
            Savings.objects.create(
                member=payment.member,
                amount=payment.amount,
                payment_method='MTN Mobile Money' if payment.provider == Payment.Provider.MTN else 'Airtel Money' if payment.provider == Payment.Provider.AIRTEL else 'PesaPal',
                transaction_reference=payment.internal_reference,
            )
            Transaction.objects.create(
                member=payment.member,
                transaction_type=Transaction.TransactionType.SAVINGS,
                amount=payment.amount,
                payment_method=payment.provider,
                description='Savings payment',
                reference=payment.internal_reference,
                status=Transaction.Status.COMPLETED,
            )
        payment.save(update_fields=['status', 'provider_verified', 'source', 'verified_by', 'verified_at'])

    def post(self, request):
        provider = str(request.data.get('provider', '')).strip()
        transaction_id = str(request.data.get('transaction_id', '')).strip()
        source_status = str(request.data.get('status', '')).strip().upper()
        route_name = str(request.data.get('purpose', request.data.get('route', request.data.get('payment_type', Payment.Purpose.SAVINGS)))).strip()
        try:
            amount = Decimal(str(request.data.get('amount', '0')))
            member_id = request.data.get('member_id') or getattr(request.user.member_profile, 'id', None)
            member = Member.objects.filter(id=member_id).select_related('user').first() if member_id else request.user.member_profile
        except (ValueError, TypeError, AttributeError, KeyError):
            return Response({'detail': 'Invalid payment payload.'}, status=400)
        if provider not in Payment.Provider.values or not transaction_id or amount <= 0:
            return Response({'detail': 'Provider, transaction ID, and positive amount are required.'}, status=400)
        if route_name not in Payment.Purpose.values:
            route_name = Payment.Purpose.SAVINGS

        success_statuses = {'SUCCESS', 'SUCCESSFUL', 'COMPLETED', 'COMPLETED_SUCCESSFULLY', 'PAID', 'VERIFIED', 'OK'}
        is_success = bool(request.data.get('successful') in [True, 'true', 'True', '1']) or source_status in success_statuses or source_status.startswith('SUCCESS') or source_status.startswith('COMPLETED')
        if not is_success:
            payment = Payment.objects.filter(provider=provider, transaction_id=transaction_id).first()
            if payment:
                payment.status = Payment.Status.FAILED
                payment.provider_verified = False
                payment.save(update_fields=['status', 'provider_verified'])
            return Response({'detail': 'Payment receipt indicates the transaction did not complete successfully.'}, status=400)

        settings = SACCOSettings.current()
        sacco_number = str(request.data.get('sacco_number', request.data.get('phone_number', ''))).strip()
        expected_number = settings.mtn_number if provider == Payment.Provider.MTN else settings.airtel_number if provider == Payment.Provider.AIRTEL else ''
        with transaction.atomic():
            payment = Payment.objects.select_for_update().filter(provider=provider, transaction_id=transaction_id).first()
            if payment:
                if payment.status == Payment.Status.VERIFIED:
                    return Response(PaymentSerializer(payment).data, status=200)
                payment.member = member
                payment.purpose = route_name
                payment.amount = amount
                payment.sacco_number = sacco_number or payment.sacco_number
                payment.payment_time = request.data.get('payment_time') or payment.payment_time
                payment.source = Payment.Source.PROVIDER_API
                payment.sms_received = False
            else:
                payment = Payment.objects.create(
                    member=member,
                    provider=provider,
                    transaction_id=transaction_id,
                    purpose=route_name,
                    internal_reference=f'YS-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}',
                    amount=amount,
                    sacco_number=sacco_number,
                    status=Payment.Status.PENDING,
                    source=Payment.Source.PROVIDER_API,
                    provider_verified=False,
                    sms_received=False,
                    payment_time=request.data.get('payment_time') or None,
                )

            if provider != Payment.Provider.PESAPAL and expected_number and sacco_number and sacco_number != expected_number:
                payment.status = Payment.Status.REJECTED
                payment.provider_verified = False
                payment.save(update_fields=['status', 'provider_verified', 'sacco_number'])
                notify_member(member, 'Payment rejected', 'Your payment was rejected because the SACCO number did not match the configured account.')
                return Response({'detail': 'SACCO number does not match configured account.', 'payment': PaymentSerializer(payment).data}, status=400)

            self._apply_verified_payment(payment)
            notify_member(member, 'Payment received', f'Your {route_name.replace("_", " ")} payment of UGX {amount:,.0f} was confirmed by the payment provider and updated in real time.')
            admin_users = list(getattr(request.user.__class__, 'objects', None).filter(is_staff=True, is_active=True).exclude(email='').values_list('email', flat=True) if getattr(request.user.__class__, 'objects', None) is not None else [])
            if admin_users:
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        'SACCO payment verified',
                        f'A successful {route_name.replace("_", " ")} payment of UGX {amount:,.0f} for {member.full_name} was confirmed by {provider}.',
                        settings.DEFAULT_FROM_EMAIL,
                        admin_users,
                        fail_silently=True,
                    )
                except Exception:
                    pass
            AuditLog.objects.create(
                user=request.user,
                action='payment_verified',
                object_type='Payment',
                object_id=str(payment.id),
                description=f'Provider receipt for {provider} confirmed payment {transaction_id} for {route_name.replace("_", " ")} amount UGX {amount:,.0f}.',
            )
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
