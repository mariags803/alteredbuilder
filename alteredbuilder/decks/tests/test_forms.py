import html

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from decks.forms import DecklistForm
from decks.models import Card, CardInDeck, Character, Deck, Hero
from .utils import generate_card, get_login_url


class DecksFormsTestCase(TestCase):
    """Test case focusing on the Forms."""

    USER_NAME = "test_user"
    DECK_NAME = "test deck"
    HERO_REFERENCE = "ALT_CORE_B_AX_01_C"
    CHARACTER_REFERENCE = "ALT_CORE_B_YZ_08_R2"

    @classmethod
    def setUpTestData(cls):
        """Create the database data for this test.

        Specifically, it creates:
        * 1 User
        * 1 Hero
        * 1 Character
        """
        cls.user = User.objects.create_user(username=cls.USER_NAME)

        Hero.objects.create(
            reference=cls.HERO_REFERENCE,
            name="Sierra & Oddball",
            faction=Card.Faction.AXIOM,
            type=Card.Type.HERO,
            rarity=Card.Rarity.COMMON,
        )
        Character.objects.create(
            reference=cls.CHARACTER_REFERENCE,
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

    def test_invalid_deck_only_name(self):
        """Validate a form creating a Deck only providing the name."""
        form_data = {"name": self.DECK_NAME}
        form = DecklistForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, "decklist", "This field is required.")

    def test_invalid_deck_only_decklist(self):
        """Validate a form creating a Deck only providing the decklist."""
        form_data = {"decklist": f"1 {self.HERO_REFERENCE}"}
        form = DecklistForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, "name", "This field is required.")

    def test_valid_deck_wrong_quantity(self):
        """Validate a form creating a Deck with an invalid amount of cards."""
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"4 {self.CHARACTER_REFERENCE}",
        }
        form = DecklistForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_deck(self):
        """Validate a valid form creating a Deck."""
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"1 {self.HERO_REFERENCE}\n3 {self.CHARACTER_REFERENCE}",
        }
        form = DecklistForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_valid_deck_unauthenticated(self):
        """Attempt to submit a form creating a Deck while unauthenticated."""
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"1 {self.HERO_REFERENCE}\n3 {self.CHARACTER_REFERENCE}",
        }

        response = self.client.post(reverse("new-deck"), form_data)
        self.assertRedirects(response, get_login_url("new-deck"), status_code=302)

    def test_valid_deck_authenticated(self):
        """Attempt to submit a form creating a valid Deck."""
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"1 {self.HERO_REFERENCE}\n3 {self.CHARACTER_REFERENCE}",
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("new-deck"), form_data)

        new_deck = Deck.objects.filter(owner=self.user).get()
        hero = Hero.objects.get(reference=self.HERO_REFERENCE)
        character = Character.objects.get(reference=self.CHARACTER_REFERENCE)
        deck_cards = new_deck.cardindeck_set.all()

        self.assertRedirects(
            response, reverse("deck-detail", kwargs={"pk": new_deck.id})
        )
        self.assertFalse(new_deck.is_public)
        self.assertEqual(new_deck.hero, hero)
        self.assertEqual(len(deck_cards), 1)
        self.assertEqual(deck_cards[0].quantity, 3)
        self.assertEqual(deck_cards[0].card.character, character)

    def test_invalid_deck_wrong_reference(self):
        """Attempt to submit a form creating a Deck with an invalid reference to a
        card.
        """
        wrong_card_reference = "wrong_card_reference"
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"1 {self.HERO_REFERENCE}\n3 {wrong_card_reference}",
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("new-deck"), form_data)
        self.assertContains(
            response, html.escape(f"Card '{wrong_card_reference}' does not exist")
        )

    def test_invalid_deck_multiple_heroes(self):
        """Attempt to submit a form creating a Deck that contains multiple heroes."""
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"1 {self.HERO_REFERENCE}\n1 {self.HERO_REFERENCE}",
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("new-deck"), form_data)
        self.assertContains(response, "Multiple heroes present in the decklist")

    def test_invalid_deck_wrong_format(self):
        """Attempt to submit a form creating a Deck with an incorrect format.
        This is useful as the DecklistForm only checks that at least one line respects
        the format.
        """
        wrong_format_line = "NOT_THE_RIGHT_FORMAT"
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"1 {self.HERO_REFERENCE}\n{wrong_format_line}",
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("new-deck"), form_data)
        self.assertContains(
            response, html.escape(f"Failed to unpack '{wrong_format_line}'")
        )

    def test_valid_deck_missing_hero(self):
        """Submit a form creating a Deck without a hero reference."""
        form_data = {
            "name": self.DECK_NAME,
            "decklist": f"3 {self.CHARACTER_REFERENCE}",
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("new-deck"), form_data)

        new_deck = Deck.objects.filter(owner=self.user).get()
        character = Character.objects.get(reference=self.CHARACTER_REFERENCE)
        deck_cards = new_deck.cardindeck_set.all()

        self.assertRedirects(
            response, reverse("deck-detail", kwargs={"pk": new_deck.id})
        )
        self.assertFalse(new_deck.is_public)
        self.assertEqual(new_deck.hero, None)
        self.assertEqual(len(deck_cards), 1)
        self.assertEqual(deck_cards[0].quantity, 3)
        self.assertEqual(deck_cards[0].card.character, character)

    def test_update_deck_add_existing_card(self):
        hero = Hero.objects.get(reference=self.HERO_REFERENCE)
        character = Character.objects.get(reference=self.CHARACTER_REFERENCE)
        deck = Deck.objects.create(owner=self.user, name=self.DECK_NAME, hero=hero)
        CardInDeck.objects.create(deck=deck, card=character, quantity=1)

        form_data = {
            "deck_id": deck.id,
            "card_reference": character.reference,
            "quantity": 2,
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("update-deck"), form_data)
        cid = CardInDeck.objects.filter(deck=deck, card=character).get()

        self.assertEqual(cid.quantity, 3)
        self.assertRedirects(response, reverse("cards"))

    def test_update_deck_add_nonexisting_card(self):
        hero = Hero.objects.get(reference=self.HERO_REFERENCE)
        character = generate_card(
            Card.Faction.AXIOM, Card.Type.CHARACTER, Card.Rarity.RARE
        )
        deck = Deck.objects.create(owner=self.user, name=self.DECK_NAME, hero=hero)

        form_data = {
            "deck_id": deck.id,
            "card_reference": character.reference,
            "quantity": 2,
        }

        self.client.force_login(self.user)
        response = self.client.post(reverse("update-deck"), form_data)
        cid = CardInDeck.objects.filter(deck=deck, card=character).get()

        self.assertEqual(cid.quantity, 2)
        self.assertRedirects(response, reverse("cards"))
