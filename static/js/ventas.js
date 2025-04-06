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

let productosSeleccionados   = [];

function agregarProductoATabla() {
    const selectProducto  = document.getElementById("selectProducto");
    const cantidadInput  = parseFloat(document.getElementById("cantidad").value) || 0;
    const precio = parseFloat(selectProducto.options[selectProducto.selectedIndex].getAttribute('data-precio')) || 0;
    const cantidad = parseInt(cantidadInput, 10);
    const idProducto = selectProducto.value;

    if (!idProducto || cantidad <= 0) {
        alert("Selecciona un producto y una cantidad válida.");
        return;
    }

    const idIva = parseInt(selectProducto.options[selectProducto.selectedIndex].getAttribute('data-idiva')) || 0;
    const nombreProducto = selectProducto.options[selectProducto.selectedIndex].text;

    if (nombreProducto && cantidad > 0) {
        const totalDetalle = cantidad * precio;
        let iva = 0;

        // Calcular IVA en base al valor del id_iva
        if (idIva === 10) {
            iva = totalDetalle / 11;
            actualizarTotalIVA(iva, 0);
        } else if (idIva === 5) {
            iva = totalDetalle / 21;
            actualizarTotalIVA(0, iva);
        }

        // Buscar si el producto ya está en la tabla
        const productoExistente = productosSeleccionados .find(prod => prod.id_producto === idProducto);
        console.log("productoExistente: ", productoExistente);
        if (productoExistente) {
            // Actualizar producto existente
            productoExistente.cantidad += cantidad;
            productoExistente.total_detalle = (productoExistente.cantidad * precio).toFixed(0);

            // Actualizar la fila en la tabla
            const fila = document.querySelector(`tr[data-producto-id='${idProducto}']`);
            fila.cells[1].innerText = productoExistente.cantidad;
            fila.cells[3].innerText = productoExistente.total_detalle;
            fila.cells[4].innerText = (parseFloat(fila.cells[4].innerText) + iva).toFixed(0);
        } else {
            // Insertar nueva fila si no existe el producto
            const tabla = document.getElementById("tablaProductos").querySelector("tbody");
            const nuevaFila = tabla.insertRow();
            nuevaFila.setAttribute('data-producto-id', idProducto); // Añadir ID de producto a la fila

            const celdaProducto = nuevaFila.insertCell(0);
            const celdaCantidad = nuevaFila.insertCell(1);
            const celdaPrecio = nuevaFila.insertCell(2);
            const celdaTotalDetalle = nuevaFila.insertCell(3);
            const celdaIva = nuevaFila.insertCell(4);
            const celdaAccion = nuevaFila.insertCell(5);

            celdaProducto.innerText = nombreProducto;
            celdaCantidad.innerText = cantidad;
            celdaPrecio.innerText = precio.toFixed(0);
            celdaTotalDetalle.innerText = totalDetalle.toFixed(0);
            celdaIva.innerText = iva.toFixed(0);
            celdaAccion.innerHTML = `<button class="btn btn-sm btn-danger" title="Eliminar" onclick="eliminarProducto('${idProducto}', ${totalDetalle}, ${iva}, ${idIva})"><i class="bi bi-trash"></i></button>`;
            console.log("idProducto:", idProducto, "tipo de dato:", typeof idProducto)
            console.log("cantidad:", cantidad, "tipo de dato:", typeof cantidad)
            console.log("total_detalle:", totalDetalle, "tipo de dato:", typeof totalDetalle)
            const productoObj = {
                id_producto: idProducto,
                cantidad: cantidad,
                total_detalle: totalDetalle.toFixed(0)
            };
            productosSeleccionados .push(productoObj);
        }

        document.getElementById('productos_json').value = JSON.stringify(productosSeleccionados );

        actualizarTotal(totalDetalle);
        document.getElementById('cantidad').value = 1;
    } else if (cantidad < 1) {
        window.alert("La cantidad mínima es 1");
    } else {
        window.alert("Debe seleccionar al menos un producto.");
    }


}

function eliminarProducto(idProducto, totalDetalle, iva, idIva) {
    // Buscar la fila por el id_producto
    const tabla = document.getElementById("tablaProductos").querySelector("tbody");
    const fila = document.querySelector(`tr[data-producto-id='${idProducto}']`);
    const total_detalle_a_eliminar = (parseFloat(fila.cells[3].innerText)).toFixed(0)
    const total_iva = (parseFloat(fila.cells[4].innerText)).toFixed(0)
    // Eliminar la fila de la tabla
    tabla.removeChild(fila);

    // Eliminar producto de la lista de productos
    productosSeleccionados  = productosSeleccionados .filter(prod => prod.id_producto !== idProducto);

    // Actualizar el campo oculto con los productos restantes
    document.getElementById('productos_json').value = JSON.stringify(productosSeleccionados );

    // Restar el total detalle del total de la venta
    actualizarTotal(-total_detalle_a_eliminar);

    // Restar el IVA correspondiente
    if (idIva === 10) {
        actualizarTotalIVA(-total_iva, 0);
    } else if (idIva === 5) {
        actualizarTotalIVA(0, -total_iva);
    }
}

function actualizarTotal(nuevoTotalDetalle) {
    const total_venta = document.getElementById("total_venta");
    const totalVentaActual = parseFloat(total_venta.value) || 0;
    const nuevoTotalVenta = totalVentaActual + nuevoTotalDetalle;
    total_venta.value = nuevoTotalVenta.toFixed(0);
}

function actualizarTotalIVA(iva10, iva5) {
    const totalIva10 = document.getElementById('total_iva_10');
    const totalIva5 = document.getElementById('total_iva_5');

    totalIva10.value = ((parseFloat(totalIva10.value) || 0) + iva10).toFixed(0);
    totalIva5.value = ((parseFloat(totalIva5.value) || 0) + iva5).toFixed(0);
}

// Función para abrir el modal del vuelto
function abrirModalVuelto() {
    $('#modalCobro').modal('show');
    setTimeout(() => document.getElementById("efectivo").focus(), 500);
}

// Función para calcular el vuelto
function calcularVuelto() {
    const totalVenta = parseFloat(document.getElementById("total_venta").value) || 0;
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
    } else {
        document.querySelector("form").submit();
    }

}
