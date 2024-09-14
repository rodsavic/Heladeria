from django.db import models

class Medida(models.Model):
    id_medida = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100,db_column='descripcion' ,null=False)
    prefijo = models.CharField(max_length=20, db_column='prefijo', null=False)

    class Meta:
        managed = False
        db_table = 'medidas'
        verbose_name = 'Medida'
        verbose_name_plural = 'Medidas'

    def __str__(self):
        return f'idMedida: {self.id_medida}, descripcion: {self.descripcion}, prefijo{self.prefijo}'


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=50, db_column='descripcion', null=False)

    class Meta:
        managed = False
        db_table = 'categoria'
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return f'idCategoria: {self.id_categoria}, descripcion: {self.descripcion}'


class Iva(models.Model):
    id_iva = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=10,db_column='descripcion', null=False)

    class Meta:
        managed = False
        db_table = 'iva'
        verbose_name = 'Iva'
        verbose_name_plural = 'Ivas'

    def __str__(self):
        return f'idIva: {self.id_iva}, descripcion: {self.descripcion}'

class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, db_column='nombre', null=False)
    precio_actual = models.FloatField(db_column='precio_actual', null=False)
    stock_minimo = models.IntegerField(db_column='stock_minimo', null=True)
    stock_actual = models.IntegerField(db_column='stock_actual', null=True)
    vencimiento = models.DateField(db_column='vencimiento', null=True)
    costo_actual = models.FloatField(db_column='costo_actual', null=True)
    usuario_creacion = models.IntegerField(db_column='usuario_creacion', null=True)
    usuario_modificacion = models.IntegerField(db_column='usuario_modificacion', null=True)
    fecha_creacion = models.DateTimeField(db_column='fecha_creacion', auto_now_add=True)
    fecha_modificacion = models.DateTimeField(db_column='fecha_modificacion', null=True)
    id_medida = models.ForeignKey(Medida, models.DO_NOTHING, db_column='id_medida', null=False)
    id_iva = models.ForeignKey(Iva, models.DO_NOTHING, db_column='id_iva', null=False)

    class Meta:
        managed = False
        db_table = 'productos'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f'idProducto: {self.id_producto}, nombre: {self.nombre}, precioActual: {self.precio_actual}, usuarioCreacion: {self.usuario_creacion}, id_iva: {self.id_iva}'


class CategoriaProducto(models.Model):
    id_tipo_producto = models.AutoField(primary_key=True)
    id_categoria = models.ForeignKey(Categoria, models.DO_NOTHING, db_column='id_categoria', null=False)
    id_producto = models.ForeignKey(Producto, models.DO_NOTHING, db_column='id_producto', null=False)

    class Meta:
        managed = False
        db_table = 'categoria_producto'
        verbose_name = 'CategoriaProducto'
        verbose_name_plural = 'CategoriasProductos'

    def __str__(self):
        return f' idCategoriaProducto: {self.id_tipo_producto}, idCategoria: {self.id_categoria}, idProducto: {self.id_producto}'


