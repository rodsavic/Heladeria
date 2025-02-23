
CREATE SEQUENCE public.tipo_pago_id_tipo_pago_seq;

CREATE TABLE public.tipo_pago (
                id_tipo_pago BIGINT NOT NULL DEFAULT nextval('public.tipo_pago_id_tipo_pago_seq'),
                descripcion VARCHAR(50) NOT NULL,
                CONSTRAINT tipo_pago_pk PRIMARY KEY (id_tipo_pago)
);


ALTER SEQUENCE public.tipo_pago_id_tipo_pago_seq OWNED BY public.tipo_pago.id_tipo_pago;

CREATE SEQUENCE public.proveedores_id_proveedor_seq;

CREATE TABLE public.proveedores (
                id_proveedor BIGINT NOT NULL DEFAULT nextval('public.proveedores_id_proveedor_seq'),
                documento VARCHAR(50) NOT NULL,
                nombre VARCHAR(255) NOT NULL,
                correo VARCHAR(100),
                telefono VARCHAR(100) NOT NULL,
                usuario_creacion INTEGER NOT NULL,
                direccion VARCHAR(255) NOT NULL,
                estado VARCHAR(15) NOT NULL,
                usuario_modificacion INTEGER,
                fecha_creacion TIMESTAMP DEFAULT now() NOT NULL,
                fecha_modificacion TIMESTAMP NOT NULL,
                CONSTRAINT proveedores_pk PRIMARY KEY (id_proveedor)
);


ALTER SEQUENCE public.proveedores_id_proveedor_seq OWNED BY public.proveedores.id_proveedor;

CREATE SEQUENCE public.compras_id_compra_seq;

CREATE TABLE public.compras (
                id_compra BIGINT NOT NULL DEFAULT nextval('public.compras_id_compra_seq'),
                id_proveedor BIGINT NOT NULL,
                fecha_compra TIMESTAMP DEFAULT now() NOT NULL,
                total_iva_10 REAL NOT NULL,
                total_compra REAL NOT NULL,
                total_iva_5 REAL NOT NULL,
                usuario_creacion BIGINT NOT NULL,
                CONSTRAINT compras_pk PRIMARY KEY (id_compra)
);


ALTER SEQUENCE public.compras_id_compra_seq OWNED BY public.compras.id_compra;

CREATE SEQUENCE public.categoria_id_categoria_seq;

CREATE TABLE public.categoria (
                id_categoria BIGINT NOT NULL DEFAULT nextval('public.categoria_id_categoria_seq'),
                descripcion VARCHAR(50) NOT NULL,
                CONSTRAINT categoria_pk PRIMARY KEY (id_categoria)
);


ALTER SEQUENCE public.categoria_id_categoria_seq OWNED BY public.categoria.id_categoria;

CREATE SEQUENCE public.clientes_id_cliente_seq;

CREATE TABLE public.clientes (
                id_cliente BIGINT NOT NULL DEFAULT nextval('public.clientes_id_cliente_seq'),
                documento VARCHAR(16) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                apellido VARCHAR(100) NOT NULL,
                correo VARCHAR(100) NOT NULL,
                celular VARCHAR(50) NOT NULL,
                direccion VARCHAR(255),
                estado VARCHAR NOT NULL,
                CONSTRAINT clientes_pk PRIMARY KEY (id_cliente)
);


ALTER SEQUENCE public.clientes_id_cliente_seq OWNED BY public.clientes.id_cliente;

CREATE SEQUENCE public.ventas_id_venta_seq;

CREATE TABLE public.ventas (
                id_venta BIGINT NOT NULL DEFAULT nextval('public.ventas_id_venta_seq'),
                fecha_venta TIMESTAMP NOT NULL,
                total_iva_10 REAL NOT NULL,
                total_iva_5 REAL NOT NULL,
                total_venta REAL NOT NULL,
                usuario_creacion BIGINT NOT NULL,
                id_cliente BIGINT NOT NULL,
                id_tipo_pago BIGINT NOT NULL,
                CONSTRAINT ventas_pk PRIMARY KEY (id_venta)
);


ALTER SEQUENCE public.ventas_id_venta_seq OWNED BY public.ventas.id_venta;

CREATE SEQUENCE public.ventas_tipo_de_pago_id_venta_tipo_pago_seq;

CREATE TABLE public.ventas_tipo_de_pago (
                id_venta_tipo_pago BIGINT NOT NULL DEFAULT nextval('public.ventas_tipo_de_pago_id_venta_tipo_pago_seq'),
                monto INTEGER NOT NULL,
                id_tipo_pago BIGINT NOT NULL,
                id_venta BIGINT NOT NULL,
                CONSTRAINT ventas_tipo_de_pago_pk PRIMARY KEY (id_venta_tipo_pago)
);


ALTER SEQUENCE public.ventas_tipo_de_pago_id_venta_tipo_pago_seq OWNED BY public.ventas_tipo_de_pago.id_venta_tipo_pago;

CREATE SEQUENCE public.iva_id_iva_seq;

CREATE TABLE public.iva (
                id_iva BIGINT NOT NULL DEFAULT nextval('public.iva_id_iva_seq'),
                descripcion REAL NOT NULL,
                CONSTRAINT iva_pk PRIMARY KEY (id_iva)
);


ALTER SEQUENCE public.iva_id_iva_seq OWNED BY public.iva.id_iva;

CREATE SEQUENCE public.medidas_id_medida_seq;

CREATE TABLE public.medidas (
                id_medida BIGINT NOT NULL DEFAULT nextval('public.medidas_id_medida_seq'),
                prefijo VARCHAR(20) NOT NULL,
                descripcion VARCHAR NOT NULL,
                CONSTRAINT medidas_pk PRIMARY KEY (id_medida)
);


ALTER SEQUENCE public.medidas_id_medida_seq OWNED BY public.medidas.id_medida;

CREATE SEQUENCE public.productos_id_producto_seq;

CREATE TABLE public.productos (
                id_producto BIGINT NOT NULL DEFAULT nextval('public.productos_id_producto_seq'),
                nombre VARCHAR(100) NOT NULL,
                precio_actual REAL NOT NULL,
                stock_minimo INTEGER,
                stock_actual INTEGER,
                vencimiento DATE,
                usuario_creacion INTEGER,
                costo_actual REAL,
                usuario_modificacion INTEGER,
                fecha_creacion TIMESTAMP DEFAULT now(),
                fecha_modificacion TIMESTAMP,
                id_medida BIGINT NOT NULL,
                id_iva BIGINT NOT NULL,
                CONSTRAINT productos_pk PRIMARY KEY (id_producto)
);


ALTER SEQUENCE public.productos_id_producto_seq OWNED BY public.productos.id_producto;

CREATE SEQUENCE public.compra_detalle_id_detalle_seq;

CREATE TABLE public.compra_detalle (
                id_detalle BIGINT NOT NULL DEFAULT nextval('public.compra_detalle_id_detalle_seq'),
                id_compra BIGINT NOT NULL,
                id_producto BIGINT NOT NULL,
                total_detalle REAL NOT NULL,
                cantidad_producto REAL NOT NULL,
                CONSTRAINT compra_detalle_pk PRIMARY KEY (id_detalle)
);


ALTER SEQUENCE public.compra_detalle_id_detalle_seq OWNED BY public.compra_detalle.id_detalle;

CREATE SEQUENCE public.venta_detalle_id_detalle_seq;

CREATE TABLE public.venta_detalle (
                id_detalle BIGINT NOT NULL DEFAULT nextval('public.venta_detalle_id_detalle_seq'),
                total_detalle REAL NOT NULL,
                cantidad_producto REAL NOT NULL,
                id_venta BIGINT NOT NULL,
                id_producto BIGINT NOT NULL,
                CONSTRAINT venta_detalle_pk PRIMARY KEY (id_detalle)
);


ALTER SEQUENCE public.venta_detalle_id_detalle_seq OWNED BY public.venta_detalle.id_detalle;

CREATE SEQUENCE public.categoria_producto_id_tipo_producto_seq;

CREATE TABLE public.categoria_producto (
                id_tipo_producto BIGINT NOT NULL DEFAULT nextval('public.categoria_producto_id_tipo_producto_seq'),
                id_categoria BIGINT NOT NULL,
                id_producto BIGINT NOT NULL,
                CONSTRAINT categoria_producto_pk PRIMARY KEY (id_tipo_producto)
);


ALTER SEQUENCE public.categoria_producto_id_tipo_producto_seq OWNED BY public.categoria_producto.id_tipo_producto;

CREATE SEQUENCE public.permisos_id_permiso_seq;

CREATE TABLE public.permisos (
                id_permiso BIGINT NOT NULL DEFAULT nextval('public.permisos_id_permiso_seq'),
                descripcion VARCHAR(100) NOT NULL,
                CONSTRAINT permisos_pk PRIMARY KEY (id_permiso)
);


ALTER SEQUENCE public.permisos_id_permiso_seq OWNED BY public.permisos.id_permiso;

CREATE SEQUENCE public.roles_id_rol_seq;

CREATE TABLE public.roles (
                id_rol BIGINT NOT NULL DEFAULT nextval('public.roles_id_rol_seq'),
                descripcion VARCHAR(100) NOT NULL,
                CONSTRAINT roles_pk PRIMARY KEY (id_rol)
);


ALTER SEQUENCE public.roles_id_rol_seq OWNED BY public.roles.id_rol;

CREATE SEQUENCE public.rol_permiso_id_seq;

CREATE TABLE public.rol_permiso (
                id BIGINT NOT NULL DEFAULT nextval('public.rol_permiso_id_seq'),
                id_permiso BIGINT NOT NULL,
                id_rol BIGINT NOT NULL,
                CONSTRAINT rol_permiso_pk PRIMARY KEY (id)
);


ALTER SEQUENCE public.rol_permiso_id_seq OWNED BY public.rol_permiso.id;

CREATE SEQUENCE public.usuarios_id_usuario_seq;

CREATE TABLE public.usuarios (
                id_usuario BIGINT NOT NULL DEFAULT nextval('public.usuarios_id_usuario_seq'),
                nombre VARCHAR(50) NOT NULL,
                nombre_usuario VARCHAR(16) NOT NULL,
                documento VARCHAR(20) NOT NULL,
                usuario_creacion BIGINT,
                usuario_modificacion BIGINT,
                fecha_creacion TIMESTAMP DEFAULT now(),
                contrasena VARCHAR(255) NOT NULL,
                fecha_modificacion TIMESTAMP,
                apellido VARCHAR(50) NOT NULL,
                CONSTRAINT usuarios_pk PRIMARY KEY (id_usuario)
);


ALTER SEQUENCE public.usuarios_id_usuario_seq OWNED BY public.usuarios.id_usuario;

CREATE SEQUENCE public.usuario_rol_id_seq;

CREATE TABLE public.usuario_rol (
                id BIGINT NOT NULL DEFAULT nextval('public.usuario_rol_id_seq'),
                id_rol BIGINT NOT NULL,
                id_usuario BIGINT NOT NULL,
                CONSTRAINT usuario_rol_pk PRIMARY KEY (id)
);


ALTER SEQUENCE public.usuario_rol_id_seq OWNED BY public.usuario_rol.id;

ALTER TABLE public.ventas ADD CONSTRAINT tipo_pago_ventas_fk
FOREIGN KEY (id_tipo_pago)
REFERENCES public.tipo_pago (id_tipo_pago)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.ventas_tipo_de_pago ADD CONSTRAINT tipo_pago_ventas_tipo_de_pago_fk
FOREIGN KEY (id_tipo_pago)
REFERENCES public.tipo_pago (id_tipo_pago)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.compras ADD CONSTRAINT proveedores_compras_fk
FOREIGN KEY (id_proveedor)
REFERENCES public.proveedores (id_proveedor)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.compra_detalle ADD CONSTRAINT compras_compra_detalle_fk
FOREIGN KEY (id_compra)
REFERENCES public.compras (id_compra)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.categoria_producto ADD CONSTRAINT categoria_tipo_producto_fk
FOREIGN KEY (id_categoria)
REFERENCES public.categoria (id_categoria)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.ventas ADD CONSTRAINT clientes_ventas_fk
FOREIGN KEY (id_cliente)
REFERENCES public.clientes (id_cliente)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.venta_detalle ADD CONSTRAINT ventas_venta_detalle_fk
FOREIGN KEY (id_venta)
REFERENCES public.ventas (id_venta)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.ventas_tipo_de_pago ADD CONSTRAINT ventas_ventas_tipo_de_pago_fk
FOREIGN KEY (id_venta)
REFERENCES public.ventas (id_venta)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.productos ADD CONSTRAINT iva_productos_fk
FOREIGN KEY (id_iva)
REFERENCES public.iva (id_iva)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.productos ADD CONSTRAINT medidas_productos_fk
FOREIGN KEY (id_medida)
REFERENCES public.medidas (id_medida)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.categoria_producto ADD CONSTRAINT productos_tipo_producto_fk
FOREIGN KEY (id_producto)
REFERENCES public.productos (id_producto)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.venta_detalle ADD CONSTRAINT productos_venta_detalle_fk
FOREIGN KEY (id_producto)
REFERENCES public.productos (id_producto)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.compra_detalle ADD CONSTRAINT productos_compra_detalle_fk
FOREIGN KEY (id_producto)
REFERENCES public.productos (id_producto)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.rol_permiso ADD CONSTRAINT permisos_rol_permiso_fk
FOREIGN KEY (id_permiso)
REFERENCES public.permisos (id_permiso)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.rol_permiso ADD CONSTRAINT roles_rol_permiso_fk
FOREIGN KEY (id_rol)
REFERENCES public.roles (id_rol)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.usuario_rol ADD CONSTRAINT roles_usuario_rol_fk
FOREIGN KEY (id_rol)
REFERENCES public.roles (id_rol)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;

ALTER TABLE public.usuario_rol ADD CONSTRAINT usuarios_usuario_rol_fk
FOREIGN KEY (id_usuario)
REFERENCES public.usuarios (id_usuario)
ON DELETE NO ACTION
ON UPDATE NO ACTION
NOT DEFERRABLE;