INSERT INTO categoria (descripcion) VALUES ('MATERIA PRIMA');
INSERT INTO categoria (descripcion) VALUES ('PARA VENTA');

INSERT INTO iva (descripcion) VALUES ('10');
INSERT INTO iva (descripcion) VALUES ('5');

INSERT INTO medidas(prefijo,descripcion) VALUES('KG', 'Kilogramo');
INSERT INTO medidas(prefijo,descripcion) VALUES('ML', 'Mililitros');
INSERT INTO medidas(prefijo,descripcion) VALUES('GR', 'Gramos');
INSERT INTO medidas(prefijo,descripcion) VALUES('L', 'Litros');
INSERT INTO medidas(prefijo,descripcion) VALUES('U', 'Unidad');

INSERT INTO tipo_pago (descripcion) VALUES ('Efectivo');
INSERT INTO tipo_pago (descripcion) VALUES ('POS');
INSERT INTO tipo_pago (descripcion) VALUES ('Transferencia');

INSERT INTO public.productos (
	nombre, precio_actual, stock_minimo, stock_actual, vencimiento, costo_actual, usuario_creacion, usuario_modificacion, fecha_creacion, fecha_modificacion, id_iva, id_medida
) VALUES
('Picole Frutal', 1500, 0, 0, '2024-09-14', 1500, 1, NULL, '2024-09-14 20:15:07.176673', NULL, 1, 5),
('Picole Cremoso', 2500, 0, 0, '2024-09-14', 2500, 1, NULL, '2024-09-14 20:15:34.924843', NULL, 1, 1),
('Picole Bañado', 4000, 0, 0, '2024-09-14', 4000, 1, NULL, '2024-09-14 20:16:06.454299', NULL, 1, 5),
('Paleton', 10000, 0, 0, '2024-09-14', 0, 1, NULL, '2024-09-14 20:16:34.237905', NULL, 1, 5),
('Chupa chup', 4000, 0, 0, '2024-09-14', 4000, 1, NULL, '2024-09-14 20:17:05.675892', NULL, 1, 5),
('Cremoso 1 Bocha', 4000, 0, 0, '2024-09-14', 4000, 1, NULL, '2024-09-14 20:18:14.340081', NULL, 1, 5),
('Cremoso 2 Bochas', 8000, 0, 0, '2024-09-14', 8000, 1, NULL, '2024-09-14 20:18:39.839898', NULL, 1, 5),
('Especial 1 Bocha', 8000, 0, 0, '2024-09-14', 8000, 1, NULL, '2024-09-14 20:19:10.335449', NULL, 1, 5),
('Especial 2 Bochas', 12000, 0, 0, '2024-09-14', 12000, 1, NULL, '2024-09-14 20:19:38.536851', NULL, 1, 5),
('Isopor 1/4', 12000, 0, 0, '2024-09-14', 12000, 1, NULL, '2024-09-14 20:20:32.419752', NULL, 1, 5),
('Isopor 1/2 L', 21000, 0, 0, '2024-09-14', 21000, 1, NULL, '2024-09-14 20:21:15.534639', NULL, 1, 5),
('Isopor 1L', 38000, 0, 0, '2024-09-14', 38000, 1, NULL, '2024-09-14 20:21:45.881979', NULL, 1, 5),
('Isopor especial 1/4L', 17000, 0, 0, '2024-09-14', 17000, 1, NULL, '2024-09-14 20:22:17.085111', NULL, 1, 5),
('Isopor especial 1/2L', 30000, 0, 0, '2024-09-14', 30000, 1, NULL, '2024-09-14 20:22:45.190138', NULL, 1, 5),
('Isopor especial 1L', 50000, 0, 0, '2024-09-14', 50000, 1, NULL, '2024-09-14 20:23:06.975345', NULL, 1, 1),
('Camadiña Tradicional 400 ml', 18000, 0, 0, '2024-09-14', 18000, 1, NULL, '2024-09-14 20:23:46.906548', NULL, 1, 5),
('Camadiña 3 Leches 400 ml', 18000, 0, 0, '2024-09-14', 18000, 1, NULL, '2024-09-14 20:24:32.246769', NULL, 1, 5),
('Camadiña 3 Leches 300 ml', 15000, 0, 0, '2024-09-14', 15000, 1, NULL, '2024-09-14 20:25:04.470423', NULL, 1, 5),
('Camadiña Tradicional 300 ml', 15000, 0, 0, '1999-09-01', 15000, 1, NULL, '2024-09-14 20:25:36.665309', NULL, 1, 5),
('Cono chico', 1000, 0, 0, '2024-09-21', 1000, 1, NULL, '2024-09-21 19:27:17.801051', NULL, 1, 5),
('Frutal Mayorista', 800, 0, 0, '2024-09-21', 800, 1, NULL, '2024-09-21 19:28:57.838511', NULL, 1, 5),
('Cremoso Mayorista', 1400, 0, 0, '2024-09-21', 1400, 1, NULL, '2024-09-21 19:29:28.414275', NULL, 1, 5),
('Helado en balde de 10L', 110000, 0, 0, '2024-09-21', 110000, 1, NULL, '2024-09-21 19:30:09.562004', NULL, 1, 5),
('Alfajor', 5000, 0, 0, '2024-09-21', 5000, 1, NULL, '2024-09-21 19:30:37.820647', NULL, 1, 5),
('Helado en balde de 5L', 55000, 0, 0, '2024-09-21', 55000, 1, NULL, '2024-09-21 19:31:38.954627', NULL, 1, 5),
('Milkshake', 15000, 0, 0, '2024-09-21', 15000, 1, NULL, '2024-09-21 21:27:10.329665', NULL, 1, 5),
('Bañado Mayorista', 2800, 0, 0, '2024-09-28', 0, 1, NULL, '2024-09-28 17:29:24.371254', NULL, 1, 1),
('Jugo Watts 200ml', 4000, 0, 0, '2024-09-28', 4000, 1, NULL, '2024-09-28 18:57:05.637086', NULL, 1, 5),
('Coca Cola 200ml', 3000, 0, 0, '2024-10-05', 3000, 1, NULL, '2024-10-05 17:48:18.554828', NULL, 1, 5),
('Copa oreo', 20000, 0, 0, '2024-12-21', 20000, 1, NULL, '2024-10-05 20:06:39.122291', NULL, 1, 5),
('Coca Cola 500ml', 6000, 0, 0, '2024-10-07', 6000, 1, NULL, '2024-10-07 18:07:24.469454', NULL, 1, 5),
('Toddy', 4000, 0, 0, '2024-10-07', 4000, 1, NULL, '2024-10-07 18:17:06.701387', NULL, 1, 5),
('Torta Helada', 15000, 0, 0, '2024-10-07', 15000, 1, NULL, '2024-10-07 18:23:49.281805', NULL, 1, 5),
('Agua 500ml', 5000, 0, 0, '2024-10-07', 5000, 1, NULL, '2024-10-07 18:44:06.663255', NULL, 1, 5),
('SOBRANTE', 1, 0, 0, '2024-10-07', 1, 1, NULL, '2024-10-07 18:50:20.998741', NULL, 1, 5),
('Pruebas', 14, 1, 3, '2024-08-16', 123, 1, NULL, '2024-08-16 18:06:41.443387', NULL, 1, 1),
('Cono Grande', 1500, 0, 0, '2024-09-14', 1500, 1, NULL, '2024-09-15 00:27:57.727878', NULL, 1, 5),
('Cuchara de Acai', 8000, 0, 0, '2024-10-12', 8000, 1, NULL, '2024-10-12 16:40:44.816785', NULL, 1, 5),
('Postre 250ml', 5000, 0, 0, '2024-11-19', 5000, 1, NULL, '2024-11-19 16:35:50.981702', NULL, 1, 5);
