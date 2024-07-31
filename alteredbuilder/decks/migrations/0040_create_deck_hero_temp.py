# Generated by Django 5.0.7 on 2024-07-30 11:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0039_refactor_card_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="deck",
            name="hero_temp",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="hero_temp",
                to="decks.card",
            ),
        ),
    ]