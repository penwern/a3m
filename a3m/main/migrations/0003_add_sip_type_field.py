# Generated by Django 4.2.16 on 2025-04-29 09:38

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0002_initial_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="sip",
            name="sip_type",
            field=models.CharField(
                choices=[("SIP", "SIP"), ("DIP", "DIP")], default="SIP", max_length=8
            ),
        ),
    ]
