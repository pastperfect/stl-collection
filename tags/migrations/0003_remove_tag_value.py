# Generated manually
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0002_tag_reference_tag_tag_value_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tag',
            name='value',
        ),
    ]
