from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0010_adminloginotp')]

    operations = [migrations.CreateModel(
        name='FinancialGoal',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=150)),
            ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
            ('achieved_at', models.DateTimeField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='financial_goals', to='accounts.member')),
        ],
        options={'ordering': ['-created_at']},
    )]