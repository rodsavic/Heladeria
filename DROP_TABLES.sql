-- Eliminar las restricciones de claves foráneas primero
ALTER TABLE public.usuario_rol DROP CONSTRAINT usuarios_usuario_rol_fk;
ALTER TABLE public.usuario_rol DROP CONSTRAINT roles_usuario_rol_fk;
ALTER TABLE public.rol_permiso DROP CONSTRAINT roles_rol_permiso_fk;
ALTER TABLE public.rol_permiso DROP CONSTRAINT permisos_rol_permiso_fk;

-- Eliminar las tablas en orden
DROP TABLE IF EXISTS public.usuario_rol CASCADE;
DROP TABLE IF EXISTS public.rol_permiso CASCADE;
DROP TABLE IF EXISTS public.usuarios CASCADE;
DROP TABLE IF EXISTS public.roles CASCADE;
DROP TABLE IF EXISTS public.permisos CASCADE;

-- Eliminar las secuencias
DROP SEQUENCE IF EXISTS public.usuario_rol_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.rol_permiso_id_seq CASCADE;
DROP SEQUENCE IF EXISTS public.usuarios_id_usuario_seq CASCADE;
DROP SEQUENCE IF EXISTS public.roles_id_rol_seq CASCADE;
DROP SEQUENCE IF EXISTS public.permisos_id_permiso_seq CASCADE;
