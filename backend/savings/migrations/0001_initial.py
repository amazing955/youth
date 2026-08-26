import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0001_initial')]
    operations = [migrations.CreateModel(name='Savings', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
        ('payment_method', models.CharField(choices=[('MTN Mobile Money', 'MTN Mobile Money'), ('Airtel Money', 'Airtel Money')], max_length=30)),
        ('transaction_reference', models.CharField(max_length=100, unique=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='savings', to='accounts.member')),
    ], options={'ordering': ['-created_at']})]
