from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.cache import cache
from django.db.models import Sum
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.auth_serializers import LoginSerializer, RegisterSerializer
from accounts.models import AuditLog, Member, Notification, PushDevice, WithdrawalRequest
from accounts.notification_utils import notify_member
from loans.models import Loan
from savings.models import Savings
from savings.payment_models import Payment
from transactions.models import Transaction

User = get_user_model()


class ActivationFlowTests(TestCase):
    def test_push_device_registration_is_owned_by_authenticated_user(self):
        user = User.objects.create_user(username='pushuser', email='push@example.com', password='Secret123')
        Member.objects.create(user=user, full_name='Push User', email=user.email, phone_number='+256700000015', is_active=True)
        other = User.objects.create_user(username='pushother', email='other-push@example.com', password='Secret123')
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/push-devices/', {'token': 'fcm-token-1', 'platform': 'android'}, format='json')

        self.assertEqual(response.status_code, 201)
        device = PushDevice.objects.get(token='fcm-token-1')
        self.assertEqual(device.user, user)
        client.force_authenticate(user=other)
        response = client.delete('/api/push-devices/', {'token': 'fcm-token-1'}, format='json')
        self.assertEqual(response.status_code, 204)
        self.assertTrue(PushDevice.objects.filter(pk=device.pk).exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_savings_reminder_is_sent_after_seven_days_once(self):
        member = Member.objects.create(full_name='Saving Member', email='saving@example.com', phone_number='+256700000006', is_active=True)
        saving = Savings.objects.create(member=member, amount=Decimal('10000'), payment_method=Savings.PaymentMethod.MTN, transaction_reference='SAV-REMINDER-001')
        Savings.objects.filter(pk=saving.pk).update(created_at=timezone.now() - timedelta(days=8))

        call_command('send_savings_reminders')
        self.assertEqual(Notification.objects.filter(member=member, kind='Savings reminder').count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        call_command('send_savings_reminders')
        self.assertEqual(Notification.objects.filter(member=member, kind='Savings reminder').count(), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_notification_is_emailed_and_can_be_marked_read(self):
        user = User.objects.create_user(username='noticeuser', email='notice@example.com', password='Secret123')
        member = Member.objects.create(user=user, full_name='Notice User', email=user.email, phone_number='+256700000005')
        notify_member(member, 'Test notice', 'A message for the member.')

        self.assertEqual(Notification.objects.filter(member=member).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/notifications/')
        self.assertEqual(response.data['unread_count'], 1)
        notification_id = response.data['notifications'][0]['id']
        response = client.patch(f'/api/notifications/{notification_id}/read/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_read'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', FRONTEND_URL='http://localhost:5173')
    def test_admin_can_send_one_time_password_reset_link(self):
        admin = User.objects.create_superuser(username='resetadmin', email='admin@example.com', password='AdminSecret123')
        user = User.objects.create_user(username='resetmember', email='reset@example.com', password='OldSecret123')
        member = Member.objects.create(user=user, full_name='Reset Member', email=user.email, phone_number='+256700000007')
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.post(f'/api/admin/members/{member.id}/password-reset/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        reset_url = response.data['reset_url']
        query = reset_url.split('?', 1)[1].split('&')
        payload = {part.split('=', 1)[0]: part.split('=', 1)[1] for part in query}
        payload['password'] = 'NewSecret123'
        response = client.post('/api/auth/reset-password/', payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.get(pk=user.pk).check_password('NewSecret123'))
        response = client.post('/api/auth/reset-password/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_register_creates_member_that_needs_activation(self):
        payload = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'username': 'janedoe',
            'email': 'jane@example.com',
            'phone_number': '+256700000001',
            'date_of_birth': '2000-01-01',
            'gender': 'Female',
            'password': 'Secret123',
            'confirm_password': 'Secret123',
            'nin': 'CM123456789',
            'address': 'Kampala',
            'next_of_kin_name': 'John Doe',
            'next_of_kin_phone': '+256700000002',
        }

        user = RegisterSerializer().create(payload)

        self.assertFalse(user.member_profile.is_active)

    def test_login_allows_member_to_activate_account(self):
        user = User.objects.create_user(username='newmember', email='newmember@example.com', password='Secret123')
        Member.objects.create(
            user=user,
            full_name='New Member',
            email=user.email,
            phone_number='+256700000003',
            is_active=False,
        )

        serializer = LoginSerializer(data={'username': 'newmember', 'password': 'Secret123'})
        self.assertTrue(serializer.is_valid())

    def test_seed_data_resets_sample_login_password(self):
        call_command('seed_data')
        client = APIClient()
        response = client.post('/api/auth/login/', {'username': 'john', 'password': 'ChangeMe123!'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['username'], 'john')

    def test_login_is_throttled_after_repeated_attempts(self):
        cache.clear()
        client = APIClient()
        for attempt in range(5):
            response = client.post('/api/auth/login/', {'username': 'unknown', 'password': 'wrong-password'}, format='json', REMOTE_ADDR='198.51.100.42')
            self.assertEqual(response.status_code, 400, f'Attempt {attempt + 1} should be handled as an invalid login.')
        response = client.post('/api/auth/login/', {'username': 'unknown', 'password': 'wrong-password'}, format='json', REMOTE_ADDR='198.51.100.42')
        self.assertEqual(response.status_code, 429)

    @override_settings(PESAPAL_CONSUMER_KEY='test-consumer-key', PESAPAL_CONSUMER_SECRET='test-consumer-secret')
    @patch('savings.payment_views.urlopen')
    def test_pesapal_payment_start_returns_redirect_url(self, mock_urlopen):
        user = User.objects.create_user(username='pesapaluser', email='pesapal@example.com', password='Secret123')
        Member.objects.create(
            user=user,
            full_name='Pesapal User',
            email=user.email,
            phone_number='+256700000010',
            is_active=True,
        )

        token_response = Mock()
        token_response.read.return_value = b'{"token":"sample-token"}'
        redirect_response = Mock()
        redirect_response.read.return_value = b'{"redirect_url":"https://pay.pesapal.com/checkout/abc123"}'
        mock_urlopen.side_effect = [token_response, redirect_response]

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/payments/start/', {'provider': 'PesaPal', 'amount': '20000', 'purpose': 'savings', 'phone_number': '+256700000010'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertIn('https://pay.pesapal.com/checkout', response.data['redirect_url'])
        self.assertEqual(response.data['payment']['provider'], 'PesaPal')
        self.assertEqual(response.data['payment']['sacco_number'], '+256700000010')

    def test_provider_receipt_verifies_payment_route_and_updates_balances(self):
        user = User.objects.create_user(username='receiptuser', email='receipt@example.com', password='Secret123')
        member = Member.objects.create(
            user=user,
            full_name='Receipt User',
            email=user.email,
            phone_number='+256700000011',
            is_active=True,
        )
        loan = Loan.objects.create(member=member, loan_amount=Decimal('50000'), amount_paid=Decimal('25000'), status=Loan.Status.ACTIVE)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/payments/reconcile/', {
            'provider': 'PesaPal',
            'transaction_id': 'PESAPAL-RECEIPT-001',
            'amount': '25000',
            'purpose': 'loan_repayment',
            'route': 'loan_repayment',
            'member_id': member.id,
            'status': 'COMPLETED',
            'payment_time': timezone.now().isoformat(),
        }, format='json')

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get(transaction_id='PESAPAL-RECEIPT-001')
        self.assertEqual(payment.status, Payment.Status.VERIFIED)
        self.assertEqual(payment.purpose, Payment.Purpose.LOAN_REPAYMENT)
        self.assertTrue(payment.provider_verified)
        self.assertEqual(payment.source, Payment.Source.PROVIDER_API)
        loan.refresh_from_db()
        self.assertEqual(loan.amount_paid, Decimal('50000'))

    def test_member_cannot_reconcile_payment_for_another_member(self):
        user = User.objects.create_user(username='receiptowner', email='owner@example.com', password='Secret123')
        member = Member.objects.create(user=user, full_name='Receipt Owner', email=user.email, phone_number='+256700000012', is_active=True)
        other_member = Member.objects.create(full_name='Other Member', email='other@example.com', phone_number='+256700000013', is_active=True)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/payments/reconcile/', {
            'provider': 'PesaPal',
            'transaction_id': 'PESAPAL-OTHER-001',
            'amount': '25000',
            'purpose': 'savings',
            'member_id': other_member.id,
            'status': 'COMPLETED',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Payment.objects.get(transaction_id='PESAPAL-OTHER-001').member, member)

    def test_profile_upload_rejects_non_image_content(self):
        user = User.objects.create_user(username='uploaduser', email='upload@example.com', password='Secret123')
        Member.objects.create(user=user, full_name='Upload User', email=user.email, phone_number='+256700000014', is_active=True)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/profile/me/profile-picture/', {
            'profile_picture': SimpleUploadedFile('malware.svg', b'<script>alert(1)</script>', content_type='image/svg+xml'),
        }, format='multipart')

        self.assertEqual(response.status_code, 400)

    def test_loan_repayment_updates_outstanding_balance(self):
        member = Member.objects.create(
            full_name='Repay Member',
            email='repay@example.com',
            phone_number='+256700000004',
            is_active=True,
        )
        loan = Loan.objects.create(member=member, loan_amount=Decimal('100000'), amount_paid=Decimal('20000'), status=Loan.Status.ACTIVE)
        payment = Payment.objects.create(
            member=member,
            purpose=Payment.Purpose.LOAN_REPAYMENT,
            provider=Payment.Provider.MTN,
            internal_reference='PAY-LOAN-001',
            amount=Decimal('30000'),
            sacco_number='256700000001',
            status=Payment.Status.VERIFIED,
        )

        loan.amount_paid += payment.amount
        loan.save(update_fields=['amount_paid', 'outstanding_balance'])

        self.assertEqual(loan.amount_paid, Decimal('50000'))
        self.assertEqual(loan.outstanding_balance, Decimal('60000.00'))


class AdminMemberDirectoryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='directoryadmin', password='AdminSecret123')
        self.member_user = User.objects.create_user(username='directorymember', password='MemberSecret123')
        self.member = Member.objects.create(
            user=self.member_user,
            full_name='Directory Member',
            phone_number='+256700000008',
            email='directory@example.com',
            date_of_birth='2001-02-03',
            gender='Female',
            nin='NIN-123',
            address='Kampala',
            next_of_kin_name='Kin Member',
            next_of_kin_phone='+256700000009',
        )
        Savings.objects.create(member=self.member, amount=Decimal('125000'), payment_method=Savings.PaymentMethod.MTN, transaction_reference='DIRECTORY-SAV-001')
        Loan.objects.create(member=self.member, loan_amount=Decimal('200000'), amount_paid=Decimal('50000'), status=Loan.Status.ACTIVE)
        self.client = APIClient()

    def test_admin_member_list_and_detail_include_balances_without_password(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/admin/members/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['savings_balance'], Decimal('125000.00'))
        self.assertEqual(response.data[0]['loan_balance'], Decimal('170000.00'))
        response = self.client.get(f'/api/admin/members/{self.member.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nin'], 'NIN-123')
        self.assertEqual(len(response.data['loans']), 1)
        self.assertNotIn('password', response.data)

    def test_admin_can_add_manual_deposit_and_audit_balance_change(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/admin/members/{self.member.id}/deposit/', {'amount': '25000.50'}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['previous_balance'], Decimal('125000.00'))
        self.assertEqual(response.data['new_balance'], Decimal('150000.50'))
        saving = Savings.objects.get(transaction_reference=response.data['transaction_reference'])
        self.assertEqual(saving.payment_method, Savings.PaymentMethod.MANUAL)
        transaction = Transaction.objects.get(reference=response.data['transaction_reference'])
        self.assertEqual(transaction.description, 'Manual savings deposit')
        self.assertEqual(transaction.amount, Decimal('25000.50'))
        self.client.force_authenticate(user=self.member_user)
        transaction_response = self.client.get('/api/transactions/')
        self.assertEqual(transaction_response.status_code, 200)
        self.assertEqual(transaction_response.data[0]['reference'], transaction.reference)
        audit = AuditLog.objects.get(action='member_balance_updated', object_id=str(self.member.id))
        self.assertIn('deposited UGX 25,000.50', audit.description)
        self.assertIn('new balance UGX 150,000.50', audit.description)

    def test_admin_can_reverse_manual_deposit_and_audit_reversal(self):
        self.client.force_authenticate(user=self.admin)
        deposit_response = self.client.post(f'/api/admin/members/{self.member.id}/deposit/', {'amount': '25000.50'}, format='json')
        reference = deposit_response.data['transaction_reference']

        response = self.client.post(f'/api/admin/members/{self.member.id}/deposit/{reference}/reverse/', {}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['previous_balance'], Decimal('150000.50'))
        self.assertEqual(response.data['new_balance'], Decimal('125000.00'))
        self.assertEqual(Savings.objects.filter(member=self.member).aggregate(total=Sum('amount'))['total'], Decimal('125000.00'))
        reversal = Savings.objects.get(transaction_reference=response.data['transaction_reference'])
        self.assertEqual(reversal.amount, Decimal('-25000.50'))
        self.assertTrue(Transaction.objects.filter(reference=response.data['transaction_reference'], amount=Decimal('-25000.50')).exists())
        audit = AuditLog.objects.get(action='member_balance_reversed', object_id=str(self.member.id))
        self.assertEqual(audit.user, self.admin)
        self.assertIn(f'original reference {reference}', audit.description)
        audit_response = self.client.get('/api/admin/audit/')
        self.assertEqual(audit_response.status_code, 200)
        self.assertTrue(any(log['action'] == 'member_balance_reversed' for log in audit_response.data))

        repeat_response = self.client.post(f'/api/admin/members/{self.member.id}/deposit/{reference}/reverse/', {}, format='json')
        self.assertEqual(repeat_response.status_code, 409)

    def test_admin_withdrawal_requires_member_approval_before_balance_changes(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/admin/members/{self.member.id}/withdraw/', {'amount': '25000.50'}, format='json')

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['previous_balance'], Decimal('125000.00'))
        self.assertEqual(response.data['status'], WithdrawalRequest.Status.PENDING)
        self.assertEqual(Savings.objects.filter(member=self.member).aggregate(total=Sum('amount'))['total'], Decimal('125000.00'))
        self.assertFalse(Transaction.objects.filter(transaction_type=Transaction.TransactionType.WITHDRAWAL).exists())
        self.assertTrue(Notification.objects.filter(member=self.member, kind='Withdrawal approval').exists())
        request_id = response.data['id']

        self.client.force_authenticate(user=self.member_user)
        response = self.client.post(f'/api/withdrawals/{request_id}/respond/', {'action': 'approve'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], WithdrawalRequest.Status.APPROVED)
        self.assertEqual(response.data['new_balance'], Decimal('99999.50'))
        self.assertTrue(AuditLog.objects.filter(action='member_withdrawal_requested', object_id=str(request_id)).exists())
        withdrawal = Transaction.objects.get(reference=response.data['transaction_reference'])
        self.assertEqual(withdrawal.transaction_type, Transaction.TransactionType.WITHDRAWAL)
        self.assertEqual(withdrawal.amount, Decimal('-25000.50'))
        audit = AuditLog.objects.get(action='member_withdrawal_approved', object_id=str(request_id))
        self.assertIn('approved withdrawal of UGX 25,000.50', audit.description)

    def test_member_can_cancel_withdrawal_without_balance_change(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(f'/api/admin/members/{self.member.id}/withdraw/', {'amount': '25000'}, format='json')
        self.client.force_authenticate(user=self.member_user)

        response = self.client.post(f'/api/withdrawals/{created.data["id"]}/respond/', {'action': 'cancel'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], WithdrawalRequest.Status.CANCELLED)
        self.assertEqual(Savings.objects.filter(member=self.member).aggregate(total=Sum('amount'))['total'], Decimal('125000.00'))
        self.assertFalse(Transaction.objects.filter(transaction_type=Transaction.TransactionType.WITHDRAWAL).exists())
        self.assertTrue(AuditLog.objects.filter(action='member_withdrawal_cancelled', object_id=str(created.data['id'])).exists())

    def test_expired_withdrawal_is_logged_and_cannot_be_approved(self):
        self.client.force_authenticate(user=self.admin)
        created = self.client.post(f'/api/admin/members/{self.member.id}/withdraw/', {'amount': '25000'}, format='json')
        WithdrawalRequest.objects.filter(pk=created.data['id']).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.client.force_authenticate(user=self.member_user)

        response = self.client.get('/api/withdrawals/pending/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        approval_response = self.client.post(f'/api/withdrawals/{created.data["id"]}/respond/', {'action': 'approve'}, format='json')
        self.assertEqual(approval_response.status_code, 409)
        withdrawal_request = WithdrawalRequest.objects.get(pk=created.data['id'])
        self.assertEqual(withdrawal_request.status, WithdrawalRequest.Status.EXPIRED)
        self.assertTrue(AuditLog.objects.filter(action='member_withdrawal_expired', object_id=str(withdrawal_request.id)).exists())
        self.assertEqual(Savings.objects.filter(member=self.member).aggregate(total=Sum('amount'))['total'], Decimal('125000.00'))

    def test_expired_request_does_not_block_admin_from_requesting_again(self):
        self.client.force_authenticate(user=self.admin)
        first = self.client.post(f'/api/admin/members/{self.member.id}/withdraw/', {'amount': '25000'}, format='json')
        WithdrawalRequest.objects.filter(pk=first.data['id']).update(expires_at=timezone.now() - timedelta(seconds=1))

        second = self.client.post(f'/api/admin/members/{self.member.id}/withdraw/', {'amount': '15000'}, format='json')

        self.assertEqual(second.status_code, 202)
        self.assertEqual(WithdrawalRequest.objects.get(pk=first.data['id']).status, WithdrawalRequest.Status.EXPIRED)
        self.assertTrue(AuditLog.objects.filter(action='member_withdrawal_expired', object_id=str(first.data['id'])).exists())
        self.assertEqual(WithdrawalRequest.objects.get(pk=second.data['id']).status, WithdrawalRequest.Status.PENDING)
        self.assertEqual(Savings.objects.filter(member=self.member).aggregate(total=Sum('amount'))['total'], Decimal('125000.00'))

    def test_admin_cannot_withdraw_more_than_member_balance(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/admin/members/{self.member.id}/withdraw/', {'amount': '125000.01'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.filter(transaction_type=Transaction.TransactionType.WITHDRAWAL).exists())

    def test_member_detail_lists_manual_deposits_and_reversal_state(self):
        self.client.force_authenticate(user=self.admin)
        deposit_response = self.client.post(f'/api/admin/members/{self.member.id}/deposit/', {'amount': '25000'}, format='json')
        reference = deposit_response.data['transaction_reference']
        response = self.client.get(f'/api/admin/members/{self.member.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['manual_deposits'][0]['reference'], reference)
        self.assertFalse(response.data['manual_deposits'][0]['reversed'])

        self.client.post(f'/api/admin/members/{self.member.id}/deposit/{reference}/reverse/', {}, format='json')
        response = self.client.get(f'/api/admin/members/{self.member.id}/')
        self.assertTrue(response.data['manual_deposits'][0]['reversed'])

    def test_loan_request_is_logged_for_admin_notifications(self):
        self.client.force_authenticate(user=self.member_user)
        response = self.client.post('/api/loans/', {'loan_amount': '100000'}, format='json')

        self.assertEqual(response.status_code, 201)
        audit = AuditLog.objects.get(action='loan_application_submitted', object_type='Loan', object_id=str(response.data['id']))
        self.assertIn('Directory Member submitted a loan application', audit.description)

    def test_admin_can_force_pay_overdue_loan_from_savings(self):
        loan = Loan.objects.create(member=self.member, loan_amount=Decimal('100000'), amount_paid=Decimal('0'), status=Loan.Status.ACTIVE)
        Loan.objects.filter(pk=loan.pk).update(created_at=timezone.now() - timedelta(days=366))
        Savings.objects.create(member=self.member, amount=Decimal('200000'), payment_method=Savings.PaymentMethod.MTN, transaction_reference='FORCE-PAY-SAV-001')
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(f'/api/admin/loans/{loan.id}/force-pay/', {}, format='json')

        self.assertEqual(response.status_code, 201)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.COMPLETED)
        self.assertEqual(loan.outstanding_balance, Decimal('0.00'))
        self.assertEqual(Savings.objects.filter(member=self.member).aggregate(total=Sum('amount'))['total'], Decimal('215000.00'))
        self.assertTrue(AuditLog.objects.filter(action='loan_force_paid', object_id=str(loan.id)).exists())

    def test_member_cannot_access_admin_member_directory(self):
        self.client.force_authenticate(user=self.member_user)
        self.assertEqual(self.client.get('/api/admin/members/').status_code, 403)
