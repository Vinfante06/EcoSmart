from django.db import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.nombre


class Ingreso(models.Model):
    descripcion = models.CharField(max_length=200)
    monto       = models.DecimalField(max_digits=10, decimal_places=2)
    fecha       = models.DateField(auto_now_add=True)
    categoria   = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    usuario     = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.descripcion


class Gasto(models.Model):
    descripcion = models.CharField(max_length=200)
    monto       = models.DecimalField(max_digits=10, decimal_places=2)
    fecha       = models.DateField(auto_now_add=True)
    categoria   = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    usuario     = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.descripcion


class Presupuesto(models.Model):
    categoria    = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    monto_limite = models.DecimalField(max_digits=10, decimal_places=2)
    mes          = models.PositiveIntegerField()
    anio         = models.PositiveIntegerField()
    usuario      = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.categoria} - {self.mes}/{self.anio}"


class ObjetivoAhorro(models.Model):
    nombre         = models.CharField(max_length=120)
    monto_objetivo = models.DecimalField(max_digits=10, decimal_places=2)
    monto_ahorrado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_objetivo = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateField(auto_now_add=True)
    usuario        = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - ${self.monto_objetivo}"
