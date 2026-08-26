import decimal
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0001_initial')]
    operations = [migrations.CreateModel(name='Loan', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('loan_amount', models.DecimalField(decimal_places=2, max_digits=14)),
        ('amount_paid', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=14)),
        ('outstanding_balance', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=14)),
        ('status', models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Active', 'Active'), ('Completed', 'Completed'), ('Rejected', 'Rejected')], default='Pending', max_length=20)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to='accounts.member')),
    ], options={'ordering': ['-created_at']})]
