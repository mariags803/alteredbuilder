# Generated by Django 5.0.3 on 2024-03-04 16:32
from urllib import request
import json
import math

from django.db import migrations

from decks.models import Card

API_URL = "https://api.altered.gg/cards"
ITEMS_PER_PAGE = 36
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Origin": "https://www.altered.gg",
}


def extract_card(card):
    card_object = {
        "reference": card["reference"],
        "name": card["name"],
        "faction": card["mainFaction"]["reference"],
        "type": card["cardType"]["reference"],
        "rarity": card["rarity"]["reference"],
        "image_url": card["imagePath"],
    }
    if "MAIN_EFFECT" in card["elements"]:
        card_object["main_effect"] = card["elements"]["MAIN_EFFECT"]

    if card_object["type"] == "PERMANENT":
        card_object["type"] = "LANDMARK"

    if card_object["type"] == "HERO":
        try:
            card_object.update(
                {
                    "reserve_count": card["elements"]["RESERVE"],
                    "landmark_count": card["elements"]["PERMANENT"],
                }
            )
        except KeyError:
            card_object.update({"reserve_count": 2, "landmark_count": 2})

    else:
        if card_object["type"] == "TOKEN":
            card_object.update({"main_cost": 0, "recall_cost": 0})
        else:
            card_object.update(
                {
                    "main_cost": card["elements"]["MAIN_COST"],
                    "recall_cost": card["elements"]["RECALL_COST"],
                }
            )

        if "ECHO_EFFECT" in card["elements"]:
            card_object["echo_effect"] = card["elements"]["ECHO_EFFECT"]
        if card_object["type"] == "CHARACTER":
            card_object.update(
                {
                    "forest_power": card["elements"]["FOREST_POWER"],
                    "mountain_power": card["elements"]["MOUNTAIN_POWER"],
                    "ocean_power": card["elements"]["OCEAN_POWER"],
                }
            )
    return card_object


def convert_choices(card_object):
    card_object["faction"] = Card.Faction(card_object["faction"])
    card_object["type"] = getattr(Card.Type, card_object["type"])
    card_object["rarity"] = getattr(Card.Rarity, card_object["rarity"])


def import_cards(apps, schema_editor):
    Hero = apps.get_model("decks", "Hero")
    Character = apps.get_model("decks", "Character")
    Spell = apps.get_model("decks", "Spell")
    Landmark = apps.get_model("decks", "Landmark")

    page_index = 1
    page_count = math.inf
    total_items = math.inf

    while page_index <= page_count:
        params = f"?page={page_index}&itemsPerPage={ITEMS_PER_PAGE}"
        req = request.Request(API_URL + params, headers=headers)
        with request.urlopen(req) as response:
            page = response.read()
            data = json.loads(page.decode("utf8"))

        total_items = min(data["hydra:totalItems"], total_items)
        page_count = min(math.ceil(total_items / ITEMS_PER_PAGE), page_count)

        for card in data["hydra:member"]:
            try:
                card_object = extract_card(card)
            except KeyError:
                print(card)
                raise

            convert_choices(card_object)

            match card_object["type"]:
                case Card.Type.HERO:
                    Hero.objects.create(**card_object)
                case Card.Type.CHARACTER:
                    Character.objects.create(**card_object)
                case Card.Type.SPELL:
                    Spell.objects.create(**card_object)
                case Card.Type.LANDMARK:
                    Landmark.objects.create(**card_object)
                case Card.Type.TOKEN | Card.Type.MANA:
                    continue
                case _:
                    continue

        page_index += 1


class Migration(migrations.Migration):

    dependencies = [
        ("decks", "0001_initial"),
    ]

    operations = [migrations.RunPython(import_cards)]
