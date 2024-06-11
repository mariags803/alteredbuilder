# Generated by Django 5.0.3 on 2024-06-02 18:16

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0018_deck_love_count_alter_cardindeck_quantity_lovepoint"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name="deck",
            index=models.Index(
                fields=["-modified_at"], name="decks_deck_modifie_f6692c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="deck",
            index=models.Index(
                fields=["is_public"], name="decks_deck_is_publ_71586c_idx"
            ),
        ),
    ]