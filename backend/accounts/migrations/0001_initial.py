import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=150)),
                ('phone_number', models.CharField(max_length=30)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('profile_image', models.FileField(blank=True, null=True, upload_to='member-profiles/')),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['full_name']},
        ),
    ]
