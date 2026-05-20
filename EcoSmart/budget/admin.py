from django.contrib import admin

from .models import Categoria, Gasto, Ingreso, ObjetivoAhorro, Presupuesto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "usuario")
    search_fields = ("nombre", "usuario__username")


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "monto", "categoria", "fecha", "usuario")
    list_filter = ("fecha", "categoria")
    search_fields = ("descripcion", "usuario__username")


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "monto", "categoria", "fecha", "usuario")
    list_filter = ("fecha", "categoria")
    search_fields = ("descripcion", "usuario__username")


@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ("categoria", "monto_limite", "mes", "anio", "usuario")
    list_filter = ("mes", "anio", "categoria")


@admin.register(ObjetivoAhorro)
class ObjetivoAhorroAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "monto_objetivo",
        "monto_ahorrado",
        "fecha_objetivo",
        "usuario",
    )
    list_filter = ("fecha_objetivo",)
    search_fields = ("nombre", "usuario__username")
