from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0009_supportissue')]

    operations = [migrations.CreateModel(
        name='AdminLoginOTP',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('code_hash', models.CharField(max_length=128)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('expires_at', models.DateTimeField()),
            ('attempts', models.PositiveSmallIntegerField(default=0)),
            ('verified_at', models.DateTimeField(blank=True, null=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_login_otps', to=settings.AUTH_USER_MODEL)),
        ],
    )]