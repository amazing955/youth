from decimal import Decimal
from uuid import UUID
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Member
from loans.models import Loan
from savings.models import Savings
from transactions.models import Transaction


class Command(BaseCommand):
    help = 'Create sample Youth Saving SACCO data.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(username='john', defaults={'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@example.com'})
        if not user.has_usable_password():
            user.set_password('ChangeMe123!')
            user.save(update_fields=['password'])
        member, _ = Member.objects.update_or_create(
            id=UUID('00000000-0000-0000-0000-000000000001'),
            defaults={
                'user': user,
                'full_name': 'John Doe',
                'phone_number': '+256 700 123 456',
                'email': 'john.doe@example.com',
                'is_active': True,
            },
        )
        Savings.objects.filter(member=member).delete()
        Loan.objects.filter(member=member).delete()
        Transaction.objects.filter(member=member).delete()

        Savings.objects.bulk_create([
            Savings(member=member, amount=Decimal('1000000'), payment_method=Savings.PaymentMethod.MTN, transaction_reference='SAV-001'),
            Savings(member=member, amount=Decimal('950000'), payment_method=Savings.PaymentMethod.AIRTEL, transaction_reference='SAV-002'),
            Savings(member=member, amount=Decimal('500000'), payment_method=Savings.PaymentMethod.MTN, transaction_reference='SAV-003'),
        ])
        from accounts.models import SACCOSettings
        SACCOSettings.objects.get_or_create(id=1, defaults={'sacco_name': 'Youth Saving', 'mtn_number': '0700000000', 'airtel_number': '0750000000'})
        Loan.objects.create(member=member, loan_amount=Decimal('1500000'), amount_paid=Decimal('650000'), status=Loan.Status.ACTIVE)
        Transaction.objects.bulk_create([
            Transaction(member=member, transaction_type=Transaction.TransactionType.SAVINGS, amount=Decimal('100000'), payment_method='MTN Mobile Money', description='Savings Deposit', reference='TXN-001'),
            Transaction(member=member, transaction_type=Transaction.TransactionType.LOAN_REPAYMENT, amount=Decimal('-50000'), payment_method='Airtel Money', description='Loan Repayment', reference='TXN-002'),
            Transaction(member=member, transaction_type=Transaction.TransactionType.SAVINGS, amount=Decimal('200000'), payment_method='MTN Mobile Money', description='Savings Deposit', reference='TXN-003'),
            Transaction(member=member, transaction_type=Transaction.TransactionType.SAVINGS, amount=Decimal('50000'), payment_method='Airtel Money', description='Membership Contribution', reference='TXN-004'),
        ])
        self.stdout.write(self.style.SUCCESS(f'Seeded SACCO data for {member.full_name} (id={member.id}).'))
