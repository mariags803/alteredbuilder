# Generated by Django 5.0.7 on 2024-07-31 15:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0049_subtype_card_subtypes"),
    ]

    operations = [
        migrations.RenameField(
            model_name="card",
            old_name="echo_effect_temp",
            new_name="echo_effect",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="echo_effect_temp_de",
            new_name="echo_effect_de",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="echo_effect_temp_en",
            new_name="echo_effect_en",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="echo_effect_temp_es",
            new_name="echo_effect_es",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="echo_effect_temp_fr",
            new_name="echo_effect_fr",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="echo_effect_temp_it",
            new_name="echo_effect_it",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="main_effect_temp",
            new_name="main_effect",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="main_effect_temp_de",
            new_name="main_effect_de",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="main_effect_temp_en",
            new_name="main_effect_en",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="main_effect_temp_es",
            new_name="main_effect_es",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="main_effect_temp_fr",
            new_name="main_effect_fr",
        ),
        migrations.RenameField(
            model_name="card",
            old_name="main_effect_temp_it",
            new_name="main_effect_it",
        ),
    ]
