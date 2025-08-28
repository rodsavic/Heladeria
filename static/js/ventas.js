function inicializarSelects() {
    $('.selectProducto').select2({
        placeholder: "Selecciona un producto",
        allowClear: true
    });
    $('#cliente').select2({
        placeholder: "Selecciona un cliente",
        allowClear: true
    });
}

function agregarProductoATabla() {

    const selectProducto = document.getElementById("selectProducto");
    const cantidadInput = parseFloat(document.getElementById("cantidad").value) || 0;
    const precio = parseFloat(selectProducto.options[selectProducto.selectedIndex].getAttribute('data-precio')) || 0;
    const cantidad = parseInt(cantidadInput, 10);
    const idProducto = selectProducto.value;
    const ivaDescripcion = parseInt(selectProducto.options[selectProducto.selectedIndex].getAttribute('data-descripcionIva')) || 0;
    const nombreProducto = selectProducto.options[selectProducto.selectedIndex].text;

    console.log("idProducto:", idProducto, "tipo de dato:", typeof idProducto)

    if (!idProducto || cantidad <= 0) {
        alert("Selecciona un producto y una cantidad válida.");
        return;
    }

    const tabla = document.getElementById('tablaProductos').getElementsByTagName('tbody')[0];

    let filaExistente = null;

    for (let fila of tabla.rows) {
        if (fila.cells[0].innerText === nombreProducto) {
            filaExistente = fila;
            break;
        }
    }

    console.log("productoExistente: ", filaExistente);
    console.log("iva: ", ivaDescripcion)

    if (nombreProducto && cantidad > 0) {
        const totalDetalle = cantidad * precio;
        let iva10 = 0;
        let iva5 = 0;

        // Buscar si el producto ya está en la tabla
        
        if (filaExistente) {
            // Actualizar producto existente
            const totalDetalleNuevo = parseInt(filaExistente.cells[3].innerText) + totalDetalle;
            const ivaAnterior = parseFloat(filaExistente.cells[4].innerText) || 0;

            if (ivaDescripcion === 10) {
                actualizarTotalIVA(-ivaAnterior, 0);
                iva10 = totalDetalleNuevo / 11;
                actualizarTotalIVA(iva10, 0);
            } else if (ivaDescripcion === 5) {
                actualizarTotalIVA(0, -ivaAnterior);
                iva5 = totalDetalleNuevo / 21;
                actualizarTotalIVA(0, iva5);
            }

            // Actualizar la fila en la tabla
            //const fila = document.querySelector(`tr[data-producto-id='${idProducto}']`);
            filaExistente.cells[1].innerText = parseInt(filaExistente.cells[1].innerText) + cantidad;
            filaExistente.cells[3].innerText = totalDetalleNuevo;
            filaExistente.cells[4].innerText = iva10.toFixed(0);
            filaExistente.cells[5].innerText = iva5.toFixed(0);
        } else {
            // Insertar nueva fila si no existe el producto
            const tabla = document.getElementById("tablaProductos").querySelector("tbody");
            const nuevaFila = tabla.insertRow();
            nuevaFila.setAttribute('data-producto-id', idProducto); // Añadir ID de producto a la fila

            const celdaProducto = nuevaFila.insertCell(0);
            const celdaCantidad = nuevaFila.insertCell(1);
            const celdaPrecio = nuevaFila.insertCell(2);
            const celdaTotalDetalle = nuevaFila.insertCell(3);
            const celdaIva10 = nuevaFila.insertCell(4);
            const celdaIva5 = nuevaFila.insertCell(5);
            const celdaAccion = nuevaFila.insertCell(6);

            celdaProducto.innerText = nombreProducto;
            celdaCantidad.innerText = cantidad;
            celdaPrecio.innerText = precio.toFixed(0);
            celdaTotalDetalle.innerText = totalDetalle.toFixed(0);

            // Calcular IVA en base al valor del id_iva
            if (ivaDescripcion === 10) {
                iva10 = totalDetalle / 11;
                actualizarTotalIVA(iva10, 0);
            } else if (ivaDescripcion === 5) {
                iva5 = totalDetalle / 21;
                actualizarTotalIVA(0, iva5);
            }
            celdaIva10.innerText = iva10.toFixed(0);
            celdaIva5.innerText = iva5.toFixed(0);
            celdaAccion.innerHTML = `<button class="btn-cancelar btn-sm" title="Eliminar" onclick="eliminarProducto('${idProducto}', ${ivaDescripcion})"><i class="bi bi-trash"></i></button>`;
            console.log("idProducto:", idProducto, "tipo de dato:", typeof idProducto)
            console.log("cantidad:", cantidad, "tipo de dato:", typeof cantidad)
            console.log("total_detalle:", totalDetalle, "tipo de dato:", typeof totalDetalle)
        }

        actualizarTotal(totalDetalle);
        document.getElementById('cantidad').value = 1;
    } else if (cantidad < 1) {
        window.alert("La cantidad mínima es 1");
    } else {
        window.alert("Debe seleccionar al menos un producto.");
    }


}

function eliminarProducto(idProducto, ivaDescripcion) {
    // Buscar la fila por el id_producto
    const tabla = document.getElementById("tablaProductos").querySelector("tbody");
    const fila = document.querySelector(`tr[data-producto-id='${idProducto}']`);
    const total_detalle_a_eliminar = (parseFloat(fila.cells[3].innerText)).toFixed(0)
    const total_iva_10 = (parseFloat(fila.cells[4].innerText)).toFixed(0);
    const total_iva_5 = (parseFloat(fila.cells[5].innerText)).toFixed(0);
    // Eliminar la fila de la tabla
    tabla.removeChild(fila);

    // Restar el total detalle del total de la venta
    actualizarTotal(-total_detalle_a_eliminar);

    // Restar el IVA correspondiente
    if (ivaDescripcion === 10) {
        actualizarTotalIVA(-total_iva_10, 0);
    } else if (ivaDescripcion === 5) {
        actualizarTotalIVA(0, -total_iva_5);
    }
}

function actualizarTotal(nuevoTotalDetalle) {
    const total_venta = document.getElementById("total_venta");
    const totalVentaActual = parseFloat(total_venta.value) || 0;
    const nuevoTotalVenta = totalVentaActual + nuevoTotalDetalle;
    total_venta.value = nuevoTotalVenta.toFixed(0);
    const totalVentaModal = document.getElementById("totalVentaModal");
    totalVentaModal.value = nuevoTotalVenta.toLocaleString('es-ES');
}

function actualizarTotalIVA(iva10, iva5) {
    const totalIva10 = document.getElementById('total_iva_10');
    const totalIva5 = document.getElementById('total_iva_5');
    totalIva10.value = ((parseFloat(totalIva10.value) || 0) + iva10).toFixed(0);
    totalIva5.value = ((parseFloat(totalIva5.value) || 0) + iva5).toFixed(0);
}

function abrirModalVuelto() {
    // Validaciones
    if(document.getElementById("cliente").value == ""){
        alert("Por favor, selecciona un cliente antes de continuar.");
        return;
    }
    const totalVenta = parseFloat(document.getElementById("total_venta").value) || 0;
    const totalVentaModal = document.getElementById("totalVentaModal");

    if(totalVenta == 0){
        alert("No hay productos en la venta.");
        return;
    }

    // Actualizar el total en el modal
    totalVentaModal.value = totalVenta.toLocaleString('es-ES');

    // Limpiar campos anteriores
    document.getElementById("efectivo").value = "";
    document.getElementById("pos").value = "";
    document.getElementById("transferencia").value = "";
    document.getElementById("mensajeVuelto").textContent = "";

    // Obtener el modal y mostrarlo
    const modalElement = document.getElementById('modalCobro');
    modalElement.style.display = 'block';
    modalElement.classList.add('show');
    modalElement.setAttribute('aria-modal', 'true');
    modalElement.setAttribute('aria-hidden', 'false');

    // Agregar backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade show';
    backdrop.id = 'modal-backdrop';
    document.body.appendChild(backdrop);

    // Prevenir scroll del body
    document.body.classList.add('modal-open');

    // Enfocar campo
    setTimeout(() => {
        document.getElementById("efectivo").focus();
    }, 500);
}

function cerrarModal() {
    const modalElement = document.getElementById('modalCobro');
    const backdrop = document.getElementById('modal-backdrop');

    modalElement.style.display = 'none';
    modalElement.classList.remove('show');
    modalElement.setAttribute('aria-hidden', 'true');
    modalElement.removeAttribute('aria-modal');

    if (backdrop) {
        backdrop.remove();
    }

    document.body.classList.remove('modal-open');
}


// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Cerrar modal al hacer clic en el backdrop
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-backdrop')) {
            cerrarModal();
        }
    });

    // Cerrar modal con ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            cerrarModal();
        }
    });

    // Auto-cálculo del vuelto
    ['efectivo', 'pos', 'transferencia'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('input', calcularVuelto);
        }
    });
});

// Función para calcular el vuelto
function calcularVuelto() {
    const totalVenta = parseFloat(document.getElementById("total_venta").value) || 0;
    const totalVentaModal = document.getElementById("totalVentaModal");
    totalVentaModal.value = totalVenta.toLocaleString('es-ES');
    console.log("totalVentaModal:", totalVentaModal.value, "tipo de dato:", typeof totalVentaModal.value)
    const montoEfectivo = parseFloat(document.getElementById("efectivo").value) || 0;
    const montoPos = parseFloat(document.getElementById("pos").value) || 0;
    const montoTransferencia = parseFloat(document.getElementById("transferencia").value) || 0;
    const mensajeVuelto = document.getElementById("mensajeVuelto");
    const montoApagar = totalVenta - montoPos - montoTransferencia

    if (montoEfectivo >= montoApagar) {
        const vuelto = montoEfectivo - montoApagar;
        const vueltoFormateado = vuelto.toFixed(0).toLocaleString('es-ES');  // Formato en miles
        mensajeVuelto.textContent = `Vuelto: ₲${vueltoFormateado}`;

    } else {
        mensajeVuelto.textContent = "Monto recibido es insuficiente para cubrir el total de la venta.";
    }
}

function enviarFormulario() {
    const totalVenta = parseFloat(document.getElementById("total_venta").value) || 0;
    const montoEfectivo = parseFloat(document.getElementById("efectivo").value) || 0;
    const montoPos = parseFloat(document.getElementById("pos").value) || 0;
    const montoTransferencia = parseFloat(document.getElementById("transferencia").value) || 0;
    const montoPagado = montoEfectivo + montoPos + montoTransferencia;

    if (montoPagado < totalVenta) {
        window.alert('No se ha pagado el total de la venta');
    } else if(montoPos > totalVenta){
        window.alert("El monto en POS excede al monto total de la venta.")
    } else if(montoTransferencia > totalVenta){
        window.alert("El monto en Transferencia excede al monto total de la venta.")
    } else {
        const tabla = document.getElementById("tablaProductos").querySelector("tbody");
        const productosSeleccionados = [];

        for (let fila of tabla.rows) {
            const idProducto = fila.getAttribute('data-producto-id');
            const cantidad = parseInt(fila.cells[1].innerText, 10);
            const totalDetalle = parseFloat(fila.cells[3].innerText) || 0;
            const iva10 = parseFloat(fila.cells[4].innerText) || 0;
            const iva5 = parseFloat(fila.cells[5].innerText) || 0;
            const productoObj = {
                id_producto: idProducto,
                cantidad: cantidad,
                total_detalle: totalDetalle.toFixed(0),
                total_detalle_iva_10: iva10.toFixed(0),
                total_detalle_iva_5: iva5.toFixed(0),
            };
            productosSeleccionados.push(productoObj);
        }

        document.getElementById('efectivo').value = totalVenta - montoPos - montoTransferencia;

        document.getElementById('productos_json').value = JSON.stringify(productosSeleccionados);

        document.querySelector("form").submit();
    }

}
