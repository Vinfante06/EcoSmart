from django import forms

from .models import Categoria, Gasto, Ingreso, ObjetivoAhorro, Presupuesto


class FormularioConUsuarioMixin:
    """Guarda el usuario actual para limitar datos y asociar registros."""

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)


class CategoriaForm(FormularioConUsuarioMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre"]
        labels = {"nombre": "Nombre de la categoría"}
        error_messages = {
            "nombre": {"required": "Debes escribir el nombre de la categoría."},
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if not nombre:
            raise forms.ValidationError("Debes escribir el nombre de la categoría.")

        repetida = Categoria.objects.filter(nombre__iexact=nombre, usuario=self.usuario)
        if self.instance.pk:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError("Ya tienes una categoría con ese nombre.")
        return nombre

    def save(self, commit=True):
        categoria = super().save(commit=False)
        categoria.usuario = self.usuario
        if commit:
            categoria.save()
        return categoria


class MovimientoFormBase(FormularioConUsuarioMixin, forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        empty_label="Sin categoría",
        label="Categoría",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(
            usuario=self.usuario
        ).order_by("nombre")

    def clean_descripcion(self):
        descripcion = self.cleaned_data["descripcion"].strip()
        if not descripcion:
            raise forms.ValidationError("Debes escribir una descripción.")
        return descripcion

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor que 0.")
        return monto

    def save(self, commit=True):
        movimiento = super().save(commit=False)
        movimiento.usuario = self.usuario
        if commit:
            movimiento.save()
            self.save_m2m()
        return movimiento


class IngresoForm(MovimientoFormBase):
    class Meta:
        model = Ingreso
        fields = ["descripcion", "monto", "categoria"]
        labels = {
            "descripcion": "Descripción",
            "monto": "Monto",
            "categoria": "Categoría",
        }
        error_messages = {
            "descripcion": {"required": "Debes escribir una descripción."},
            "monto": {
                "required": "Debes escribir el monto del ingreso.",
                "invalid": "El monto del ingreso no es válido.",
            },
        }


class GastoForm(MovimientoFormBase):
    class Meta:
        model = Gasto
        fields = ["descripcion", "monto", "categoria"]
        labels = {
            "descripcion": "Descripción",
            "monto": "Monto",
            "categoria": "Categoría",
        }
        error_messages = {
            "descripcion": {"required": "Debes escribir una descripción."},
            "monto": {
                "required": "Debes escribir el monto del gasto.",
                "invalid": "El monto del gasto no es válido.",
            },
        }


class PresupuestoForm(FormularioConUsuarioMixin, forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=True,
        label="Categoría",
        empty_label="Selecciona una categoría",
    )

    class Meta:
        model = Presupuesto
        fields = ["categoria", "monto_limite", "mes", "anio"]
        labels = {
            "categoria": "Categoría",
            "monto_limite": "Monto límite",
            "mes": "Mes",
            "anio": "Año",
        }
        error_messages = {
            "categoria": {"required": "Debes seleccionar una categoría."},
            "monto_limite": {
                "required": "Debes escribir el límite del presupuesto.",
                "invalid": "El límite del presupuesto no es válido.",
            },
            "mes": {
                "required": "Debes escribir el mes.",
                "invalid": "El mes debe ser un número entre 1 y 12.",
            },
            "anio": {
                "required": "Debes escribir el año.",
                "invalid": "El año debe ser un número válido.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(
            usuario=self.usuario
        ).order_by("nombre")

    def clean_monto_limite(self):
        monto_limite = self.cleaned_data["monto_limite"]
        if monto_limite <= 0:
            raise forms.ValidationError("El límite debe ser mayor que 0.")
        return monto_limite

    def clean_mes(self):
        mes = self.cleaned_data["mes"]
        if mes < 1 or mes > 12:
            raise forms.ValidationError("El mes debe estar entre 1 y 12.")
        return mes

    def clean_anio(self):
        anio = self.cleaned_data["anio"]
        if anio < 2000 or anio > 2100:
            raise forms.ValidationError("El año debe estar entre 2000 y 2100.")
        return anio

    def save(self, commit=True):
        presupuesto = super().save(commit=False)
        presupuesto.usuario = self.usuario
        if commit:
            presupuesto.save()
        return presupuesto


class ObjetivoAhorroForm(FormularioConUsuarioMixin, forms.ModelForm):
    class Meta:
        model = ObjetivoAhorro
        fields = ["nombre", "monto_objetivo", "fecha_objetivo"]
        labels = {
            "nombre": "Nombre del objetivo",
            "monto_objetivo": "Monto objetivo",
            "fecha_objetivo": "Fecha objetivo",
        }
        error_messages = {
            "nombre": {"required": "Debes escribir el nombre del objetivo."},
            "monto_objetivo": {
                "required": "Debes escribir el monto objetivo.",
                "invalid": "El monto objetivo no es válido.",
            },
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if not nombre:
            raise forms.ValidationError("Debes escribir el nombre del objetivo.")
        return nombre

    def clean_monto_objetivo(self):
        monto_objetivo = self.cleaned_data["monto_objetivo"]
        if monto_objetivo <= 0:
            raise forms.ValidationError("El monto objetivo debe ser mayor que 0.")
        return monto_objetivo

    def save(self, commit=True):
        objetivo = super().save(commit=False)
        objetivo.usuario = self.usuario
        if commit:
            objetivo.save()
        return objetivo


class AbonoAhorroForm(FormularioConUsuarioMixin, forms.Form):
    objetivo_id = forms.IntegerField(
        required=True,
        error_messages={"required": "Debes indicar el objetivo de ahorro."},
    )
    abono = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        error_messages={
            "required": "Debes escribir el monto del abono.",
            "invalid": "El monto del abono no es válido.",
        },
    )

    def clean_abono(self):
        abono = self.cleaned_data["abono"]
        if abono <= 0:
            raise forms.ValidationError("El abono debe ser mayor que 0.")
        return abono

    def clean_objetivo_id(self):
        objetivo_id = self.cleaned_data["objetivo_id"]
        try:
            return ObjetivoAhorro.objects.get(id=objetivo_id, usuario=self.usuario)
        except ObjetivoAhorro.DoesNotExist as exc:
            raise forms.ValidationError("El objetivo seleccionado no existe.") from exc

    def guardar(self):
        objetivo = self.cleaned_data["objetivo_id"]
        objetivo.monto_ahorrado += self.cleaned_data["abono"]
        objetivo.save(update_fields=["monto_ahorrado"])
        return objetivo


class FiltroHistorialForm(FormularioConUsuarioMixin, forms.Form):
    tipo = forms.ChoiceField(
        required=False,
        choices=[("", "Todos"), ("ingreso", "Ingresos"), ("gasto", "Gastos")],
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        empty_label="Todas las categorías",
    )
    desde = forms.DateField(required=False)
    hasta = forms.DateField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(
            usuario=self.usuario
        ).order_by("nombre")

    def clean(self):
        cleaned_data = super().clean()
        desde = cleaned_data.get("desde")
        hasta = cleaned_data.get("hasta")
        if desde and hasta and desde > hasta:
            raise forms.ValidationError("La fecha inicial no puede ser mayor que la final.")
        return cleaned_data


class PeriodoReporteForm(forms.Form):
    mes = forms.IntegerField(min_value=1, max_value=12, required=False)
    anio = forms.IntegerField(min_value=2000, max_value=2100, required=False)
