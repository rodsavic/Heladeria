from django.db import models


class Pais(models.Model):
    """Paises segun ISO 3166-1 (codigo de tres letras)."""
    codigo = models.CharField(max_length=3, primary_key=True, db_column='codigo')
    nombre = models.CharField(max_length=100, db_column='nombre')

    class Meta:
        db_table = 'paises'
        verbose_name = 'Pais'
        verbose_name_plural = 'Paises'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class Moneda(models.Model):
    """Monedas segun ISO 4217."""
    codigo = models.CharField(max_length=3, primary_key=True, db_column='codigo')
    descripcion = models.CharField(max_length=100, db_column='descripcion')

    class Meta:
        db_table = 'monedas'
        verbose_name = 'Moneda'
        verbose_name_plural = 'Monedas'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} - {self.descripcion}'


class Departamento(models.Model):
    """Codigo de departamento segun SIFEN."""
    codigo = models.PositiveIntegerField(primary_key=True, db_column='codigo')
    descripcion = models.CharField(max_length=100, db_column='descripcion')

    class Meta:
        db_table = 'departamentos'
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['descripcion']

    def __str__(self):
        return self.descripcion


class Distrito(models.Model):
    """Codigo de distrito segun SIFEN."""
    codigo = models.PositiveIntegerField(primary_key=True, db_column='codigo')
    descripcion = models.CharField(max_length=100, db_column='descripcion')
    departamento = models.ForeignKey(Departamento, models.DO_NOTHING, db_column='departamento', related_name='distritos')

    class Meta:
        db_table = 'distritos'
        verbose_name = 'Distrito'
        verbose_name_plural = 'Distritos'
        ordering = ['descripcion']

    def __str__(self):
        return self.descripcion


class Ciudad(models.Model):
    """Codigo de ciudad segun SIFEN."""
    codigo = models.PositiveIntegerField(primary_key=True, db_column='codigo')
    descripcion = models.CharField(max_length=100, db_column='descripcion')
    distrito = models.ForeignKey(Distrito, models.DO_NOTHING, db_column='distrito', related_name='ciudades')

    class Meta:
        db_table = 'ciudades'
        verbose_name = 'Ciudad'
        verbose_name_plural = 'Ciudades'
        ordering = ['descripcion']

    def __str__(self):
        return self.descripcion
