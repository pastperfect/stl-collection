# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0003_remove_tag_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='tagtype',
            name='show_in_gallery',
            field=models.BooleanField(default=True, help_text='Show this tag type in the Collection Gallery filters'),
        ),
    ]
