document.addEventListener('DOMContentLoaded', function() {
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('mainContent');
const sidebarToggle = document.getElementById('sidebarToggle');
const mobileToggle = document.getElementById('mobileToggle');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const sidebarLinks = document.querySelectorAll('.sidebar-link:not(.has-dropdown)');

// Función para detectar si estamos en móvil
function isMobile() {
    return window.innerWidth <= 768;
}

// Función para detectar si estamos en tablet/desktop
function isDesktop() {
    return window.innerWidth >= 769;
}

// Toggle del sidebar en desktop
if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        if (isDesktop()) {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('collapsed');

            // Cerrar dropdowns abiertos cuando se colapsa
            if (sidebar.classList.contains('collapsed')) {
                const openDropdowns = sidebar.querySelectorAll('.collapse.show');
                openDropdowns.forEach(dropdown => {
                    const bsCollapse = bootstrap.Collapse.getInstance(dropdown);
                    if (bsCollapse) {
                        bsCollapse.hide();
                    }
                });
            }
        }
    });
}

// Toggle del sidebar en móvil
if (mobileToggle) {
    mobileToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        if (isMobile()) {
            sidebar.classList.add('show');
            sidebarOverlay.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    });
}

// Cerrar sidebar con overlay
if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', function() {
        closeMobileSidebar();
    });
}

// Función para cerrar sidebar en móvil
function closeMobileSidebar() {
    sidebar.classList.remove('show');
    sidebarOverlay.classList.remove('show');
    document.body.style.overflow = '';
}

// Marcar enlace activo basado en URL actual
function setActiveLink() {
    const currentPath = window.location.pathname;
    sidebarLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Cerrar sidebar al hacer click en enlaces en móvil
sidebarLinks.forEach(link => {
    link.addEventListener('click', function(e) {
        if (isMobile()) {
            // Marcar como activo
            sidebarLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');

            // Cerrar sidebar después de un pequeño delay
            setTimeout(() => {
                closeMobileSidebar();
            }, 200);
        } else {
            // En desktop, solo cambiar la clase active
            sidebarLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        }
    });
});

// Manejar redimensionamiento de ventana
window.addEventListener('resize', function() {
    if (isDesktop()) {
        // En desktop/tablet, cerrar móvil sidebar si está abierto
        closeMobileSidebar();
        sidebar.classList.remove('show');
    } else {
        // En móvil, remover clase collapsed
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('collapsed');
    }
});

// Prevenir que clicks dentro del sidebar cierren el overlay
if (sidebar) {
    sidebar.addEventListener('click', function(e) {
        e.stopPropagation();
    });
}

// Prevenir que clicks en el logo naveguen cuando el sidebar está colapsado
const sidebarLogo = document.querySelector('.sidebar-logo');
if (sidebarLogo) {
    sidebarLogo.addEventListener('click', function(e) {
        if (sidebar.classList.contains('collapsed') && isDesktop()) {
            e.preventDefault();
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('collapsed');
        }
    });
}

// Manejar dropdowns en sidebar colapsado (hover effect)
const dropdownItems = sidebar.querySelectorAll('.sidebar-item:has(.has-dropdown)');

dropdownItems.forEach(item => {
    let hoverTimeout;

    item.addEventListener('mouseenter', function() {
        if (sidebar.classList.contains('collapsed') && isDesktop()) {
            clearTimeout(hoverTimeout);
            const dropdown = item.querySelector('.sidebar-dropdown');
            if (dropdown) {
                dropdown.style.display = 'block';
            }
        }
    });

    item.addEventListener('mouseleave', function() {
        if (sidebar.classList.contains('collapsed') && isDesktop()) {
            const dropdown = item.querySelector('.sidebar-dropdown');
            hoverTimeout = setTimeout(() => {
                if (dropdown) {
                    dropdown.style.display = 'none';
                }
            }, 300);
        }
    });
});

// Cerrar sidebar con tecla Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && isMobile() && sidebar.classList.contains('show')) {
        closeMobileSidebar();
    }
});

// Inicialización
if (isMobile()) {
    sidebar.classList.remove('collapsed');
    mainContent.classList.remove('collapsed');
}

// Establecer enlace activo al cargar la página
setActiveLink();
});