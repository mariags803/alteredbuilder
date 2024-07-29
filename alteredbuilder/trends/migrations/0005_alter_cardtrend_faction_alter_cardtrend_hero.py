# Generated by Django 5.0.7 on 2024-07-26 07:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0034_create_promo_set"),
        ("trends", "0004_remove_cardtrend_count_cardtrend_hero"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cardtrend",
            name="faction",
            field=models.CharField(
                blank=True,
                choices=[
                    ("AX", "axiom"),
                    ("BR", "bravos"),
                    ("LY", "lyra"),
                    ("MU", "muna"),
                    ("OR", "ordis"),
                    ("YZ", "yzmir"),
                ],
                max_length=2,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="cardtrend",
            name="hero",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hero_trend",
                to="decks.card",
            ),
        ),
    ]