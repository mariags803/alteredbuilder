# Generated by Django 5.0.7 on 2024-07-30 10:24

from django.conf import settings
from django.db import migrations, models
from django.utils.translation import activate


def init_models(apps):
    global Card, Set
    Card = apps.get_model("decks", "Card")
    Set = apps.get_model("decks", "Set")


def refactor_cards(apps, schema_editor):
    init_models(apps)

    for card in Card.objects.all():
        match card.type:
            case "HERO":
                refactor_hero(card)
            case "SPELL":
                refactor_spell(card)
            case "PERMANENT":
                refactor_permanent(card)
            case "CHARACTER":
                refactor_character(card)
            case _:
                print(f"un-typed card found: {card}")


def refactor_hero(card):
    card.stats = {
        "reserve_count": card.hero.reserve_count,
        "permanent_count": card.hero.permanent_count,
    }
    for language, _ in settings.LANGUAGES:
        activate(language)
        card.main_effect_temp = card.hero.main_effect
    card.save()


def refactor_spell(card):
    card.stats = {
        "main_cost": card.spell.main_cost,
        "recall_cost": card.spell.recall_cost,
    }
    for language, _ in settings.LANGUAGES:
        activate(language)
        card.main_effect_temp = card.spell.main_effect
        card.echo_effect_temp = card.spell.echo_effect
    card.save()


def refactor_permanent(card):
    card.stats = {
        "main_cost": card.permanent.main_cost,
        "recall_cost": card.permanent.recall_cost,
    }
    for language, _ in settings.LANGUAGES:
        activate(language)
        card.main_effect_temp = card.permanent.main_effect
        card.echo_effect_temp = card.permanent.echo_effect
    card.save()


def refactor_character(card):
    card.stats = {
        "main_cost": card.character.main_cost,
        "recall_cost": card.character.recall_cost,
        "forest_power": card.character.forest_power,
        "mountain_power": card.character.mountain_power,
        "ocean_power": card.character.ocean_power,
    }
    for language, _ in settings.LANGUAGES:
        activate(language)
        card.main_effect_temp = card.character.main_effect
        card.echo_effect_temp = card.character.echo_effect
    card.save()


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0037_commentvote"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="echo_effect_temp",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="card",
            name="echo_effect_temp_de",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="echo_effect_temp_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="echo_effect_temp_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="echo_effect_temp_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="echo_effect_temp_it",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="main_effect_temp",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="card",
            name="main_effect_temp_de",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="main_effect_temp_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="main_effect_temp_es",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="main_effect_temp_fr",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="main_effect_temp_it",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="stats",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(refactor_cards),
    ]