# Generated by Django 5.0.3 on 2024-03-14 15:47

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0005_deck_is_public"),
    ]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="deck",
            name="modified_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
