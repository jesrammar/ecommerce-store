from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import Pedido

def staff_required(u): return u.is_active and u.is_staff

@login_required
@user_passes_test(staff_required)
def pedidos_list(request):
    qs = Pedido.objects.order_by("-fecha_creacion").select_related("cliente")
    estado = request.GET.get("estado","")
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, "admin/pedido_list.html", {"pedidos": qs, "estado": estado})

@login_required
@user_passes_test(staff_required)
def pedido_detalle(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado in dict(Pedido.ESTADOS).keys():
            pedido.estado = nuevo_estado
            pedido.save(update_fields=["estado"])
    return render(request, "admin/pedido_detail.html", {"pedido": pedido})
