from django.contrib.auth.models import User
from django.test import TestCase

from decks.models import Card, Character, Deck, Hero, Landmark, Spell


class DecksViewsTestCase(TestCase):
    TEST_USER = "test_user"
    HERO_REFERENCE = "ALT_CORE_B_AX_01_C"
    PROMO_HERO_REFERENCE = "ALT_CORE_P_AX_01_C"
    CHARACTER_REFERENCE = "ALT_CORE_B_YZ_08_C"
    OOF_CHARACTER_REFERENCE = "ALT_CORE_B_YZ_08_R2"
    SPELL_REFERENCE = "ALT_CORE_B_YZ_26_R2"
    LANDMARK_REFERENCE = "ALT_CORE_B_LY_30_R2"
    DECK_NAME = "deck name"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=cls.TEST_USER)
        hero = Hero.objects.create(
            reference=cls.HERO_REFERENCE,
            name="Sierra & Oddball",
            faction=Card.Faction.AXIOM,
            type=Card.Type.HERO,
            rarity=Card.Rarity.COMMON,
        )
        Hero.objects.create(
            reference=cls.PROMO_HERO_REFERENCE,
            name="Sierra & Oddball",
            faction=Card.Faction.AXIOM,
            type=Card.Type.HERO,
            rarity=Card.Rarity.COMMON,
        )
        Character.objects.create(
            reference=cls.CHARACTER_REFERENCE,
            name="Yzmir Stargazer",
            faction=Card.Faction.YZMIR,
            type=Card.Type.CHARACTER,
            rarity=Card.Rarity.COMMON,
            main_cost=2,
            recall_cost=1,
            forest_power=1,
            mountain_power=2,
            ocean_power=1,
        )
        Character.objects.create(
            reference=cls.OOF_CHARACTER_REFERENCE,
            name="Yzmir Stargazer",
            faction=Card.Faction.AXIOM,
            type=Card.Type.CHARACTER,
            rarity=Card.Rarity.RARE,
            main_cost=1,
            recall_cost=1,
            forest_power=1,
            mountain_power=2,
            ocean_power=1,
        )
        Spell.objects.create(
            reference=cls.SPELL_REFERENCE,
            name="Kraken's Wrath",
            faction=Card.Faction.AXIOM,
            type=Card.Type.SPELL,
            rarity=Card.Rarity.RARE,
            main_cost=5,
            recall_cost=5,
        )
        Landmark.objects.create(
            reference=cls.LANDMARK_REFERENCE,
            name="The Ouroboros, Lyra Bastion",
            faction=Card.Faction.AXIOM,
            type=Card.Type.LANDMARK,
            rarity=Card.Rarity.RARE,
            main_cost=3,
            recall_cost=3,
        )
        Deck.objects.create(
            owner=cls.user, name=cls.DECK_NAME, hero=hero, is_public=True
        )

    def test_to_string(self):
        hero = Hero.objects.get(reference=self.HERO_REFERENCE)
        character = Character.objects.get(reference=self.CHARACTER_REFERENCE)
        spell = Spell.objects.get(reference=self.SPELL_REFERENCE)
        landmark = Landmark.objects.get(reference=self.LANDMARK_REFERENCE)
        deck = Deck.objects.get(name=self.DECK_NAME)

        self.assertEqual(str(hero), f"{hero.reference} - {hero.name}")
        self.assertEqual(
            str(character),
            f"[{character.faction}] - {character.name} ({character.rarity})",
        )
        self.assertEqual(
            str(spell), f"[{spell.faction}] - {spell.name} ({spell.rarity})"
        )
        self.assertEqual(
            str(landmark), f"[{landmark.faction}] - {landmark.name} ({landmark.rarity})"
        )
        self.assertEqual(str(deck), f"{deck.owner.username} - {deck.name}")

    def test_hero_promo(self):
        hero = Hero.objects.get(reference=self.HERO_REFERENCE)
        promo_hero = Hero.objects.get(reference=self.PROMO_HERO_REFERENCE)

        self.assertFalse(hero.is_promo())
        self.assertTrue(promo_hero.is_promo())

    def test_character_oof(self):
        character = Character.objects.get(reference=self.CHARACTER_REFERENCE)
        oof_character = Character.objects.get(reference=self.OOF_CHARACTER_REFERENCE)

        self.assertFalse(character.is_oof())
        self.assertTrue(oof_character.is_oof())