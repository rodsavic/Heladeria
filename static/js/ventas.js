/* Formulario de venta: alta rapida de cliente + punto de venta. */

function obtenerCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function mostrarErrorClienteModal(message) {
    const alertBox = document.getElementById('clienteModalAlert');
    if (!alertBox) return;
    alertBox.textContent = message;
    alertBox.classList.remove('d-none');
}

function limpiarErrorClienteModal() {
    const alertBox = document.getElementById('clienteModalAlert');
    if (!alertBox) return;
    alertBox.textContent = '';
    alertBox.classList.add('d-none');
}

function validarCamposNuevoCliente(container) {
    const camposRequeridos = [
        { name: 'documento', label: 'Cedula / Documento' },
        { name: 'nombre', label: 'Nombre' },
        { name: 'apellido', label: 'Apellido' },
        { name: 'correo', label: 'Correo' },
        { name: 'celular', label: 'Celular' }
    ];

    for (const campo of camposRequeridos) {
        const input = container.querySelector(`input[name="${campo.name}"]`);
        const valor = input?.value?.trim() || '';
        if (!valor) {
            if (input) input.focus();
            mostrarErrorClienteModal(`El campo ${campo.label} es obligatorio.`);
            return false;
        }
    }

    const correoInput = container.querySelector('input[name="correo"]');
    if (correoInput && correoInput.value.trim()) {
        const correoValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correoInput.value.trim());
        if (!correoValido) {
            correoInput.focus();
            mostrarErrorClienteModal('Ingresa un correo valido.');
            return false;
        }
    }

    return true;
}

function actualizarSelectClientes(clienteSeleccionadoId = null) {
    const clienteSelect = document.getElementById('cliente');
    if (!clienteSelect) return Promise.resolve();

    return fetch('/clientes/clientes_json/')
        .then(response => {
            if (!response.ok) {
                throw new Error('No se pudo actualizar la lista de clientes.');
            }
            return response.json();
        })
        .then(data => {
            clienteSelect.innerHTML = '<option value="">Seleccionar cliente...</option>';
            (data.clientes || []).forEach(cliente => {
                const option = document.createElement('option');
                option.value = cliente.id_cliente;
                option.textContent = cliente.label;
                if (clienteSeleccionadoId && String(cliente.id_cliente) === String(clienteSeleccionadoId)) {
                    option.selected = true;
                }
                clienteSelect.appendChild(option);
            });

            if (typeof $ !== "undefined" && $('#cliente').length) {
                $('#cliente').trigger('change.select2');
            }
        });
}

function cargarOpcionesUbicacion(select, url) {
    if (!select) return;
    select.innerHTML = '<option value="">Seleccione...</option>';
    if (!url) return;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            (data.items || []).forEach(item => select.add(new Option(item.descripcion, item.codigo)));
        });
}

function inicializarUbicacionNuevoCliente() {
    const departamento = document.getElementById('cliente_departamento');
    const distrito = document.getElementById('cliente_distrito');
    const ciudad = document.getElementById('cliente_id_ciudad');
    if (!departamento || !distrito || !ciudad) return;

    departamento.addEventListener('change', () => {
        cargarOpcionesUbicacion(distrito, departamento.value && `/catalogos/distritos/${departamento.value}/`);
        cargarOpcionesUbicacion(ciudad, null);
    });
    distrito.addEventListener('change', () => {
        cargarOpcionesUbicacion(ciudad, distrito.value && `/catalogos/ciudades/${distrito.value}/`);
    });
}

function abrirModalNuevoCliente() {
    limpiarErrorClienteModal();
    const container = document.getElementById('formNuevoCliente');
    if (container) {
        container.querySelectorAll('input').forEach(input => {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = input.defaultValue;
            }
        });
        container.querySelectorAll('select').forEach(select => {
            const opcionPorDefecto = Array.from(select.options).find(option => option.defaultSelected);
            select.value = opcionPorDefecto ? opcionPorDefecto.value : '';
        });
        cargarOpcionesUbicacion(document.getElementById('cliente_distrito'), null);
        cargarOpcionesUbicacion(document.getElementById('cliente_id_ciudad'), null);
    }

    const modalElement = document.getElementById('modalNuevoCliente');
    if (!modalElement) return;
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
}

function guardarNuevoCliente() {
    limpiarErrorClienteModal();

    const container = document.getElementById('formNuevoCliente');
    const submitButton = document.getElementById('btnGuardarNuevoCliente');
    if (!container) return;
    // Enter en un campo llama a esta funcion aunque el boton ya este deshabilitado.
    if (submitButton && submitButton.disabled) return;
    if (!validarCamposNuevoCliente(container)) return;

    const formData = new FormData();
    container.querySelectorAll('input[name], select[name]').forEach(input => {
        if (input.type === 'checkbox' && !input.checked) return;
        formData.append(input.name, input.value);
    });
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Guardando...';
    }

    fetch('/clientes/crear_cliente_ajax/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': obtenerCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
        .then(async response => {
            const data = await response.json();
            if (!response.ok || !data.ok) {
                const firstError = data?.errors ? Object.values(data.errors)[0]?.[0] : null;
                throw new Error(firstError || data.message || 'No se pudo crear el cliente.');
            }
            return data;
        })
        .then(data => {
            return actualizarSelectClientes(data.cliente.id_cliente).then(() => data);
        })
        .then(data => {
            if (typeof $ !== "undefined" && $('#cliente').length) {
                $('#cliente').val(String(data.cliente.id_cliente)).trigger('change');
            } else {
                document.getElementById('cliente').value = data.cliente.id_cliente;
            }

            const modalElement = document.getElementById('modalNuevoCliente');
            const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
            modal.hide();
        })
        .catch(error => {
            mostrarErrorClienteModal(error.message);
        })
        .finally(() => {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = '<i class="bi bi-save"></i> Guardar cliente';
            }
        });
}

/* ==========================================================================
 * Punto de venta (crear / editar venta)
 * El carrito vive en memoria (estado.carrito) y la vista se redibuja desde ahi.
 * ========================================================================== */
const PosVenta = (function () {
    const formatoGs = new Intl.NumberFormat('es-PY', { maximumFractionDigits: 0 });
    const BILLETES = [2000, 5000, 10000, 20000, 50000, 100000];

    const estado = {
        productos: [],
        porId: new Map(),
        carrito: [],          // [{ id, cantidad }]
        categoria: '',
        resaltado: -1,        // indice dentro de los tiles visibles
        metodo: 'efectivo',
        firmaInicial: '',     // estado al abrir el formulario (para detectar cambios)
        saliendo: false,      // true cuando la salida es intencional (cobro o salida confirmada)
    };
    const el = {};

    const fmt = (n) => formatoGs.format(Math.round(n || 0));
    const num = (v) => {
        const n = parseFloat(v);
        return Number.isFinite(n) ? n : 0;
    };
    const normalizar = (texto) => (texto || '')
        .toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    const esPunteroFino = () => window.matchMedia && window.matchMedia('(pointer: fine)').matches;

    function leerJson(id, porDefecto) {
        const nodo = document.getElementById(id);
        if (!nodo) return porDefecto;
        try {
            const valor = JSON.parse(nodo.textContent);
            return valor === '' || valor === null ? porDefecto : valor;
        } catch (e) {
            return porDefecto;
        }
    }

    /* ---------- Tipo de venta y precios ---------- */

    function tipoVentaSeleccionado() {
        return document.querySelector('.tipo-venta-radio:checked');
    }

    function esPedidosYa() {
        const tipo = tipoVentaSeleccionado();
        return !!tipo && normalizar(tipo.dataset.nombre).includes('pedido');
    }

    function precioDe(producto) {
        if (esPedidosYa() && producto.precio_py > 0) return producto.precio_py;
        return producto.precio;
    }

    function disponible(producto) {
        return !esPedidosYa() || producto.precio_py > 0;
    }

    /* ---------- Catalogo ---------- */

    function construirGrilla() {
        const fragmento = document.createDocumentFragment();
        estado.productos.forEach((producto) => {
            const boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'pos-producto';
            boton.dataset.id = producto.id;
            boton.setAttribute('role', 'listitem');
            boton.innerHTML = '<span class="nombre"></span><span class="precio"></span><span class="en-ticket"></span>';
            boton.querySelector('.nombre').textContent = producto.nombre;
            boton.addEventListener('click', () => {
                agregar(producto.id, 1);
                if (esPunteroFino()) el.buscar.focus();
            });
            producto.tile = boton;
            producto.busqueda = normalizar(producto.nombre);
            fragmento.appendChild(boton);
        });
        el.vacio = document.createElement('div');
        el.vacio.className = 'pos-vacio d-none';
        el.vacio.textContent = 'No hay productos que coincidan con la búsqueda.';
        fragmento.appendChild(el.vacio);
        el.grilla.appendChild(fragmento);
    }

    function textoBusqueda() {
        // Admite "3*cono" o "3 x cono" para indicar la cantidad.
        const crudo = el.buscar.value.trim();
        const match = crudo.match(/^(\d+)\s*[*x]\s*(.*)$/i);
        if (match) return { cantidad: Math.max(1, parseInt(match[1], 10)), texto: normalizar(match[2]) };
        return { cantidad: 1, texto: normalizar(crudo) };
    }

    function filtrarGrilla() {
        const { texto } = textoBusqueda();
        const palabras = texto.split(/\s+/).filter(Boolean);
        let visibles = 0;
        estado.productos.forEach((producto) => {
            const coincide = palabras.every(p => producto.busqueda.includes(p));
            const enCategoria = !estado.categoria || producto.categorias.includes(Number(estado.categoria));
            const mostrar = coincide && enCategoria && disponible(producto);
            producto.tile.classList.toggle('d-none', !mostrar);
            producto.tile.querySelector('.precio').textContent = `Gs ${fmt(precioDe(producto))}`;
            if (mostrar) visibles++;
        });
        el.vacio.classList.toggle('d-none', visibles > 0);
        estado.resaltado = palabras.length && visibles ? 0 : -1;
        pintarResaltado();
    }

    function tilesVisibles() {
        return estado.productos.map(p => p.tile).filter(t => !t.classList.contains('d-none'));
    }

    function pintarResaltado() {
        const visibles = tilesVisibles();
        estado.productos.forEach(p => p.tile.classList.remove('resaltado'));
        const tile = visibles[estado.resaltado];
        if (tile) {
            tile.classList.add('resaltado');
            tile.scrollIntoView({ block: 'nearest' });
        }
    }

    function moverResaltado(paso) {
        const visibles = tilesVisibles();
        if (!visibles.length) return;
        // Paso vertical = cantidad de columnas de la grilla.
        const columnas = getComputedStyle(el.grilla).gridTemplateColumns.split(' ').length || 1;
        const delta = Math.abs(paso) === 2 ? Math.sign(paso) * columnas : paso;
        const actual = estado.resaltado < 0 ? -1 : estado.resaltado;
        estado.resaltado = Math.min(visibles.length - 1, Math.max(0, actual + delta));
        pintarResaltado();
    }

    function onBuscarKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const visibles = tilesVisibles();
            const tile = visibles[estado.resaltado] || (visibles.length === 1 ? visibles[0] : null);
            if (!tile) return;
            agregar(Number(tile.dataset.id), textoBusqueda().cantidad);
            el.buscar.value = '';
            filtrarGrilla();
        } else if (e.key === 'Escape') {
            if (el.buscar.value) {
                e.preventDefault();
                el.buscar.value = '';
                filtrarGrilla();
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault(); moverResaltado(2);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault(); moverResaltado(-2);
        } else if (e.key === 'ArrowRight' && el.buscar.selectionStart === el.buscar.value.length && estado.resaltado >= 0) {
            e.preventDefault(); moverResaltado(1);
        } else if (e.key === 'ArrowLeft' && estado.resaltado > 0) {
            e.preventDefault(); moverResaltado(-1);
        }
    }

    /* ---------- Carrito ---------- */

    function agregar(id, cantidad) {
        const producto = estado.porId.get(Number(id));
        if (!producto) return;
        if (!tipoVentaSeleccionado()) {
            AppAlertas.alerta('Selecciona el tipo de venta antes de agregar productos.', 'warning');
            return;
        }
        const item = estado.carrito.find(i => i.id === producto.id);
        if (item) {
            item.cantidad += cantidad;
        } else {
            estado.carrito.push({ id: producto.id, cantidad: cantidad });
        }
        producto.tile.classList.remove('agregado');
        void producto.tile.offsetWidth; // reinicia la animacion
        producto.tile.classList.add('agregado');
        renderCarrito(producto.id);
    }

    function cambiarCantidad(id, cantidad) {
        const item = estado.carrito.find(i => i.id === id);
        if (!item) return;
        if (cantidad <= 0) {
            estado.carrito = estado.carrito.filter(i => i.id !== id);
        } else {
            item.cantidad = cantidad;
        }
        renderCarrito();
    }

    function lineas() {
        return estado.carrito.map((item) => {
            const producto = estado.porId.get(item.id);
            const precio = precioDe(producto);
            const total = Math.round(precio * item.cantidad);
            return {
                item, producto, precio, total,
                iva10: producto.iva === 10 ? Math.round(total / 11) : 0,
                iva5: producto.iva === 5 ? Math.round(total / 21) : 0,
            };
        });
    }

    function totales() {
        return lineas().reduce((acc, l) => {
            acc.total += l.total; acc.iva10 += l.iva10; acc.iva5 += l.iva5; acc.items += l.item.cantidad;
            return acc;
        }, { total: 0, iva10: 0, iva5: 0, items: 0 });
    }

    function renderCarrito(idEnfocar) {
        const lista = lineas();
        el.items.innerHTML = '';

        if (!lista.length) {
            el.items.innerHTML = '<div class="pos-ticket-vacio"><i class="bi bi-cart3 fs-3 d-block mb-1"></i>Tocá un producto para agregarlo</div>';
        }

        lista.forEach((l) => {
            const fila = document.createElement('div');
            fila.className = 'pos-item';
            fila.dataset.id = l.producto.id;
            fila.innerHTML = `
                <div>
                    <div class="nombre"></div>
                    <div class="unitario">Gs ${fmt(l.precio)} c/u</div>
                </div>
                <div class="subtotal">Gs ${fmt(l.total)}</div>
                <div class="controles">
                    <button type="button" data-accion="menos" aria-label="Restar uno"><i class="bi bi-dash"></i></button>
                    <input type="number" min="1" step="1" inputmode="numeric" value="${l.item.cantidad}" aria-label="Cantidad">
                    <button type="button" data-accion="mas" aria-label="Sumar uno"><i class="bi bi-plus"></i></button>
                    <button type="button" class="quitar" data-accion="quitar" title="Quitar"><i class="bi bi-trash"></i></button>
                </div>`;
            fila.querySelector('.nombre').textContent = l.producto.nombre;
            el.items.appendChild(fila);
        });

        if (idEnfocar) {
            el.items.querySelector(`.pos-item[data-id="${idEnfocar}"]`)?.scrollIntoView({ block: 'nearest' });
        }

        // Insignias de cantidad sobre los productos del catalogo.
        const cantidades = new Map(estado.carrito.map(i => [i.id, i.cantidad]));
        estado.productos.forEach((p) => {
            const cant = cantidades.get(p.id) || 0;
            p.tile.classList.toggle('en-carrito', cant > 0);
            p.tile.querySelector('.en-ticket').textContent = cant;
        });

        const t = totales();
        el.total.textContent = fmt(t.total);
        el.iva10.textContent = fmt(t.iva10);
        el.iva5.textContent = fmt(t.iva5);
        el.cantidadItems.textContent = t.items;
        el.barraItems.textContent = t.items;
        el.barraTotal.textContent = fmt(t.total);
        el.vaciar.classList.toggle('invisible', !lista.length);
        actualizarCobro();
    }

    function onItemsClick(e) {
        const boton = e.target.closest('button[data-accion]');
        if (!boton) return;
        const id = Number(boton.closest('.pos-item').dataset.id);
        const item = estado.carrito.find(i => i.id === id);
        if (!item) return;
        const accion = boton.dataset.accion;
        if (accion === 'mas') cambiarCantidad(id, item.cantidad + 1);
        if (accion === 'menos') cambiarCantidad(id, item.cantidad - 1);
        if (accion === 'quitar') cambiarCantidad(id, 0);
    }

    function onItemsChange(e) {
        if (e.target.tagName !== 'INPUT') return;
        const id = Number(e.target.closest('.pos-item').dataset.id);
        const cantidad = parseInt(e.target.value, 10);
        cambiarCantidad(id, Number.isNaN(cantidad) ? 1 : cantidad);
    }

    /* ---------- Cobro ---------- */

    function seleccionarMetodo(metodo, enfocar) {
        estado.metodo = metodo;
        el.metodos.querySelectorAll('button').forEach(b => b.classList.toggle('activo', b.dataset.metodo === metodo));
        el.pagoEfectivo.classList.toggle('d-none', metodo !== 'efectivo');
        el.pagoMixto.classList.toggle('d-none', metodo !== 'mixto');
        actualizarCobro();
        if (!enfocar) return;
        if (metodo === 'efectivo') el.recibido.focus();
        if (metodo === 'mixto') {
            // Foco sin autocompletar: el usuario todavia no eligio en que campo va el resto.
            estado.focoProgramatico = true;
            el.pagoMixto.querySelector('input').focus();
            estado.focoProgramatico = false;
        }
    }

    function montosMixto() {
        const montos = {};
        el.pagoMixto.querySelectorAll('.pos-mixto').forEach(i => { montos[i.dataset.metodo] = num(i.value); });
        return montos;
    }

    /** Calcula el reparto del pago. Devuelve { ok, mensaje, efectivo, pos, transferencia, vuelto }. */
    function calcularPago() {
        const total = totales().total;
        const r = { ok: true, mensaje: '', efectivo: 0, pos: 0, transferencia: 0, vuelto: 0, falta: 0 };
        if (estado.metodo === 'efectivo') {
            const recibido = el.recibido.value === '' ? total : num(el.recibido.value);
            r.efectivo = total;
            r.vuelto = recibido - total;
            if (r.vuelto < 0) { r.ok = false; r.falta = -r.vuelto; r.mensaje = 'El monto recibido no cubre el total.'; }
        } else if (estado.metodo === 'pos' || estado.metodo === 'transferencia') {
            r[estado.metodo] = total;
        } else {
            const m = montosMixto();
            const noEfectivo = m.pos + m.transferencia;
            if (noEfectivo > total) {
                r.ok = false; r.mensaje = 'POS + Transferencia superan el total de la venta.';
            } else {
                r.pos = m.pos;
                r.transferencia = m.transferencia;
                r.efectivo = total - noEfectivo; // se guarda el efectivo neto (sin vuelto)
                const pagado = m.efectivo + noEfectivo;
                if (pagado < total) {
                    r.ok = false; r.falta = total - pagado; r.mensaje = 'Los montos ingresados no cubren el total.';
                } else {
                    r.vuelto = pagado - total; // solo puede venir del efectivo
                }
            }
        }
        return r;
    }

    function renderBilletes(total) {
        el.billetes.innerHTML = '';
        if (total <= 0) return;
        const opciones = new Set();
        [1000, 5000, 10000, 50000, 100000].forEach(m => {
            const v = Math.ceil(total / m) * m;
            if (v > total) opciones.add(v);
        });
        BILLETES.filter(b => b > total).forEach(b => opciones.add(b));
        const valores = ['exacto', ...Array.from(opciones).sort((a, b) => a - b).slice(0, 5)];
        valores.forEach((v) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.textContent = v === 'exacto' ? 'Exacto' : fmt(v);
            b.addEventListener('click', () => {
                el.recibido.value = v === 'exacto' ? '' : v;
                actualizarCobro();
                el.btnCobrar.focus();
            });
            el.billetes.appendChild(b);
        });
    }

    function actualizarCobro() {
        const total = totales().total;
        if (estado.metodo === 'efectivo' && el.billetes.dataset.total !== String(total)) {
            el.billetes.dataset.total = String(total);
            renderBilletes(total);
        }

        const r = calcularPago();
        el.resultado.classList.remove('ok', 'falta', 'd-none');
        if (!total) {
            el.resultado.classList.add('d-none');
        } else if (r.falta > 0) {
            el.resultado.classList.add('falta');
            el.resultadoTexto.textContent = 'Falta';
            el.resultadoValor.textContent = `Gs ${fmt(r.falta)}`;
        } else if (!r.ok) {
            el.resultado.classList.add('falta');
            el.resultadoTexto.textContent = r.mensaje;
            el.resultadoValor.textContent = '';
        } else if (estado.metodo === 'efectivo' || estado.metodo === 'mixto') {
            el.resultado.classList.add('ok');
            el.resultadoTexto.textContent = 'Vuelto';
            el.resultadoValor.textContent = `Gs ${fmt(r.vuelto)}`;
        } else {
            el.resultado.classList.add('ok');
            el.resultadoTexto.textContent = 'Cobrar';
            el.resultadoValor.textContent = `Gs ${fmt(total)}`;
        }
    }

    function cobrar() {
        if (window.EnvioUnico && EnvioUnico.enviando(el.form)) return;

        const t = totales();
        if (!tipoVentaSeleccionado()) {
            AppAlertas.alerta('Selecciona el tipo de venta.', 'warning'); return;
        }
        if (!estado.carrito.length || t.total <= 0) {
            AppAlertas.alerta('No hay productos en la venta.', 'warning'); el.buscar.focus(); return;
        }
        if (!el.cliente.value) {
            AppAlertas.alerta('Por favor, selecciona un cliente antes de continuar.', 'warning'); return;
        }
        const pago = calcularPago();
        if (!pago.ok) {
            AppAlertas.alerta(pago.mensaje, 'warning'); return;
        }

        document.getElementById('productos_json').value = JSON.stringify(lineas().map(l => ({
            id_producto: l.producto.id,
            cantidad: l.item.cantidad,
            total_detalle: l.total.toFixed(0),
            total_detalle_iva_10: l.iva10.toFixed(0),
            total_detalle_iva_5: l.iva5.toFixed(0),
        })));
        document.getElementById('total_venta').value = t.total.toFixed(0);
        document.getElementById('total_iva_10').value = t.iva10.toFixed(0);
        document.getElementById('total_iva_5').value = t.iva5.toFixed(0);
        document.getElementById('efectivo').value = pago.efectivo.toFixed(0);
        document.getElementById('pos').value = pago.pos.toFixed(0);
        document.getElementById('transferencia').value = pago.transferencia.toFixed(0);

        try {
            if (el.seguirVendiendo) localStorage.setItem('pos.seguirVendiendo', el.seguirVendiendo.checked ? '1' : '0');
        } catch (e) { /* sin almacenamiento: no pasa nada */ }

        estado.saliendo = true; // el envio no debe disparar el aviso de salida
        if (window.EnvioUnico) {
            EnvioUnico.enviar(el.form);
        } else {
            el.form.submit();
        }
    }

    /* ---------- Inicializacion ---------- */

    function cargarEstadoInicial() {
        const carrito = leerJson('pos-carrito-inicial', []);
        if (Array.isArray(carrito)) {
            carrito.forEach((i) => {
                const id = Number(i.id);
                if (!estado.porId.has(id)) return;
                const existente = estado.carrito.find(c => c.id === id);
                const cantidad = Math.max(1, Math.round(num(i.cantidad)));
                if (existente) existente.cantidad += cantidad;
                else estado.carrito.push({ id, cantidad });
            });
        }

        const pagos = leerJson('pos-pagos-iniciales', null);
        if (pagos && typeof pagos === 'object') {
            const usados = ['efectivo', 'pos', 'transferencia'].filter(m => num(pagos[m]) > 0);
            if (usados.length === 1) {
                estado.metodo = usados[0];
            } else if (usados.length > 1) {
                estado.metodo = 'mixto';
                el.pagoMixto.querySelectorAll('.pos-mixto').forEach((input) => {
                    const valor = num(pagos[input.dataset.metodo]);
                    input.value = valor > 0 ? valor : '';
                });
            }
        }

        try {
            if (el.seguirVendiendo && localStorage.getItem('pos.seguirVendiendo') === '0') {
                el.seguirVendiendo.checked = false;
            }
        } catch (e) { /* sin almacenamiento */ }
    }

    /* ---------- Aviso al salir con una venta en curso ---------- */

    function firmaEstado() {
        return JSON.stringify({
            carrito: estado.carrito.map(i => [i.id, i.cantidad]),
            tipo: tipoVentaSeleccionado()?.value || '',
            cliente: el.cliente?.value || '',
            fecha: document.getElementById('fecha_venta')?.value || '',
        });
    }

    function hayVentaEnCurso() {
        if (estado.saliendo) return false;
        // Venta nueva: hay algo cargado en el ticket. Edicion: algo cambio respecto a lo guardado.
        if (el.form.closest('#posVenta').dataset.modo === 'crear') return estado.carrito.length > 0;
        return firmaEstado() !== estado.firmaInicial;
    }

    function protegerSalida() {
        estado.firmaInicial = firmaEstado();

        // Recargar, cerrar la pestana o escribir otra URL: aviso nativo del navegador.
        window.addEventListener('beforeunload', (e) => {
            if (!hayVentaEnCurso()) return;
            e.preventDefault();
            e.returnValue = '';
        });

        // Enlaces internos (menu lateral, volver, etc.): dialogo propio de la app.
        document.addEventListener('click', (e) => {
            const enlace = e.target.closest('a[href]');
            if (!enlace || e.defaultPrevented || e.button !== 0) return;
            if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;       // abre en otra pestana
            if (enlace.target && enlace.target !== '_self') return;
            if (enlace.hasAttribute('download')) return;
            const href = enlace.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
            if (!hayVentaEnCurso()) return;

            e.preventDefault();
            e.stopPropagation();
            const mensaje = el.form.closest('#posVenta').dataset.modo === 'crear'
                ? 'Hay una venta en curso sin guardar. Si salís se perderán los productos cargados.'
                : 'Hay cambios sin guardar en esta venta. Si salís se perderán.';
            AppAlertas.confirmar(mensaje, {
                titulo: '¿Salir sin guardar?', aceptar: 'Salir', cancelar: 'Seguir con la venta',
            }).then((ok) => {
                if (!ok) return;
                estado.saliendo = true;
                window.location.href = enlace.href;
            });
        }, true);

        // Volver con el boton atras y regresar desde el cache: la venta sigue en curso.
        window.addEventListener('pageshow', (e) => {
            if (e.persisted) estado.saliendo = false;
        });
    }

    function init() {
        const raiz = document.getElementById('posVenta');
        if (!raiz) return;

        Object.assign(el, {
            form: document.getElementById('formVenta'),
            buscar: document.getElementById('posBuscar'),
            grilla: document.getElementById('posGrilla'),
            categorias: document.getElementById('posCategorias'),
            items: document.getElementById('posItems'),
            total: document.getElementById('posTotal'),
            iva10: document.getElementById('posIva10'),
            iva5: document.getElementById('posIva5'),
            cantidadItems: document.getElementById('posCantidadItems'),
            vaciar: document.getElementById('posVaciar'),
            metodos: document.getElementById('posMetodos'),
            pagoEfectivo: document.getElementById('posPagoEfectivo'),
            pagoMixto: document.getElementById('posPagoMixto'),
            recibido: document.getElementById('posRecibido'),
            billetes: document.getElementById('posBilletes'),
            resultado: document.getElementById('posResultado'),
            resultadoTexto: document.getElementById('posResultadoTexto'),
            resultadoValor: document.getElementById('posResultadoValor'),
            btnCobrar: document.getElementById('posBtnCobrar'),
            cliente: document.getElementById('cliente'),
            seguirVendiendo: document.getElementById('posSeguirVendiendo'),
            barraItems: document.getElementById('posBarraItems'),
            barraTotal: document.getElementById('posBarraTotal'),
        });

        estado.productos = leerJson('pos-productos', []).map(p => ({
            ...p,
            id: Number(p.id),
            precio: num(p.precio),
            precio_py: num(p.precio_py),
            iva: Number(p.iva) || 0,
            categorias: (p.categorias || []).map(Number),
        }));
        estado.productos.forEach(p => estado.porId.set(p.id, p));

        construirGrilla();
        cargarEstadoInicial();
        filtrarGrilla();
        renderCarrito();
        seleccionarMetodo(estado.metodo, false);

        // Buscador
        el.buscar.addEventListener('input', filtrarGrilla);
        el.buscar.addEventListener('keydown', onBuscarKeydown);

        // Categorias
        el.categorias?.addEventListener('click', (e) => {
            const boton = e.target.closest('button[data-categoria]');
            if (!boton) return;
            estado.categoria = boton.dataset.categoria;
            el.categorias.querySelectorAll('button').forEach(b => b.classList.toggle('activa', b === boton));
            filtrarGrilla();
        });

        // Tipo de venta: cambia precios y productos disponibles
        document.querySelectorAll('.tipo-venta-radio').forEach((radio) => {
            radio.addEventListener('change', () => {
                const quitados = estado.carrito.filter(i => !disponible(estado.porId.get(i.id)));
                if (quitados.length) {
                    estado.carrito = estado.carrito.filter(i => disponible(estado.porId.get(i.id)));
                    AppAlertas.toast?.(`Se quitaron ${quitados.length} producto(s) sin precio para este tipo de venta.`, 'warning');
                }
                filtrarGrilla();
                renderCarrito();
            });
        });

        // Ticket
        el.items.addEventListener('click', onItemsClick);
        el.items.addEventListener('change', onItemsChange);
        el.items.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
                e.preventDefault();
                e.target.blur();
                el.buscar.focus();
            }
        });
        el.vaciar.addEventListener('click', () => {
            AppAlertas.confirmar('¿Vaciar el ticket?', { aceptar: 'Vaciar' }).then((ok) => {
                if (!ok) return;
                estado.carrito = [];
                renderCarrito();
                el.buscar.focus();
            });
        });

        // Cobro
        el.metodos.addEventListener('click', (e) => {
            const boton = e.target.closest('button[data-metodo]');
            if (boton) seleccionarMetodo(boton.dataset.metodo, true);
        });
        el.recibido.addEventListener('input', actualizarCobro);
        el.pagoMixto.addEventListener('input', actualizarCobro);
        el.pagoMixto.addEventListener('focusin', (e) => {
            const input = e.target;
            if (estado.focoProgramatico || !input.classList.contains('pos-mixto') || input.value !== '') return;
            const m = montosMixto();
            const falta = totales().total - (m.efectivo + m.pos + m.transferencia);
            if (falta > 0) {
                input.value = falta;
                input.select();
                actualizarCobro();
            }
        });

        el.form.addEventListener('submit', (e) => {
            e.preventDefault();
            cobrar();
        });
        // Enter en campos de monto cobra; en el resto del form no envia nada por accidente.
        el.form.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter' || e.target.tagName !== 'INPUT') return;
            if (e.target.closest('#modalNuevoCliente, #posItems') || e.target === el.buscar) return;
            e.preventDefault();
            if (e.target === el.recibido || e.target.classList.contains('pos-mixto')) cobrar();
        });

        // Cliente
        if (typeof $ !== 'undefined' && $.fn.select2) {
            $('#cliente').on('select2:close', () => { if (esPunteroFino()) setTimeout(() => el.buscar.focus(), 0); });
        }

        // Atajos globales
        document.addEventListener('keydown', (e) => {
            if (document.querySelector('.modal.show')) return;
            if (e.key === 'F2') {
                e.preventDefault();
                el.buscar.focus();
                el.buscar.select();
            } else if (e.key === 'F4' || (e.key === 'Enter' && (e.ctrlKey || e.metaKey))) {
                e.preventDefault();
                cobrar();
            }
        });

        protegerSalida();

        // Barra movil
        document.getElementById('posBarraIr')?.addEventListener('click', () => {
            document.getElementById('posTicket').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    return { init };
})();


document.addEventListener('DOMContentLoaded', function () {
    if (!document.getElementById('posVenta')) return;

    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('#cliente').select2({
            placeholder: 'Selecciona un cliente',
            width: '100%',
        });
    }

    PosVenta.init();

    document.getElementById('btnNuevoCliente')?.addEventListener('click', abrirModalNuevoCliente);
    document.getElementById('btnGuardarNuevoCliente')?.addEventListener('click', guardarNuevoCliente);
    inicializarUbicacionNuevoCliente();

    document.getElementById('formNuevoCliente')?.querySelectorAll('input:not([type="checkbox"])').forEach(input => {
        input.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                guardarNuevoCliente();
            }
        });
    });
});
