import django.conf
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='member_profile', to=django.conf.settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(model_name='member', name='date_of_birth', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='member', name='gender', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='member', name='nin', field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name='member', name='address', field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name='member', name='next_of_kin_name', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='member', name='next_of_kin_phone', field=models.CharField(blank=True, max_length=30)),
    ]