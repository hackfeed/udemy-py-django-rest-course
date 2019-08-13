from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse("recipe:ingredient-list")


class PubliceIngredientsAPITests(TestCase):
    """ Test the publicly available ingredients API. """

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """ Test that login is required to access the endpoint. """
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsAPITests(TestCase):
    """ Test the private ingredients API. """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@hackfeed.com",
            "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        """ Test retrieving a list of ingredients. """
        Ingredient.objects.create(user=self.user, name="Kale")
        Ingredient.objects.create(user=self.user, name="Salt")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """ Test that ingredients for the authenticated user are returned. """
        another_user = get_user_model().objects.create_user(
            "other@hackfeed.com",
            "testpass"
        )
        Ingredient.objects.create(user=another_user, name="Vinegar")
        ingredient = Ingredient.objects.create(user=self.user, name="Tumeric")

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ingredient.name)

    def test_create_ingredient_succesful(self):
        """ Test create a new ingredient. """
        payload = {"name": "Cabbage"}
        self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload["name"],
        ).exists()

        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """ Test creating invalid ingredient fails. """
        payload = {"name": ""}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """ Test filtering ingredients by those assigned to recipes. """
        first_ingredient = Ingredient.objects.create(
            user=self.user,
            name="Apples"
        )
        second_ingredient = Ingredient.objects.create(
            user=self.user,
            name="Turkey"
        )
        recipe = Recipe.objects.create(
            title="Apple crumble",
            time_minutes=5,
            price=10.00,
            user=self.user
        )
        recipe.ingredients.add(first_ingredient)

        res = self.client.get(INGREDIENTS_URL, {"assigned_only": 1})

        first_serializer = IngredientSerializer(first_ingredient)
        second_serializer = IngredientSerializer(second_ingredient)

        self.assertIn(first_serializer.data, res.data)
        self.assertNotIn(second_serializer.data, res.data)
