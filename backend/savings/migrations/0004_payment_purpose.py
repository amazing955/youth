from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('savings', '0003_alter_payment_transaction_id')]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='purpose',
            field=models.CharField(choices=[('savings', 'Savings'), ('account_activation', 'Account activation'), ('loan_repayment', 'Loan repayment')], default='savings', max_length=30),
        ),
    ]
