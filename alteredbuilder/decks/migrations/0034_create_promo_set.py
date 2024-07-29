# Generated by Django 5.0.3 on 2024-07-24 23:58

from django.db import migrations


def init_models(apps):
    global Card, Set
    Card = apps.get_model("decks", "Card")
    Set = apps.get_model("decks", "Set")


def create_promo_set(apps, schema_editor):
    init_models(apps)

    Set.objects.update_or_create(
        name="Promo",
        short_name="BTG-P",
        code="COREP",
        reference_code="_CORE_P_",
    )


def link_cards_to_sets(apps, schema_editor):

    card_set = Set.objects.get(code="COREP")

    Card.objects.filter(reference__contains=card_set.reference_code).update(
        set=card_set
    )


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0033_alter_deck_description"),
    ]

    operations = [
        migrations.RunPython(create_promo_set),
        migrations.RunPython(link_cards_to_sets),
    ]