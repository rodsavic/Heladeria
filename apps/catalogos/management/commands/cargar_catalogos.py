import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogos.models import Ciudad, Departamento, Distrito, Moneda, Pais
from apps.productos.models import Medida

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

# Codigos de unidad de medida de la SET para las medidas que ya usa el sistema (por prefijo).
CODIGO_SET_POR_PREFIJO = {
    'U': 77,
    'UNI': 77,
    'KG': 83,
    'GR': 86,
    'ML': 88,
    'L': 89,
}


def leer_csv(nombre):
    with open(DATA_DIR / nombre, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


class Command(BaseCommand):
    help = 'Carga paises (ISO 3166), monedas (ISO 4217) y ubicaciones SIFEN. Se puede ejecutar varias veces.'

    @transaction.atomic
    def handle(self, *args, **options):
        for fila in leer_csv('paises.csv'):
            Pais.objects.update_or_create(codigo=fila['codigo'], defaults={'nombre': fila['nombre']})

        for fila in leer_csv('monedas.csv'):
            Moneda.objects.update_or_create(codigo=fila['codigo'], defaults={'descripcion': fila['descripcion']})

        departamentos, distritos, ciudades = {}, {}, {}
        for fila in leer_csv('ubicaciones.csv'):
            departamentos[int(fila['dep_codigo'])] = fila['dep_descripcion']
            distritos[int(fila['dis_codigo'])] = (fila['dis_descripcion'], int(fila['dep_codigo']))
            ciudades[int(fila['ciu_codigo'])] = (fila['ciu_descripcion'], int(fila['dis_codigo']))

        for codigo, descripcion in departamentos.items():
            Departamento.objects.update_or_create(codigo=codigo, defaults={'descripcion': descripcion})
        for codigo, (descripcion, dep) in distritos.items():
            Distrito.objects.update_or_create(codigo=codigo, defaults={'descripcion': descripcion, 'departamento_id': dep})
        for codigo, (descripcion, dis) in ciudades.items():
            Ciudad.objects.update_or_create(codigo=codigo, defaults={'descripcion': descripcion, 'distrito_id': dis})

        asignadas = 0
        for prefijo, codigo in CODIGO_SET_POR_PREFIJO.items():
            asignadas += Medida.objects.filter(prefijo__iexact=prefijo, codigo_set__isnull=True).update(codigo_set=codigo)

        self.stdout.write(self.style.SUCCESS(
            f'Paises: {Pais.objects.count()}, monedas: {Moneda.objects.count()}, '
            f'departamentos: {len(departamentos)}, distritos: {len(distritos)}, ciudades: {len(ciudades)}, '
            f'medidas con codigo SET asignado: {asignadas}'
        ))
