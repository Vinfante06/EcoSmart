from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import servicios
from .formularios import (
    AbonoAhorroForm,
    AlertaForm,
    CategoriaForm,
    FiltroHistorialForm,
    GastoForm,
    IngresoForm,
    ObjetivoAhorroForm,
    PresupuestoForm,
)
from .models import AlertaPersonalizada, Categoria, Gasto, Ingreso, Presupuesto
from .reportes import generar_reporte_excel, generar_reporte_pdf


def _avisar_errores_formulario(request, formulario):
    for errores in formulario.errors.values():
        for error in errores:
            messages.error(request, error)


def _primer_error(formulario, mensaje_por_defecto):
    for errores in formulario.errors.values():
        if errores:
            return errores[0]
    return mensaje_por_defecto


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    formulario = AuthenticationForm(data=request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        login(request, formulario.get_user())
        return redirect("home")

    return render(request, "budget/login.html", {"form": formulario})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    formulario = UserCreationForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        usuario = formulario.save()
        login(request, usuario)
        return redirect("home")

    return render(request, "budget/register.html", {"form": formulario})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    return render(request, "budget/home.html", servicios.obtener_resumen_inicio(request.user))


@login_required
def remaining_budget(request):
    mes, anio = servicios.normalizar_periodo(
        request.GET.get("mes"),
        request.GET.get("anio"),
    )
    return render(
        request,
        "budget/remaining_budget.html",
        servicios.obtener_presupuestos_restantes(request.user, mes, anio),
    )


@login_required
def manage_categories(request):
    categorias = servicios.obtener_categorias(request.user)
    return render(request, "budget/manage_categories.html", {"categorias": categorias})


@login_required
def category_create(request):
    formulario = CategoriaForm(request.POST or None, usuario=request.user)
    if request.method == "POST":
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Categoría creada correctamente.")
            return redirect("manage_categories")
        _avisar_errores_formulario(request, formulario)

    return render(
        request,
        "budget/category_form.html",
        {"titulo": "Crear Categoría", "action": "crear", "form": formulario},
    )


@login_required
def category_edit(request, id):
    categoria = get_object_or_404(Categoria, id=id, usuario=request.user)
    formulario = CategoriaForm(
        request.POST or None,
        instance=categoria,
        usuario=request.user,
    )
    if request.method == "POST":
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Categoría actualizada correctamente.")
            return redirect("manage_categories")
        _avisar_errores_formulario(request, formulario)

    return render(
        request,
        "budget/category_form.html",
        {
            "titulo": "Editar Categoría",
            "action": "editar",
            "categoria": categoria,
            "form": formulario,
        },
    )


@login_required
def category_delete(request, id):
    categoria = get_object_or_404(Categoria, id=id, usuario=request.user)
    if request.method == "POST":
        categoria.delete()
        messages.success(request, "Categoría eliminada correctamente.")
        return redirect("manage_categories")
    return render(request, "budget/category_confirm_delete.html", {"categoria": categoria})


@login_required
def income_register(request):
    if request.method == "POST":
        formulario = IngresoForm(request.POST, usuario=request.user)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Ingreso registrado correctamente.")
            return redirect("income_register")
        _avisar_errores_formulario(request, formulario)

    contexto = servicios.obtener_movimientos_con_grafica(
        Ingreso,
        request.user,
        request.GET.get("categoria"),
    )
    contexto["ingresos"] = contexto.pop("movimientos")
    return render(request, "budget/income_register.html", contexto)


@login_required
def income_delete(request, id):
    ingreso = get_object_or_404(Ingreso, id=id, usuario=request.user)
    if request.method == "POST":
        ingreso.delete()
        messages.success(request, "Ingreso eliminado correctamente.")
    return redirect("income_register")


@login_required
def expense_record(request):
    if request.method == "POST":
        formulario = GastoForm(request.POST, usuario=request.user)
        if formulario.is_valid():
            gasto = formulario.save()
            alerta_presupuesto = servicios.evaluar_alerta_presupuesto(request.user, gasto.categoria)
            alerta_anomalia = servicios.detectar_anomalia_gasto(request.user, gasto)
            if alerta_presupuesto:
                getattr(messages, alerta_presupuesto["nivel"])(request, alerta_presupuesto["mensaje"])
            if alerta_anomalia:
                getattr(messages, alerta_anomalia["nivel"])(request, alerta_anomalia["mensaje"])
            if not alerta_presupuesto and not alerta_anomalia:
                messages.success(request, "Gasto registrado correctamente.")
            return redirect("expense_record")
        _avisar_errores_formulario(request, formulario)

    contexto = servicios.obtener_movimientos_con_grafica(
        Gasto,
        request.user,
        request.GET.get("categoria"),
    )
    contexto["gastos"] = contexto.pop("movimientos")
    return render(request, "budget/expense_record.html", contexto)


@login_required
def expense_delete(request, id):
    gasto = get_object_or_404(Gasto, id=id, usuario=request.user)
    if request.method == "POST":
        gasto.delete()
        messages.success(request, "Gasto eliminado correctamente.")
    return redirect("expense_record")


@login_required
def transaction_history(request):
    formulario = FiltroHistorialForm(request.GET or None, usuario=request.user)
    filtros = formulario.cleaned_data if formulario.is_valid() else {}
    if request.GET and formulario.errors:
        _avisar_errores_formulario(request, formulario)

    categoria_filtrada = filtros.get("categoria")
    desde = filtros.get("desde")
    hasta = filtros.get("hasta")
    contexto = {
        "transacciones": servicios.obtener_historial_transacciones(request.user, filtros),
        "categorias": servicios.obtener_categorias(request.user),
        "filtro_tipo": filtros.get("tipo", ""),
        "filtro_categoria": categoria_filtrada.id if categoria_filtrada else "",
        "filtro_desde": desde.isoformat() if desde else "",
        "filtro_hasta": hasta.isoformat() if hasta else "",
    }
    return render(request, "budget/transaction_history.html", contexto)


@login_required
def financial_statistics(request):
    return render(
        request,
        "budget/financial_statistics.html",
        servicios.obtener_estadisticas_financieras(request.user),
    )


@login_required
def analizar_habitos(request):
    return render(
        request,
        "budget/analizar_habitos.html",
        servicios.analizar_habitos_de_gasto(request.user),
    )


@login_required
def savings_goal(request):
    error = None

    if request.method == "POST":
        if request.POST.get("action") == "add_progress":
            formulario = AbonoAhorroForm(request.POST, usuario=request.user)
            if formulario.is_valid():
                formulario.guardar()
                messages.success(request, "Avance registrado correctamente.")
                return redirect("savings_goal")
            error = _primer_error(formulario, "No se pudo registrar el abono.")
        else:
            formulario = ObjetivoAhorroForm(request.POST, usuario=request.user)
            if formulario.is_valid():
                formulario.save()
                messages.success(request, "Objetivo de ahorro creado correctamente.")
                return redirect("savings_goal")
            error = _primer_error(formulario, "No se pudo crear el objetivo.")

    return render(
        request,
        "budget/savings_goal.html",
        {"objetivos": servicios.obtener_objetivos_con_progreso(request.user), "error": error},
    )


@login_required
def budget_create(request):
    mes, anio = servicios.normalizar_periodo(
        request.GET.get("mes"),
        request.GET.get("anio"),
    )

    if request.method == "POST":
        formulario = PresupuestoForm(request.POST, usuario=request.user)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Presupuesto creado correctamente.")
            m = formulario.cleaned_data["mes"]
            a = formulario.cleaned_data["anio"]
            return redirect(f"{reverse('budget_create')}?mes={m}&anio={a}")
        _avisar_errores_formulario(request, formulario)
    else:
        formulario = PresupuestoForm(
            usuario=request.user,
            initial={"mes": mes, "anio": anio},
        )

    mes_ant, anio_ant = servicios.calcular_periodo_adyacente(mes, anio, -1)
    mes_sig, anio_sig = servicios.calcular_periodo_adyacente(mes, anio, +1)

    return render(
        request,
        "budget/budget_create.html",
        {
            "form": formulario,
            "categorias": servicios.obtener_categorias(request.user),
            "presupuestos": Presupuesto.objects.filter(
                usuario=request.user, mes=mes, anio=anio
            ).select_related("categoria").order_by("categoria__nombre"),
            "mes": mes, "anio": anio,
            "nombre_mes": servicios.obtener_nombre_mes(mes),
            "mes_ant": mes_ant, "anio_ant": anio_ant,
            "mes_sig": mes_sig, "anio_sig": anio_sig,
        },
    )


@login_required
def copiar_presupuesto_mes(request):
    if request.method != "POST":
        return redirect("budget_create")
    mes, anio = servicios.normalizar_periodo(
        request.POST.get("mes"),
        request.POST.get("anio"),
    )
    copiados = servicios.copiar_presupuestos_mes_anterior(request.user, mes, anio)
    if copiados:
        messages.success(request, f"Se copiaron {copiados} presupuesto(s) del mes anterior.")
    else:
        messages.warning(request, "No se encontraron presupuestos nuevos para copiar del mes anterior.")
    return redirect(f"{reverse('budget_create')}?mes={mes}&anio={anio}")


@login_required
def configure_alerts(request):
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            alerta_id = request.POST.get("alerta_id")
            AlertaPersonalizada.objects.filter(id=alerta_id, usuario=request.user).delete()
            messages.success(request, "Alerta eliminada correctamente.")
            return redirect("configure_alerts")

        categoria_id = request.POST.get("categoria")
        instancia = AlertaPersonalizada.objects.filter(
            usuario=request.user, categoria_id=categoria_id
        ).first()
        formulario = AlertaForm(request.POST, instance=instancia, usuario=request.user)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, "Alerta guardada correctamente.")
            return redirect("configure_alerts")
        _avisar_errores_formulario(request, formulario)
    else:
        formulario = AlertaForm(usuario=request.user)

    alertas = (
        AlertaPersonalizada.objects.filter(usuario=request.user)
        .select_related("categoria")
        .order_by("categoria__nombre")
    )
    return render(
        request,
        "budget/configure_alerts.html",
        {"form": formulario, "alertas": alertas},
    )


@login_required
def export_pdfpage(request):
    mes_actual, anio_actual = servicios.obtener_periodo_actual()
    return render(
        request,
        "budget/export_pdf.html",
        {
            "current_month": mes_actual,
            "current_year": anio_actual,
            "years": list(range(anio_actual - 5, anio_actual + 3)),
        },
    )


@login_required
def export_monthly_pdf(request):
    mes, anio = servicios.normalizar_periodo(
        request.GET.get("mes"),
        request.GET.get("anio"),
    )
    datos = servicios.obtener_datos_reporte_mensual(request.user, mes, anio)
    return generar_reporte_pdf(datos)


@login_required
def export_monthly_excel(request):
    mes, anio = servicios.normalizar_periodo(
        request.GET.get("mes"),
        request.GET.get("anio"),
    )
    datos = servicios.obtener_datos_reporte_mensual(request.user, mes, anio)
    return generar_reporte_excel(datos)
