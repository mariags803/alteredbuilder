from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import serializers

from . import serializers as serial
from decks.models import Card, Character, Hero, Permanent, Spell


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited by admins
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = serial.UserSerializer
    permission_classes = [permissions.IsAdminUser]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited by admins
    """

    queryset = Group.objects.all()
    serializer_class = serial.GroupSerializer
    permission_classes = [permissions.IsAdminUser]


class CardViewSet(viewsets.ModelViewSet):
    """API endpoint that allows to view all the cards.
    It's a bit tricky because of the model hierarchy defined.
    """

    queryset = Card.objects.all().order_by("reference")
    serializer_class = serial.CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request: Request, pk=None) -> Response:
        """Retrieve the information of a card.
        All `Card` models should have a 1-1 relationship with their card type, which is
        more interesting to return.

        Args:
            request (Request): Request object.
            pk (str, optional): Primary key of the object to retrieve. Defaults to None.

        Returns:
            Response: The Card's full data.
        """
        card = get_object_or_404(Card, pk=pk)
        context = {"request": request}
        model, serializer = self.get_serializer_from_type(card.type)
        card = get_object_or_404(model, pk=pk)
        serializer = serializer(card, context=context)

        return Response(serializer.data)

    @staticmethod
    def get_serializer_from_type(
        card_type: Card.Type,
    ) -> tuple[Card, serializers.HyperlinkedModelSerializer]:
        """Return a card's model and serializer according to their type.

        Args:
            card_type (Card.Type): The Card's type.

        Returns:
            tuple[Card, serializers.HyperlinkedModelSerializer]: The detailed model and
                its serializer.
        """
        match card_type:
            case Card.Type.CHARACTER:
                return Character, serial.CharacterSerializer
            case Card.Type.HERO:
                return Hero, serial.HeroSerializer
            case Card.Type.PERMANENT:
                return Permanent, serial.PermanentSerializer
            case Card.Type.SPELL:
                return Spell, serial.SpellSerializer
            case _:
                return Card, serial.CardSerializer


class CharacterViewSet(viewsets.ModelViewSet):
    queryset = Character.objects.all().order_by("reference")
    serializer_class = serial.CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]


class HeroViewSet(viewsets.ModelViewSet):
    queryset = Hero.objects.all().order_by("reference")
    serializer_class = serial.HeroSerializer
    permission_classes = [permissions.IsAuthenticated]


class PermanentViewSet(viewsets.ModelViewSet):
    queryset = Permanent.objects.all().order_by("reference")
    serializer_class = serial.PermanentSerializer
    permission_classes = [permissions.IsAuthenticated]


class SpellViewSet(viewsets.ModelViewSet):
    queryset = Spell.objects.all().order_by("reference")
    serializer_class = serial.SpellSerializer
    permission_classes = [permissions.IsAuthenticated]
