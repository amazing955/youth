from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0008_saccosettings_whatsapp_group_link')]

    operations = [migrations.CreateModel(
        name='SupportIssue',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(default='Support issue', max_length=180)),
            ('description', models.TextField()),
            ('status', models.CharField(choices=[('Open', 'Open'), ('Resolved', 'Resolved')], default='Open', max_length=20)),
            ('report', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('resolved_at', models.DateTimeField(blank=True, null=True)),
            ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_issues', to='accounts.member')),
            ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_support_issues', to=settings.AUTH_USER_MODEL)),
        ],
        options={'ordering': ['-created_at']},
    )]