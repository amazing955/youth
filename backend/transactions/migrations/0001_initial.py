import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0001_initial')]
    operations = [migrations.CreateModel(name='Transaction', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('transaction_type', models.CharField(choices=[('Savings', 'Savings'), ('Loan', 'Loan'), ('Loan Repayment', 'Loan Repayment'), ('Withdrawal', 'Withdrawal'), ('Transfer', 'Transfer')], max_length=30)),
        ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
        ('payment_method', models.CharField(blank=True, max_length=30)),
        ('description', models.CharField(max_length=255)),
        ('reference', models.CharField(max_length=100, unique=True)),
        ('status', models.CharField(choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed')], default='Completed', max_length=20)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='accounts.member')),
    ], options={'ordering': ['-created_at']})]
