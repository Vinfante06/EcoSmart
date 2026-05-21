import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import AlertaPersonalizada, Categoria, Gasto, Ingreso, ObjetivoAhorro, Presupuesto


CERO = Decimal("0")
MESES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def obtener_periodo_actual():
    hoy = timezone.localdate()
    return hoy.month, hoy.year


def normalizar_periodo(mes=None, anio=None):
    mes_actual, anio_actual = obtener_periodo_actual()
    try:
        mes = int(mes)
        anio = int(anio)
    except (TypeError, ValueError):
        return mes_actual, anio_actual

    if mes < 1 or mes > 12 or anio < 2000 or anio > 2100:
        return mes_actual, anio_actual
    return mes, anio


def obtener_nombre_mes(mes):
    return MESES[mes - 1]


def calcular_periodo_adyacente(mes, anio, delta):
    mes_nuevo = mes + delta
    anio_nuevo = anio
    if mes_nuevo < 1:
        mes_nuevo = 12
        anio_nuevo -= 1
    elif mes_nuevo > 12:
        mes_nuevo = 1
        anio_nuevo += 1
    return mes_nuevo, anio_nuevo


def sumar_montos(queryset):
    return queryset.aggregate(total=Sum("monto"))["total"] or CERO


def convertir_a_float(valor):
    return float(valor or CERO)


def redondear_monto(valor):
    return Decimal(valor or CERO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_porcentaje(parte, total):
    if not total or total <= 0:
        return 0
    porcentaje = (Decimal(parte or CERO) / Decimal(total)) * Decimal("100")
    return float(porcentaje.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calcular_estado_presupuesto(porcentaje):
    if porcentaje >= 100:
        return "Tope Máximo"
    if porcentaje >= 80:
        return "Crítico"
    return "OK"


def obtener_categorias(usuario):
    return Categoria.objects.filter(usuario=usuario).order_by("nombre")


def detectar_anomalia_gasto(usuario, gasto):
    if not gasto.categoria:
        return None

    hoy = timezone.localdate()
    inicio_mes_actual = date(hoy.year, hoy.month, 1)
    mes_inicio = hoy.month - 3
    anio_inicio = hoy.year
    if mes_inicio < 1:
        mes_inicio += 12
        anio_inicio -= 1
    inicio_historico = date(anio_inicio, mes_inicio, 1)

    historicos = Gasto.objects.filter(
        usuario=usuario,
        categoria=gasto.categoria,
        fecha__gte=inicio_historico,
        fecha__lt=inicio_mes_actual,
    )
    conteo = historicos.count()
    if conteo < 3:
        return None

    total_hist = sumar_montos(historicos)
    promedio_tx = total_hist / conteo
    if promedio_tx <= CERO:
        return None

    if gasto.monto >= promedio_tx * Decimal("2.5"):
        return {
            "nivel": "warning",
            "mensaje": (
                f'Gasto inusual en "{gasto.categoria.nombre}": '
                f'${convertir_a_float(gasto.monto):.2f} es '
                f'{float(gasto.monto / promedio_tx):.1f}x el promedio histórico '
                f'(${convertir_a_float(promedio_tx):.2f} por transacción).'
            ),
        }

    promedio_mensual = total_hist / Decimal("3")
    total_mes = sumar_montos(
        Gasto.objects.filter(
            usuario=usuario,
            categoria=gasto.categoria,
            fecha__year=hoy.year,
            fecha__month=hoy.month,
        )
    )
    if promedio_mensual > CERO and total_mes >= promedio_mensual * Decimal("2"):
        return {
            "nivel": "warning",
            "mensaje": (
                f'Gasto mensual elevado en "{gasto.categoria.nombre}": '
                f'llevas ${convertir_a_float(total_mes):.2f} este mes, '
                f'el doble del promedio histórico (${convertir_a_float(promedio_mensual):.2f}/mes).'
            ),
        }

    return None


def obtener_alertas_anomalias_mes(usuario):
    hoy = timezone.localdate()
    inicio_mes_actual = date(hoy.year, hoy.month, 1)
    mes_inicio = hoy.month - 3
    anio_inicio = hoy.year
    if mes_inicio < 1:
        mes_inicio += 12
        anio_inicio -= 1
    inicio_historico = date(anio_inicio, mes_inicio, 1)

    historico_por_cat = (
        Gasto.objects.filter(
            usuario=usuario,
            fecha__gte=inicio_historico,
            fecha__lt=inicio_mes_actual,
        )
        .values("categoria__id", "categoria__nombre")
        .annotate(total_hist=Sum("monto"), cantidad=Count("id"))
    )

    alertas = []
    for fila in historico_por_cat:
        if (fila["cantidad"] or 0) < 3:
            continue
        promedio_mensual = Decimal(fila["total_hist"] or 0) / Decimal("3")
        if promedio_mensual <= CERO:
            continue

        total_mes = sumar_montos(
            Gasto.objects.filter(
                usuario=usuario,
                categoria_id=fila["categoria__id"],
                fecha__year=hoy.year,
                fecha__month=hoy.month,
            )
        )

        if total_mes >= promedio_mensual * Decimal("2"):
            alertas.append({
                "categoria_nombre": fila["categoria__nombre"] or "Sin categoría",
                "total_mes": redondear_monto(total_mes),
                "promedio_mensual": redondear_monto(promedio_mensual),
                "ratio": round(float(total_mes / promedio_mensual), 1),
            })

    return alertas


def obtener_resumen_inicio(usuario):
    total_ingresos = sumar_montos(Ingreso.objects.filter(usuario=usuario))
    total_gastos = sumar_montos(Gasto.objects.filter(usuario=usuario))
    return {
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "balance": total_ingresos - total_gastos,
        "alertas_anomalias": obtener_alertas_anomalias_mes(usuario),
    }


def _normalizar_id(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def obtener_movimientos_con_grafica(modelo, usuario, filtro_categoria=None):
    categoria_id = _normalizar_id(filtro_categoria)
    movimientos = (
        modelo.objects.filter(usuario=usuario)
        .select_related("categoria")
        .order_by("-fecha", "-id")
    )
    if categoria_id:
        movimientos = movimientos.filter(categoria_id=categoria_id)

    agrupados = (
        movimientos.values("categoria__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")
    )
    etiquetas = [fila["categoria__nombre"] or "Sin categoría" for fila in agrupados]
    montos = [convertir_a_float(fila["total"]) for fila in agrupados]

    return {
        "categorias": obtener_categorias(usuario),
        "movimientos": movimientos,
        "filtro_categoria": categoria_id or "",
        "categorias_json": json.dumps(etiquetas),
        "montos_json": json.dumps(montos),
    }


def obtener_presupuestos_restantes(usuario, mes=None, anio=None):
    if mes is None or anio is None:
        mes, anio = obtener_periodo_actual()

    presupuestos = (
        Presupuesto.objects.filter(mes=mes, anio=anio, usuario=usuario)
        .select_related("categoria")
        .order_by("categoria__nombre")
    )

    resumen = []
    for presupuesto in presupuestos:
        total_gastos = sumar_montos(
            Gasto.objects.filter(
                categoria=presupuesto.categoria,
                fecha__month=mes,
                fecha__year=anio,
                usuario=usuario,
            )
        )
        restante = redondear_monto(presupuesto.monto_limite - total_gastos)
        porcentaje = calcular_porcentaje(total_gastos, presupuesto.monto_limite)

        resumen.append(
            {
                "presupuesto": presupuesto,
                "total_gastos": total_gastos,
                "restante": restante,
                "porcentaje": porcentaje,
                "estado": calcular_estado_presupuesto(porcentaje),
            }
        )

    mes_ant, anio_ant = calcular_periodo_adyacente(mes, anio, -1)
    mes_sig, anio_sig = calcular_periodo_adyacente(mes, anio, +1)
    return {
        "presupuestos": resumen,
        "mes": mes, "anio": anio,
        "nombre_mes": obtener_nombre_mes(mes),
        "mes_ant": mes_ant, "anio_ant": anio_ant,
        "mes_sig": mes_sig, "anio_sig": anio_sig,
    }


def evaluar_alerta_presupuesto(usuario, categoria):
    if not categoria:
        return None

    mes, anio = obtener_periodo_actual()
    presupuesto = Presupuesto.objects.filter(
        categoria=categoria,
        mes=mes,
        anio=anio,
        usuario=usuario,
    ).first()
    if not presupuesto or presupuesto.monto_limite <= 0:
        return None

    total_gastado = sumar_montos(
        Gasto.objects.filter(
            categoria=categoria,
            fecha__month=mes,
            fecha__year=anio,
            usuario=usuario,
        )
    )
    porcentaje = calcular_porcentaje(total_gastado, presupuesto.monto_limite)
    mensaje_base = (
        f'Gastado: ${convertir_a_float(total_gastado):.2f} / '
        f'Límite: ${convertir_a_float(presupuesto.monto_limite):.2f}'
    )

    alerta_config = AlertaPersonalizada.objects.filter(
        usuario=usuario, categoria=categoria
    ).first()
    umbral_advertencia = alerta_config.umbral_advertencia if alerta_config else 80
    umbral_critico = alerta_config.umbral_critico if alerta_config else 100

    if porcentaje >= umbral_critico:
        return {
            "nivel": "error",
            "mensaje": (
                f'Has superado el presupuesto de "{categoria.nombre}". {mensaje_base}'
            ),
        }
    if porcentaje >= umbral_advertencia:
        return {
            "nivel": "warning",
            "mensaje": (
                f'Ya usaste el {porcentaje:.0f}% del presupuesto de '
                f'"{categoria.nombre}". {mensaje_base}'
            ),
        }
    return None


def copiar_presupuestos_mes_anterior(usuario, mes, anio):
    mes_ant, anio_ant = calcular_periodo_adyacente(mes, anio, -1)
    presupuestos_origen = Presupuesto.objects.filter(mes=mes_ant, anio=anio_ant, usuario=usuario)
    ya_presentes = set(
        Presupuesto.objects.filter(mes=mes, anio=anio, usuario=usuario)
        .values_list("categoria_id", flat=True)
    )
    nuevos = [
        Presupuesto(
            categoria=p.categoria,
            monto_limite=p.monto_limite,
            mes=mes,
            anio=anio,
            usuario=usuario,
        )
        for p in presupuestos_origen
        if p.categoria_id not in ya_presentes
    ]
    if nuevos:
        Presupuesto.objects.bulk_create(nuevos)
    return len(nuevos)


def obtener_historial_transacciones(usuario, filtros=None):
    filtros = filtros or {}
    tipo = filtros.get("tipo") or ""
    categoria = filtros.get("categoria")
    desde = filtros.get("desde")
    hasta = filtros.get("hasta")

    ingresos = Ingreso.objects.filter(usuario=usuario).select_related("categoria")
    gastos = Gasto.objects.filter(usuario=usuario).select_related("categoria")

    if categoria:
        ingresos = ingresos.filter(categoria=categoria)
        gastos = gastos.filter(categoria=categoria)
    if desde:
        ingresos = ingresos.filter(fecha__gte=desde)
        gastos = gastos.filter(fecha__gte=desde)
    if hasta:
        ingresos = ingresos.filter(fecha__lte=hasta)
        gastos = gastos.filter(fecha__lte=hasta)

    transacciones = []
    if tipo != "gasto":
        transacciones.extend(
            {
                "tipo": "ingreso",
                "descripcion": ingreso.descripcion,
                "monto": ingreso.monto,
                "fecha": ingreso.fecha,
                "categoria": ingreso.categoria,
                "id": ingreso.id,
            }
            for ingreso in ingresos
        )
    if tipo != "ingreso":
        transacciones.extend(
            {
                "tipo": "gasto",
                "descripcion": gasto.descripcion,
                "monto": gasto.monto,
                "fecha": gasto.fecha,
                "categoria": gasto.categoria,
                "id": gasto.id,
            }
            for gasto in gastos
        )

    transacciones.sort(key=lambda item: (item["fecha"], item["id"]), reverse=True)
    return transacciones


def obtener_estadisticas_financieras(usuario):
    ingresos = Ingreso.objects.filter(usuario=usuario)
    gastos = Gasto.objects.filter(usuario=usuario)
    total_ingresos = sumar_montos(ingresos)
    total_gastos = sumar_montos(gastos)
    balance = total_ingresos - total_gastos

    num_ingresos = ingresos.count()
    num_gastos = gastos.count()
    promedio_ingreso = (
        redondear_monto(total_ingresos / num_ingresos) if num_ingresos else CERO
    )
    promedio_gasto = redondear_monto(total_gastos / num_gastos) if num_gastos else CERO
    tasa_ahorro = calcular_porcentaje(balance, total_ingresos) if total_ingresos > 0 else 0

    cat_gastos = list(
        gastos.values("categoria__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")
    )
    top_categoria = cat_gastos[0] if cat_gastos else None

    ingresos_por_mes = (
        ingresos.annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )
    gastos_por_mes = (
        gastos.annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    meses = sorted(
        {fila["mes"] for fila in ingresos_por_mes}
        | {fila["mes"] for fila in gastos_por_mes}
    )
    ingresos_dict = {fila["mes"]: convertir_a_float(fila["total"]) for fila in ingresos_por_mes}
    gastos_dict = {fila["mes"]: convertir_a_float(fila["total"]) for fila in gastos_por_mes}

    evolucion = []
    for mes in meses:
        ingreso = ingresos_dict.get(mes, 0)
        gasto = gastos_dict.get(mes, 0)
        evolucion.append(
            {
                "mes": mes.strftime("%b %Y"),
                "ingreso": ingreso,
                "gasto": gasto,
                "balance": round(ingreso - gasto, 2),
            }
        )

    return {
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "balance": balance,
        "tasa_ahorro": tasa_ahorro,
        "num_ingresos": num_ingresos,
        "num_gastos": num_gastos,
        "promedio_ingreso": promedio_ingreso,
        "promedio_gasto": promedio_gasto,
        "top_categoria": top_categoria,
        "evolucion": evolucion,
        "mes_mayor_gasto": max(evolucion, key=lambda item: item["gasto"]) if evolucion else None,
        "cat_gastos": cat_gastos,
    }


def analizar_habitos_de_gasto(usuario):
    gastos_por_cat = list(
        Gasto.objects.filter(usuario=usuario)
        .values("categoria__nombre")
        .annotate(total=Sum("monto"), cantidad=Count("id"))
        .order_by("-total")
    )

    etiquetas_categoria = [
        fila["categoria__nombre"] or "Sin categoría" for fila in gastos_por_cat
    ]
    totales_categoria = [convertir_a_float(fila["total"]) for fila in gastos_por_cat]
    total_gastos = sum(totales_categoria)

    gastos_mes = (
        Gasto.objects.filter(usuario=usuario)
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )
    etiquetas_mes = [fila["mes"].strftime("%b %Y") for fila in gastos_mes]
    totales_mes = [convertir_a_float(fila["total"]) for fila in gastos_mes]

    tendencia = None
    if len(totales_mes) >= 2:
        diferencia = totales_mes[-1] - totales_mes[-2]
        tendencia = {
            "diferencia": round(abs(diferencia), 2),
            "sube": diferencia > 0,
            "mes_actual": etiquetas_mes[-1],
            "mes_anterior": etiquetas_mes[-2],
        }

    for categoria in gastos_por_cat:
        categoria["porcentaje"] = (
            round(convertir_a_float(categoria["total"]) / total_gastos * 100, 1)
            if total_gastos > 0
            else 0
        )

    return {
        "cat_labels_json": json.dumps(etiquetas_categoria),
        "cat_totales_json": json.dumps(totales_categoria),
        "meses_labels_json": json.dumps(etiquetas_mes),
        "meses_totales_json": json.dumps(totales_mes),
        "tendencia": tendencia,
        "promedio_mensual": round(sum(totales_mes) / len(totales_mes), 2)
        if totales_mes
        else 0,
        "top3": gastos_por_cat[:3],
        "gastos_por_cat": gastos_por_cat,
        "total_gastos": total_gastos,
    }


def obtener_objetivos_con_progreso(usuario):
    objetivos_db = ObjetivoAhorro.objects.filter(usuario=usuario).order_by(
        "-fecha_creacion", "-id"
    )
    objetivos = []
    for objetivo in objetivos_db:
        monto_objetivo = objetivo.monto_objetivo
        monto_ahorrado = objetivo.monto_ahorrado
        progreso = calcular_porcentaje(monto_ahorrado, monto_objetivo)
        objetivos.append(
            {
                "obj": objetivo,
                "progreso": progreso,
                "progreso_visual": min(progreso, 100),
                "restante": redondear_monto(monto_objetivo - monto_ahorrado),
                "completado": monto_ahorrado >= monto_objetivo,
            }
        )
    return objetivos



def obtener_datos_reporte_mensual(usuario, mes, anio):
    ingresos = (
        Ingreso.objects.filter(fecha__month=mes, fecha__year=anio, usuario=usuario)
        .select_related("categoria")
        .order_by("fecha", "id")
    )
    gastos = (
        Gasto.objects.filter(fecha__month=mes, fecha__year=anio, usuario=usuario)
        .select_related("categoria")
        .order_by("fecha", "id")
    )
    total_ingresos = sumar_montos(ingresos)
    total_gastos = sumar_montos(gastos)

    return {
        "mes": mes,
        "anio": anio,
        "mes_nombre": obtener_nombre_mes(mes),
        "presupuestos": obtener_presupuestos_restantes(usuario, mes, anio)["presupuestos"],
        "ingresos": ingresos,
        "total_ingresos": total_ingresos,
        "gastos": gastos,
        "total_gastos": total_gastos,
        "balance": total_ingresos - total_gastos,
        "objetivos": obtener_objetivos_con_progreso(usuario),
    }
