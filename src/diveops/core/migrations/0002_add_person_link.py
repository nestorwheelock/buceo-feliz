# Add person link to User model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("django_parties", "0004_add_lead_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="person",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="user_account",
                to="django_parties.person",
            ),
        ),
    ]
