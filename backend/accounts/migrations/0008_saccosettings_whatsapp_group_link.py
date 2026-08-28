from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0007_notification')]

    operations = [
        migrations.AddField(
            model_name='saccosettings',
            name='whatsapp_group_link',
            field=models.URLField(blank=True, default=''),
        ),
    ]