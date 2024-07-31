# Generated by Django 5.0.7 on 2024-07-31 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0045_remove_character_echo_effect_de_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TempDeck",
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
                ("owner_id", models.IntegerField()),
                ("name", models.CharField(max_length=50)),
                ("description", models.TextField(blank=True, max_length=2500)),
                ("hero_id", models.CharField(max_length=32, null=True)),
                ("is_public", models.BooleanField(default=False)),
                ("is_standard_legal", models.BooleanField(null=True)),
                (
                    "standard_legality_errors",
                    models.JSONField(blank=True, default=list),
                ),
                ("is_draft_legal", models.BooleanField(null=True)),
                ("draft_legality_errors", models.JSONField(blank=True, default=list)),
                ("is_exalts_legal", models.BooleanField(null=True)),
                ("love_count", models.PositiveIntegerField(default=0)),
                ("comment_count", models.PositiveIntegerField(default=0)),
                ("modified_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
