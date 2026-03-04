const productosBody = document.getElementById("productosBody");
const searchInput = document.getElementById("searchInput");
const pagination = document.getElementById("pagination");
const clearBtn = document.getElementById("clearBtn");

if (productosBody && searchInput && pagination) {
    let productos = [];
    let currentPage = 1;
    const itemsPerPage = 10;

    function formatNumber(value) {
        const number = parseFloat(value);
        if (Number.isNaN(number)) return "";
        return number.toLocaleString("es-PY", { maximumFractionDigits: 0 });
    }

    function formatDate(value) {
        if (!value) return "";
        // Si viene como YYYY-MM-DD
        if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            const [y, m, d] = value.split("-");
            return `${d}/${m}/${y}`;
        }
        return value;
    }

    function getFiltered() {
        const query = searchInput.value.toLowerCase().trim();
        if (!query) return productos;
        return productos.filter((p) => (p.nombre || "").toLowerCase().includes(query));
    }

    function renderTable() {
        productosBody.innerHTML = "";
        const filtered = getFiltered();

        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const pageItems = filtered.slice(start, end);

        if (pageItems.length === 0) {
            productosBody.innerHTML = '<tr><td colspan="9" class="text-center">No se encontraron productos</td></tr>';
            return;
        }

        const rows = pageItems.map((p) => `
            <tr>
                <td>${p.nombre ?? ""}</td>
                <td class="text-end">${formatNumber(p.precio_actual)}</td>
                <td class="text-end">${formatNumber(p.precio_pedidos_ya)}</td>
                <td class="text-end">${formatNumber(p.stock_minimo)}</td>
                <td class="text-end">${formatNumber(p.stock_actual)}</td>
                <td class="text-center">${formatDate(p.vencimiento)}</td>
                <td class="text-end">${formatNumber(p.costo_actual)}</td>
                <td class="text-center">${p.id_medida__descripcion ?? ""}</td>
                <td class="text-center">
                    <a type="button" class="btn btn-crear btn-sm" href="/productos/editar_producto/${p.id_producto}">
                        <i class="bi bi-pen"></i>
                    </a>
                    <a type="button" class="btn btn-cancelar btn-sm"
                       data-bs-toggle="modal"
                       data-bs-target="#confirmarEliminarModal${p.id_producto}">
                        <i class="bi bi-trash"></i>
                    </a>
                    <div class="modal fade" id="confirmarEliminarModal${p.id_producto}" tabindex="-1" aria-hidden="true">
                        <div class="modal-dialog modal-dialog-centered">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title">Confirmar eliminación</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                                </div>
                                <div class="modal-body">
                                    ¿Estás seguro de que deseas eliminar el producto <span class="fw-bold">${p.nombre ?? ""}</span>?
                                    Esta acción no se puede deshacer.
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                    <a href="/productos/eliminar_producto/${p.id_producto}" class="btn btn-danger">Eliminar</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `);

        productosBody.innerHTML = rows.join("");
    }

    function renderPagination() {
        pagination.innerHTML = "";
        const filtered = getFiltered();
        const totalPages = Math.ceil(filtered.length / itemsPerPage);

        if (totalPages <= 1) return;

        for (let i = 1; i <= totalPages; i += 1) {
            const li = document.createElement("li");
            li.classList.add("page-item");
            if (i === currentPage) li.classList.add("active");

            li.innerHTML = `<a class="page-link m-1" href="#">${i}</a>`;
            li.addEventListener("click", (e) => {
                e.preventDefault();
                currentPage = i;
                renderTable();
                renderPagination();
            });
            pagination.appendChild(li);
        }
    }

    fetch("/productos/productos_json/")
        .then((res) => res.json())
        .then((data) => {
            productos = data || [];
            renderTable();
            renderPagination();
        });

    searchInput.addEventListener("input", () => {
        currentPage = 1;
        renderTable();
        renderPagination();
    });

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            searchInput.value = "";
            currentPage = 1;
            renderTable();
            renderPagination();
        });
    }
}
