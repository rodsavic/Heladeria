# Integración con FacturaSend / SIFEN

Documento de lo que se agregó para cumplir los "Requisitos de Cambios" de
FacturaSend y lo que falta para que la facturación electrónica funcione de
punta a punta. Referencia de la fuente de los requisitos:

- https://facturasend.com.py/documentacion/requisitos-de-cambios/
- https://facturasend.com.py/documentacion/tablas-y-definiciones/
- https://facturasend.com.py/documentacion/crear-un-nuevo-documento-electronico/
- https://facturasend.com.py/documentacion/estructura-json-de-un-de/
- https://facturasend.com.py/documentacion/obtener-estado-actual-de-un-documento-electronico/
- https://facturasend.com.py/documentacion/evento-de-cancelacion/

Todo lo de este documento está sin commitear todavía (rama `update-django`);
conviene revisar el diff y commitear antes de seguir.

## 1. Qué se agregó

### 1.1 Parámetros del sistema

[apps/configuracion/models.py](../apps/configuracion/models.py) (`ConfiguracionEmpresa`):

| Campo | Tipo | Notas |
|---|---|---|
| `facturasend_url` | texto | Ej: `https://api.facturasend.com.py/<tenantId>` |
| `facturasend_api_key` | texto | Se guarda **en texto plano** (ver Pendientes) |
| `facturasend_sincrono` | booleano | Falso por defecto |

Editable desde `/configuracion/empresa/` (solo superusuario).

### 1.2 Clientes

[apps/clientes/models.py](../apps/clientes/models.py):

| Campo | Notas |
|---|---|
| `nombre_fantasia` | opcional |
| `es_proveedor_estado` | booleano |
| `es_contribuyente` | agregado para poder calcular el tipo de operación (el documento es un RUC) |
| `es_persona_juridica` | idem |
| `tipo_documento` | 1 Cédula paraguaya, 2 Pasaporte, 3 Cédula extranjera, 4 Carnet de residencia, 5 Innominado, 6 Tarjeta diplomática, 9 Otro |
| `numero_casa` | default 0 |
| `id_ciudad` | FK a `catalogos.Ciudad` |
| `pais` | FK a `catalogos.Pais` (ISO 3166, 3 letras) |
| `tipo_operacion` | B2B/B2C/B2G/B2F, se recalcula solo en `Cliente.save()` |

Regla de `tipo_operacion` (`Cliente.calcular_tipo_operacion`):
`es_proveedor_estado` → B2G; si no, tipo de documento extranjero → B2F; si no,
`es_contribuyente and es_persona_juridica` → B2B; si no, B2C.

El formulario ([apps/clientes/forms.py](../apps/clientes/forms.py)) agrega un
selector de Departamento → Distrito → Ciudad en cascada (ver 1.4), vía dos
endpoints JSON nuevos en `/catalogos/`.

### 1.3 Usuarios

`cargo` (texto libre) en `Usuario` y en `User`
([apps/usuarios/models.py](../apps/usuarios/models.py)), expuesto en los
formularios de alta y edición.

### 1.4 Catálogos nuevos (app `apps.catalogos`)

Modelos: `Pais` (ISO 3166-1, PK de 3 letras), `Moneda` (ISO 4217),
`Departamento` → `Distrito` → `Ciudad` (códigos SIFEN).

**Carga de datos** — comando
[`cargar_catalogos`](../apps/catalogos/management/commands/cargar_catalogos.py):

```bash
python manage.py migrate
python manage.py cargar_catalogos
```

Es idempotente (usa `update_or_create`). Fuentes de los CSV en
[apps/catalogos/data/](../apps/catalogos/data/):

- `paises.csv` / `monedas.csv`: generados con la librería `pycountry`
  (nombres en español). No quedó agregada a `requirements.txt` porque solo
  se usó una vez para generar los CSV; si hace falta regenerarlos, instalarla
  aparte.
- `ubicaciones.csv`: exportado del Google Sheet de FacturaSend
  (departamento/distrito/ciudad).
- `unidades_medida.csv`: exportado del Google Sheet de unidades de la SET
  que cita la documentación de FacturaSend.

El comando también asigna `codigo_set` (ver 1.5) a las medidas existentes
por prefijo (`U`→77, `KG`→83, `GR`→86, `ML`→88, `L`→89). Las medidas que se
creen después no se les asigna automáticamente.

### 1.5 Unidades de medida

`Medida.codigo_set` en [apps/productos/models.py](../apps/productos/models.py):
código numérico de la tabla de la SET. Opcional, sin validación de que sea
uno de los ~60 códigos válidos.

### 1.6 Factura / CDC / estado SIFEN

[apps/factura/models.py](../apps/factura/models.py) (`Factura`):

| Campo | Notas |
|---|---|
| `cdc` | 44 caracteres, indexado |
| `estado_sifen` | -1 Borrador (default), 0 Generado, 1 Enviado en lote, 2 Aprobado, 3 Aprobado con observación, 4 Rechazado, 98 Inexistente, 99 Cancelado |
| `respuesta_sifen` | último JSON de respuesta de FacturaSend (texto libre, para depurar) |

El campo `estado` existente (EMITIDA/ANULADA) no se tocó; `estado_sifen` es
un dato aparte, específico de la integración.

### 1.7 Cliente HTTP a FacturaSend

Tres archivos nuevos en `apps/factura/`, sin agregar dependencias (usan
`urllib`, de la librería estándar, no `requests`):

- **[facturasend_client.py](../apps/factura/facturasend_client.py)** —
  `FacturaSendClient`: habla HTTP con la API. Métodos: `crear_documento`
  (`POST /lote/create`), `consultar_estado` (`POST /de/estado/<id>/<cdc>`),
  `cancelar` (`POST /evento/cancelacion`). Header `Authorization: Bearer
  api_key_<tu api key>` según la documentación de FacturaSend.
- **[facturasend_payload.py](../apps/factura/facturasend_payload.py)** —
  `construir_documento(factura)`: arma el JSON de un DE (Documento
  Electrónico) a partir de la `Factura`, su `Venta`, el `Cliente` y los
  `VentaDetalle`. Solo cubre `tipoDocumento=1` (Factura electrónica), al
  contado o a crédito simple, items gravados por IVA 5/10%. Levanta
  `PayloadError` con un mensaje legible si falta un dato obligatorio (ciudad
  del cliente, código SET de la medida, etc.).
- **[facturasend_service.py](../apps/factura/facturasend_service.py)** —
  `enviar_documento(factura, configuracion)` y
  `cancelar_documento(factura, configuracion, motivo)`: orquestan payload +
  cliente HTTP, interpretan la respuesta y actualizan `cdc`, `estado_sifen`
  y `respuesta_sifen` en la propia `Factura`. Nunca lanzan una excepción
  hacia la vista: cualquier error (de datos, de red o de SIFEN) se guarda en
  `respuesta_sifen` y se devuelve como `(False, mensaje)`, para que un
  problema de la integración no tire abajo la emisión local de la factura.

**Enganche en las vistas**
([apps/factura/views.py](../apps/factura/views.py)):

- `emitirFacturaView`: si `facturasend_url` y `facturasend_api_key` están
  configurados:
  - `facturasend_sincrono = True` → llama a `enviar_documento` en el mismo
    request y muestra el resultado (éxito o advertencia).
  - `facturasend_sincrono = False` → no llama a nada; la factura queda con
    `cdc=''` y el envío real lo hace el comando de abajo.
- `anularFacturaView`: si la factura ya tiene `cdc`, llama al evento de
  cancelación en FacturaSend antes de confirmar la anulación local.

**Envío asíncrono** —
[`enviar_facturasend`](../apps/factura/management/commands/enviar_facturasend.py):

```bash
python manage.py enviar_facturasend
```

Busca facturas emitidas sin `cdc` y las envía una por una. Pensado para
una tarea programada (cron / Programador de tareas de Windows) cada pocos
minutos cuando `facturasend_sincrono=False`.

## 2. Cómo probar sin tocar la base real

**Importante, dejado como lección de esta sesión:** sobreescribir
`settings.DATABASES['default']` **después** de `django.setup()` no
funciona en Django 5.2 — algo durante el arranque ya deja cacheada una
conexión a la base real, y las pruebas "en memoria" terminan escribiendo en
el Postgres local de verdad. Así se contaminó la base `heladeria` en dos
sesiones seguidas (clientes, ventas y catálogos de prueba), y hubo que
limpiarla a mano.

La forma que sí aísla de verdad es fijar un settings module distinto
**antes** de `django.setup()`. Por eso se agregó
[core/settings_test.py](../core/settings_test.py):

```python
from .settings import *  # noqa
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
```

Uso:

```bash
set DJANGO_SETTINGS_MODULE=core.settings_test   # PowerShell: $env:DJANGO_SETTINGS_MODULE='core.settings_test'
python manage.py check
python manage.py shell   # o cualquier script de prueba
```

Cualquier prueba ad-hoc futura (propia o de otra persona/IA) contra este
proyecto debería usar este archivo, no editar `settings.DATABASES` a mano.

## 3. Puesta en marcha

1. `python manage.py migrate` — crea las tablas y campos nuevos.
2. `python manage.py cargar_catalogos` — carga países, monedas, ubicaciones
   y asigna `codigo_set` a las medidas existentes.
3. Completar `/configuracion/empresa/` con la URL y la API Key de
   FacturaSend (consola de FacturaSend → ambiente de pruebas primero).
4. Revisar que cada cliente que vaya a facturarse tenga ciudad asignada
   (obligatoria para armar el DE) y, si es contribuyente, que
   `es_contribuyente`/`es_persona_juridica` estén bien marcados.
5. Revisar que las medidas usadas por los productos tengan `codigo_set`.
6. Si se deja `facturasend_sincrono` apagado, programar
   `python manage.py enviar_facturasend` para que corra cada pocos minutos.
7. Probar primero contra el ambiente de pruebas de FacturaSend (tenantId y
   API Key de test), no contra producción.

## 4. Pendiente / limitaciones conocidas

- **No hay reintentos ni alertas**: si `enviar_facturasend` falla, el único
  rastro es `respuesta_sifen` y la salida del comando; no hay backoff ni
  aviso (email, Slack, etc.) si una factura queda atascada.
- **No se consulta el estado final en SIFEN**: `enviar_documento` guarda el
  estado que devuelve `/lote/create` (normalmente "0-Generado"), pero el
  estado real (Aprobado/Rechazado) llega después. Falta un paso que llame a
  `consultar_estado` periódicamente para las facturas en estado "Generado"
  o "Enviado en lote".
- **Moneda fija en PYG**: `Venta` no tiene campo de moneda, así que el
  payload siempre manda `"moneda": "PYG"`. El catálogo `Moneda` ya existe
  pero no está enganchado a `Venta`.
- **Mapeo de forma de pago aproximado**: `TipoPago` es texto libre
  ("Efectivo", "POS", "Transferencia"); el mapeo a los códigos de SIFEN en
  `facturasend_payload.TIPO_PAGO_SIFEN` asume que "POS" es tarjeta de
  crédito. Confirmar con el negocio si corresponde a crédito o débito.
- **IVA exento no soportado realmente**: solo existen las tasas 5% y 10% en
  la tabla `Iva`; el código contempla "exento" (`ivaTipo=4`) pero no hay
  forma de crear un producto exento desde la UI actual.
- **`codigo_set` sin UI**: el formulario de productos no permite elegir la
  unidad de medida SET; solo se asignó a las medidas que ya existían al
  correr `cargar_catalogos`. Una medida nueva necesita que alguien le ponga
  el código a mano (shell o admin).
- **`presencia` de la factura fija en 1** (operación presencial) — no hay
  forma de marcar ventas no presenciales (telemarketing, a domicilio, etc.).
- **Un solo establecimiento/punto de expedición**: no hay soporte para
  múltiples sucursales o puntos de venta.
- **API Key en texto plano** en `ConfiguracionEmpresa` (visible en el admin
  y en la base). Si esto va a producción, conviene moverla a una variable
  de entorno o cifrarla.
- **Sin notas de crédito/débito ni nota de remisión**: `facturasend_payload`
  solo construye `tipoDocumento=1` (Factura).
- **Sin XML/KUDE**: no se descarga ni se muestra el PDF/KUDE del documento
  aprobado; solo se guarda el CDC.
- **No se corrigió la deduplicación de medidas** en el archivo
  `INSERT_TABLAS.sql` / datos semilla: si el proyecto se reinstala desde
  cero con ese script y luego se corre `cargar_catalogos`, revisar que no
  queden medidas duplicadas (pasó una vez en la base de desarrollo, ver
  sección 2).

## 5. Archivos nuevos y modificados

**Nuevos:**
- `apps/catalogos/` (app completa: modelos, admin, urls, views, comando
  `cargar_catalogos`, datos CSV)
- `apps/factura/facturasend_client.py`
- `apps/factura/facturasend_payload.py`
- `apps/factura/facturasend_service.py`
- `apps/factura/management/commands/enviar_facturasend.py`
- `core/settings_test.py`
- `docs/facturasend.md` (este archivo)

**Modificados:** `apps/clientes/{models,forms,views}.py`,
`apps/usuarios/{models,views}.py`, `apps/configuracion/{models,views}.py`,
`apps/productos/models.py`, `apps/factura/{models,views}.py`,
`core/{settings,urls}.py`, templates de clientes/usuarios/configuración.
