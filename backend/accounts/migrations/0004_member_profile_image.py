from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_auditlog_saccosettings')]
    operations = [migrations.AlterField(
        model_name='member',
        name='profile_image',
        field=models.ImageField(blank=True, null=True, upload_to='profile_pictures/'),
    )]