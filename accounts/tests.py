# accounts/tests.py
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import CustomerProfile


class CustomerProfileModelTests(TestCase):
    def test_str_usa_username_del_usuario(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="pepe",
            email="pepe@example.com",
            password="1234",
        )

        # El perfil se crea automáticamente por la señal post_save
        perfil = CustomerProfile.objects.get(user=user)

        self.assertEqual(str(perfil), "Perfil pepe")
