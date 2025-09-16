from django.contrib import admin
from .models import Categoria, Marca, Producto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'padre')
    prepopulated_fields = {"slug": ("nombre",)}

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    prepopulated_fields = {"slug": ("nombre",)}

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'marca', 'precio', 'stock', 'activo', 'destacado')
    list_filter = ('categoria', 'marca', 'activo', 'destacado')
    search_fields = ('nombre',)
    prepopulated_fields = {"slug": ("nombre",)}
