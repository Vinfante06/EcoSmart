#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EcoSmart.settings')
django.setup()

from budget.models import Categoria, Presupuesto, Gasto, Ingreso
from datetime import datetime, timedelta
from decimal import Decimal

# Limpiar datos anteriores (opcional)
print("Limpiando datos anteriores...")
Categoria.objects.all().delete()
Presupuesto.objects.all().delete()
Gasto.objects.all().delete()
Ingreso.objects.all().delete()

# Crear categorías
print("Creando categorías...")
categorias_data = ['Comida', 'Transporte', 'Entretenimiento', 'Servicios', 'Salud']
categorias = {}
for nombre in categorias_data:
    cat = Categoria.objects.create(nombre=nombre)
    categorias[nombre] = cat
    print(f"  ✓ {nombre}")

# Crear presupuestos para febrero 2026
print("\nCreando presupuestos para febrero 2026...")
presupuestos_data = {
    'Comida': 500,
    'Transporte': 200,
    'Entretenimiento': 150,
    'Servicios': 300,
    'Salud': 100,
}

for nombre, monto in presupuestos_data.items():
    Presupuesto.objects.create(
        categoria=categorias[nombre],
        monto_limite=Decimal(str(monto)),
        mes=2,
        anio=2026
    )
    print(f"  ✓ {nombre}: ${monto}")

# Crear ingresos
print("\nCreando ingresos...")
ingresos_data = [
    ('Salario', 2000, 'Servicios'),
    ('Freelance', 500, 'Entretenimiento'),
]

for desc, monto, cat in ingresos_data:
    Ingreso.objects.create(
        descripcion=desc,
        monto=Decimal(str(monto)),
        categoria=categorias[cat],
        fecha=datetime.now().date()
    )
    print(f"  ✓ {desc}: ${monto}")

# Crear gastos para febrero 2026
print("\nCreando gastos para febrero 2026...")
gastos_data = [
    ('Almuerzo', 25, 'Comida'),
    ('Cena', 30, 'Comida'),
    ('Desayuno', 15, 'Comida'),
    ('Uber', 50, 'Transporte'),
    ('Gasolina', 40, 'Transporte'),
    ('Cine', 20, 'Entretenimiento'),
    ('Spotify', 15, 'Entretenimiento'),
    ('Internet', 50, 'Servicios'),
    ('Agua', 30, 'Servicios'),
    ('Farmacia', 45, 'Salud'),
]

for desc, monto, cat in gastos_data:
    # Crear fecha dentro de febrero 2026
    día = (gastos_data.index((desc, monto, cat)) % 28) + 1
    fecha = datetime(2026, 2, día).date()
    
    Gasto.objects.create(
        descripcion=desc,
        monto=Decimal(str(monto)),
        categoria=categorias[cat],
        fecha=fecha
    )
    print(f"  ✓ {desc}: ${monto} ({cat})")

print("\n✅ Datos de prueba creados exitosamente!")
print("\nResumen:")
print(f"  - Categorías: {Categoria.objects.count()}")
print(f"  - Presupuestos: {Presupuesto.objects.count()}")
print(f"  - Ingresos: {Ingreso.objects.count()}")
print(f"  - Gastos: {Gasto.objects.count()}")
