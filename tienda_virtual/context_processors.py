from django.conf import settings

def globals(request):
 
    return {
        "MONEDA": getattr(settings, "MONEDA", "€"),
        "ENVIO_GRATIS_DESDE": getattr(settings, "ENVIO_GRATIS_DESDE", 0),
        "settings": settings,  # por si necesitas leer otras constantes
    }