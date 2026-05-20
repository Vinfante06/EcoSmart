import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EcoSmart.settings')
django.setup()

from django.contrib.auth.models import User
from budget.models import Categoria, Ingreso, Gasto, Presupuesto
from datetime import date

u = User.objects.get(username='miguelmercado')

# ── Categorías ─────────────────────────────────────────────────────────────────
cats = {}
for nombre in ['Comida', 'Transporte', 'Entretenimiento', 'Servicios', 'Salud']:
    cat, _ = Categoria.objects.get_or_create(nombre=nombre, usuario=u)
    cats[nombre] = cat
    print(f"[+] Categoría: {nombre}  id={cat.id}")

# ── Ingreso mes actual (abril 2026) ────────────────────────────────────────────
ingreso, created = Ingreso.objects.get_or_create(
    descripcion='Salario abril', usuario=u,
    defaults={'monto': 3000, 'categoria': None}
)
if not created:
    ingreso.monto = 3000
    ingreso.save()
i = Ingreso.objects.get(id=ingreso.id)
i.fecha = date(2026, 4, 1)
i.save(update_fields=['fecha'])
print(f"[+] Ingreso 'Salario abril' $3000  created={created}")

# ── Limpiar gastos de prueba anteriores ────────────────────────────────────────
deleted, _ = Gasto.objects.filter(usuario=u, descripcion__startswith='TEST_').delete()
print(f"[~] Gastos TEST anteriores eliminados: {deleted}")

# ── Gastos históricos: febrero 2026 ───────────────────────────────────────────
datos_feb = [
    ('Comida', 150), ('Comida', 80),
    ('Transporte', 60), ('Entretenimiento', 40),
    ('Servicios', 120), ('Salud', 50),
]
for cat_name, monto in datos_feb:
    g = Gasto.objects.create(descripcion=f'TEST_{cat_name}_feb', monto=monto,
                              categoria=cats[cat_name], usuario=u)
    Gasto.objects.filter(id=g.id).update(fecha=date(2026, 2, 15))

print("[+] Gastos febrero insertados")

# ── Gastos históricos: marzo 2026 ─────────────────────────────────────────────
datos_mar = [
    ('Comida', 170), ('Transporte', 70),
    ('Entretenimiento', 30), ('Servicios', 110), ('Salud', 45),
]
for cat_name, monto in datos_mar:
    g = Gasto.objects.create(descripcion=f'TEST_{cat_name}_mar', monto=monto,
                              categoria=cats[cat_name], usuario=u)
    Gasto.objects.filter(id=g.id).update(fecha=date(2026, 3, 15))

print("[+] Gastos marzo insertados")

# ── Gastos abril 2026 (Comida ~82% del límite 350) ────────────────────────────
datos_abr = [
    ('Comida', 200), ('Comida', 85),   # 285/350 = 81.4%
    ('Transporte', 55),                 # 55/150 = 36.7%
    ('Entretenimiento', 20),            # 20/100 = 20%
    ('Servicios', 100),                 # 100/200 = 50%
]
for cat_name, monto in datos_abr:
    g = Gasto.objects.create(descripcion=f'TEST_{cat_name}_abr', monto=monto,
                              categoria=cats[cat_name], usuario=u)
    Gasto.objects.filter(id=g.id).update(fecha=date(2026, 4, 15))

print("[+] Gastos abril insertados")

# ── Presupuestos abril 2026 ───────────────────────────────────────────────────
presups = {
    'Comida': 350, 'Transporte': 150,
    'Entretenimiento': 100, 'Servicios': 200, 'Salud': 80,
}
for cat_name, limite in presups.items():
    p, created = Presupuesto.objects.get_or_create(
        categoria=cats[cat_name], mes=4, anio=2026, usuario=u,
        defaults={'monto_limite': limite}
    )
    if not created:
        p.monto_limite = limite
        p.save()
    print(f"[+] Presupuesto {cat_name}: ${limite}  created={created}")

print("\nDONE — abre http://127.0.0.1:8000/presupuesto/restante/?mes=4&anio=2026")
