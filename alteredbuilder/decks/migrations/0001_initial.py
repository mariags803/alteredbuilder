# Generated by Django 5.0.3 on 2024-03-06 15:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Card",
            fields=[
                (
                    "reference",
                    models.CharField(max_length=24, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=32)),
                (
                    "faction",
                    models.CharField(
                        choices=[
                            ("AX", "axiom"),
                            ("BR", "bravos"),
                            ("LY", "lyra"),
                            ("MU", "muna"),
                            ("OR", "ordis"),
                            ("YZ", "yzmir"),
                        ],
                        max_length=2,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("spell", "Spell"),
                            ("permanent", "Permanent"),
                            ("token", "Token"),
                            ("character", "Character"),
                            ("hero", "Hero"),
                            ("mana", "Mana"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "rarity",
                    models.CharField(
                        choices=[("C", "common"), ("R", "rare"), ("U", "unique")],
                        max_length=1,
                    ),
                ),
                ("image_url", models.URLField(blank=True)),
            ],
            options={
                "ordering": ["reference"],
            },
        ),
        migrations.CreateModel(
            name="Character",
            fields=[
                (
                    "card_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="decks.card",
                    ),
                ),
                ("main_cost", models.SmallIntegerField()),
                ("recall_cost", models.SmallIntegerField()),
                ("main_effect", models.TextField(blank=True)),
                ("echo_effect", models.TextField(blank=True)),
                ("forest_power", models.SmallIntegerField()),
                ("mountain_power", models.SmallIntegerField()),
                ("ocean_power", models.SmallIntegerField()),
            ],
            options={
                "abstract": False,
            },
            bases=("decks.card",),
        ),
        migrations.CreateModel(
            name="Hero",
            fields=[
                (
                    "card_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="decks.card",
                    ),
                ),
                ("reserve_count", models.SmallIntegerField(default=2)),
                ("permanent_count", models.SmallIntegerField(default=2)),
                ("main_effect", models.TextField(blank=True)),
            ],
            bases=("decks.card",),
        ),
        migrations.CreateModel(
            name="Permanent",
            fields=[
                (
                    "card_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="decks.card",
                    ),
                ),
                ("main_cost", models.SmallIntegerField()),
                ("recall_cost", models.SmallIntegerField()),
                ("main_effect", models.TextField(blank=True)),
                ("echo_effect", models.TextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
            bases=("decks.card",),
        ),
        migrations.CreateModel(
            name="Spell",
            fields=[
                (
                    "card_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="decks.card",
                    ),
                ),
                ("main_cost", models.SmallIntegerField()),
                ("recall_cost", models.SmallIntegerField()),
                ("main_effect", models.TextField(blank=True)),
                ("echo_effect", models.TextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
            bases=("decks.card",),
        ),
        migrations.CreateModel(
            name="CardInDeck",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.SmallIntegerField(default=1)),
                (
                    "card",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="decks.card"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Deck",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                (
                    "cards",
                    models.ManyToManyField(
                        related_name="decks",
                        through="decks.CardInDeck",
                        to="decks.card",
                    ),
                ),
                (
                    "hero",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="decks.hero",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="cardindeck",
            name="deck",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="decks.deck"
            ),
        ),
    ]
