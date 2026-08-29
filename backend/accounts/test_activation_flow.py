from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.auth_serializers import LoginSerializer, RegisterSerializer
from accounts.models import Member, Notification
from accounts.notification_utils import notify_member
from loans.models import Loan
from savings.models import Savings
from savings.payment_models import Payment

User = get_user_model()


class ActivationFlowTests(TestCase):
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

    def test_login_is_throttled_after_repeated_attempts(self):
        cache.clear()
        client = APIClient()
        for attempt in range(5):
            response = client.post('/api/auth/login/', {'username': 'unknown', 'password': 'wrong-password'}, format='json', REMOTE_ADDR='198.51.100.42')
            self.assertEqual(response.status_code, 400, f'Attempt {attempt + 1} should be handled as an invalid login.')
        response = client.post('/api/auth/login/', {'username': 'unknown', 'password': 'wrong-password'}, format='json', REMOTE_ADDR='198.51.100.42')
        self.assertEqual(response.status_code, 429)

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
        self.assertEqual(loan.outstanding_balance, Decimal('50000'))


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
        self.assertEqual(response.data[0]['loan_balance'], Decimal('150000.00'))
        response = self.client.get(f'/api/admin/members/{self.member.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nin'], 'NIN-123')
        self.assertEqual(len(response.data['loans']), 1)
        self.assertNotIn('password', response.data)

    def test_member_cannot_access_admin_member_directory(self):
        self.client.force_authenticate(user=self.member_user)
        self.assertEqual(self.client.get('/api/admin/members/').status_code, 403)
