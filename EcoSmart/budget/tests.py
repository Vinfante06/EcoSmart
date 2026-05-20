from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from . import servicios
from .formularios import (
    AbonoAhorroForm,
    GastoForm,
    IngresoForm,
    ObjetivoAhorroForm,
    PresupuestoForm,
)
from .models import Categoria, Gasto, Ingreso, ObjetivoAhorro, Presupuesto


class ServiciosFinancierosTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="ana", password="clave12345")
        self.otro_usuario = User.objects.create_user(
            username="luis",
            password="clave12345",
        )
        self.comida = Categoria.objects.create(nombre="Comida", usuario=self.usuario)
        self.transporte = Categoria.objects.create(
            nombre="Transporte",
            usuario=self.usuario,
        )
        self.otra_categoria = Categoria.objects.create(
            nombre="Comida",
            usuario=self.otro_usuario,
        )

    def test_totales_de_ingresos_y_gastos_se_aislan_por_usuario(self):
        Ingreso.objects.create(
            descripcion="Salario",
            monto=Decimal("1000.00"),
            categoria=self.comida,
            usuario=self.usuario,
        )
        Gasto.objects.create(
            descripcion="Mercado",
            monto=Decimal("350.00"),
            categoria=self.comida,
            usuario=self.usuario,
        )
        Ingreso.objects.create(
            descripcion="Dato externo",
            monto=Decimal("999.00"),
            categoria=self.otra_categoria,
            usuario=self.otro_usuario,
        )
        Gasto.objects.create(
            descripcion="Gasto externo",
            monto=Decimal("888.00"),
            categoria=self.otra_categoria,
            usuario=self.otro_usuario,
        )

        resumen = servicios.obtener_resumen_inicio(self.usuario)

        self.assertEqual(resumen["total_ingresos"], Decimal("1000.00"))
        self.assertEqual(resumen["total_gastos"], Decimal("350.00"))
        self.assertEqual(resumen["balance"], Decimal("650.00"))

    def test_validaciones_rechazan_montos_no_positivos(self):
        ingreso_form = IngresoForm(
            {"descripcion": "Pago", "monto": "0", "categoria": ""},
            usuario=self.usuario,
        )
        gasto_form = GastoForm(
            {"descripcion": "Compra", "monto": "-1", "categoria": ""},
            usuario=self.usuario,
        )
        presupuesto_form = PresupuestoForm(
            {
                "categoria": self.comida.id,
                "monto_limite": "0",
                "mes": "5",
                "anio": "2026",
            },
            usuario=self.usuario,
        )
        objetivo_form = ObjetivoAhorroForm(
            {"nombre": "Viaje", "monto_objetivo": "0", "fecha_objetivo": ""},
            usuario=self.usuario,
        )
        objetivo = ObjetivoAhorro.objects.create(
            nombre="Computador",
            monto_objetivo=Decimal("500.00"),
            usuario=self.usuario,
        )
        abono_form = AbonoAhorroForm(
            {"objetivo_id": objetivo.id, "abono": "0"},
            usuario=self.usuario,
        )

        self.assertFalse(ingreso_form.is_valid())
        self.assertFalse(gasto_form.is_valid())
        self.assertFalse(presupuesto_form.is_valid())
        self.assertFalse(objetivo_form.is_valid())
        self.assertFalse(abono_form.is_valid())

    def test_estados_de_presupuesto(self):
        self.assertEqual(servicios.calcular_estado_presupuesto(79.99), "OK")
        self.assertEqual(servicios.calcular_estado_presupuesto(80), "Crítico")
        self.assertEqual(servicios.calcular_estado_presupuesto(100), "Tope Máximo")

    def test_presupuesto_restante_calcula_porcentaje_y_estado(self):
        Presupuesto.objects.create(
            categoria=self.comida,
            monto_limite=Decimal("100.00"),
            mes=5,
            anio=2026,
            usuario=self.usuario,
        )
        gasto = Gasto.objects.create(
            descripcion="Mercado",
            monto=Decimal("85.00"),
            categoria=self.comida,
            usuario=self.usuario,
        )
        Gasto.objects.filter(id=gasto.id).update(fecha=date(2026, 5, 3))

        resultado = servicios.obtener_presupuestos_restantes(self.usuario, 5, 2026)
        item = resultado["presupuestos"][0]

        self.assertEqual(item["total_gastos"], Decimal("85.00"))
        self.assertEqual(item["restante"], Decimal("15.00"))
        self.assertEqual(item["porcentaje"], 85.0)
        self.assertEqual(item["estado"], "Crítico")

    def test_historial_filtra_por_tipo_categoria_y_fechas(self):
        ingreso = Ingreso.objects.create(
            descripcion="Salario",
            monto=Decimal("1200.00"),
            categoria=self.transporte,
            usuario=self.usuario,
        )
        gasto = Gasto.objects.create(
            descripcion="Bus",
            monto=Decimal("50.00"),
            categoria=self.transporte,
            usuario=self.usuario,
        )
        Ingreso.objects.filter(id=ingreso.id).update(fecha=date(2026, 5, 1))
        Gasto.objects.filter(id=gasto.id).update(fecha=date(2026, 5, 2))

        transacciones = servicios.obtener_historial_transacciones(
            self.usuario,
            {
                "tipo": "gasto",
                "categoria": self.transporte,
                "desde": date(2026, 5, 1),
                "hasta": date(2026, 5, 31),
            },
        )

        self.assertEqual(len(transacciones), 1)
        self.assertEqual(transacciones[0]["tipo"], "gasto")
        self.assertEqual(transacciones[0]["descripcion"], "Bus")

    def test_progreso_de_objetivos_de_ahorro(self):
        objetivo = ObjetivoAhorro.objects.create(
            nombre="Fondo de emergencia",
            monto_objetivo=Decimal("200.00"),
            monto_ahorrado=Decimal("50.00"),
            usuario=self.usuario,
        )

        [item] = servicios.obtener_objetivos_con_progreso(self.usuario)
        self.assertEqual(item["progreso"], 25.0)
        self.assertEqual(item["restante"], Decimal("150.00"))
        self.assertFalse(item["completado"])

        formulario = AbonoAhorroForm(
            {"objetivo_id": objetivo.id, "abono": "150.00"},
            usuario=self.usuario,
        )
        self.assertTrue(formulario.is_valid())
        formulario.guardar()

        [item_actualizado] = servicios.obtener_objetivos_con_progreso(self.usuario)
        self.assertEqual(item_actualizado["progreso"], 100.0)
        self.assertTrue(item_actualizado["completado"])
