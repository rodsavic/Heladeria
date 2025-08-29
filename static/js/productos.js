let productos = [];
let currentPage = 1;
const itemsPerPage = 10;

// Cargar productos desde JSON
fetch("/productos/productos_json/")  // O usa la URL que tengas
    .then(res => res.json())
    .then(data => {
        productos = data;
        renderTable();
        renderPagination();
    });

// Renderizar tabla según página y filtro
function renderTable() {
    const tbody = document.getElementById("productosBody");
    tbody.innerHTML = "";

    const query = document.getElementById("searchInput").value.toLowerCase();
    const filtered = productos.filter(p => p.nombre.toLowerCase().includes(query));

    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageItems = filtered.slice(start, end);

    if (pageItems.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center">No se encontraron productos</td></tr>`;
        return;
    }

    pageItems.forEach(p => {
        tbody.innerHTML += `
            <tr>
                <td>${p.nombre}</td>
                <td class="text-center">${p.precio_actual?.toLocaleString() ?? ''}</td>
                <td class="text-center">${p.stock_minimo?.toLocaleString() ?? ''}</td>
                <td class="text-center">${p.stock_actual?.toLocaleString() ?? ''}</td>
                <td class="text-center">${p.vencimiento ?? ''}</td>
                <td class="text-center">${p.costo_actual?.toLocaleString() ?? ''}</td>
                <td class="text-center">${p.id_medida__descripcion ?? ''}</td>
                <td class="text-center">
                    <a type="button" class="btn btn-crear btn-sm" href="/productos/editar_producto/${p.id_producto}">
                        <i class="bi bi-pen"></i>
                    </a>
                    <a type="button" class="btn btn-cancelar btn-sm"
                           data-bs-toggle="modal"
                           data-bs-target="#confirmarEliminarModal${p.id_producto}">
                            <i class="bi bi-trash"></i>
                        </a>
                        <div class="modal fade" id="confirmarEliminarModal${p.id_producto}" tabindex="-1"
                             aria-hidden="true">
                            <div class="modal-dialog modal-dialog-centered">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">Confirmar eliminación</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"
                                                aria-label="Cerrar"></button>
                                    </div>
                                    <div class="modal-body">
                                        ¿Estás seguro de que deseas eliminar el producto <span class="fw-bold">${p.nombre}</span>?
                                        Esta acción no se puede deshacer.
                                    </div>
                                    <div class="modal-footer">
                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                            Cancelar
                                        </button>
                                        <a href="/productos/eliminar_producto/${p.id_producto}"
                                           class="btn btn-danger">Eliminar</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                </td>
            </tr>
        `;
    });
}

// Renderizar paginación
function renderPagination() {
    const pagination = document.getElementById("pagination");
    pagination.innerHTML = "";

    const query = document.getElementById("searchInput").value.toLowerCase();
    const filtered = productos.filter(p => p.nombre.toLowerCase().includes(query));
    const totalPages = Math.ceil(filtered.length / itemsPerPage);

    for (let i = 1; i <= totalPages; i++) {
        const li = document.createElement("li");
        li.classList.add("page-item");
        if (i === currentPage) li.classList.add("active");

        li.innerHTML = `<a class="page-link m-1" href="#">${i}</a>`;
        li.addEventListener("click", function (e) {
            e.preventDefault();
            currentPage = i;
            renderTable();
            renderPagination();
        });
        pagination.appendChild(li);
    }
}

// Filtro en tiempo real
document.getElementById("searchInput").addEventListener("keyup", function () {
    currentPage = 1;
    renderTable();
    renderPagination();
});

// Botón limpiar filtro
document.getElementById("clearBtn").addEventListener("click", function () {
    document.getElementById("searchInput").value = "";
    currentPage = 1;
    renderTable();
    renderPagination();
});
