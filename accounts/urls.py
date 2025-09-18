from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("perfil/", views.perfil, name="perfil"),
    path("direccion/nueva/", views.address_create, name="address_create"),
    path("direccion/<int:pk>/editar/", views.address_edit, name="address_edit"),
    path("direccion/<int:pk>/eliminar/", views.address_delete, name="address_delete"),
    path("direccion/<int:pk>/predeterminada/", views.address_make_default, name="address_make_default"),
]
