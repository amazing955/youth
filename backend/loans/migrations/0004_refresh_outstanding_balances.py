from decimal import Decimal

from django.db import migrations


def refresh_outstanding_balances(apps, schema_editor):
    Loan = apps.get_model('loans', 'Loan')
    for loan in Loan.objects.all().iterator():
        interest = (loan.loan_amount * loan.interest_rate / Decimal('100')).quantize(Decimal('0.01'))
        loan.outstanding_balance = max(loan.loan_amount + interest - loan.amount_paid, Decimal('0'))
        loan.save(update_fields=['outstanding_balance'])


class Migration(migrations.Migration):
    dependencies = [('loans', '0003_loan_interest_rate')]

    operations = [migrations.RunPython(refresh_outstanding_balances, migrations.RunPython.noop)]