(function () {
    const TEXTO_ENVIANDO = 'Procesando...';

    function botonesDe(form) {
        const selector = 'button[type="submit"], button:not([type]), input[type="submit"]';
        const propios = Array.from(form.querySelectorAll(selector));
        const externos = form.id
            ? Array.from(document.querySelectorAll(`[form="${form.id}"]`)).filter(b => b.matches(selector))
            : [];
        return propios.concat(externos);
    }

    function conservarSubmitter(form, submitter) {
        // Un boton deshabilitado no se envia: se copia su name/value a un hidden.
        if (!submitter || !submitter.name) return;
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = submitter.name;
        hidden.value = submitter.value;
        hidden.dataset.envioUnico = 'submitter';
        form.appendChild(hidden);
    }

    function bloquear(form, submitter) {
        form.dataset.enviando = '1';
        conservarSubmitter(form, submitter);
        botonesDe(form).forEach(boton => {
            boton.disabled = true;
            if (boton.tagName === 'BUTTON') {
                boton.dataset.textoOriginal = boton.innerHTML;
                boton.innerHTML = `<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>${TEXTO_ENVIANDO}`;
            }
        });
    }

    function liberar(form) {
        delete form.dataset.enviando;
        form.querySelectorAll('input[data-envio-unico="submitter"]').forEach(i => i.remove());
        botonesDe(form).forEach(boton => {
            boton.disabled = false;
            if (boton.dataset.textoOriginal !== undefined) {
                boton.innerHTML = boton.dataset.textoOriginal;
                delete boton.dataset.textoOriginal;
            }
        });
    }

    function aplica(form) {
        return form instanceof HTMLFormElement
            && (form.getAttribute('method') || 'get').toLowerCase() === 'post'
            && !form.hasAttribute('data-permitir-reenvio');
    }

    // Captura: corta el reenvio antes que cualquier otro handler.
    document.addEventListener('submit', function (event) {
        const form = event.target;
        if (aplica(form) && form.dataset.enviando === '1') {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    }, true);

    // Burbuja: corre despues del onsubmit del form; si nadie cancelo el envio, se bloquea.
    document.addEventListener('submit', function (event) {
        const form = event.target;
        if (aplica(form) && !event.defaultPrevented) {
            bloquear(form, event.submitter);
        }
    });

    // Pagina restaurada desde el cache del navegador (boton atras): reactivar formularios.
    window.addEventListener('pageshow', function (event) {
        if (!event.persisted) return;
        document.querySelectorAll('form[data-enviando="1"]').forEach(liberar);
    });

    window.EnvioUnico = {
        /** Envia el form una sola vez. Devuelve false si ya estaba enviandose. */
        enviar: function (form) {
            if (!form || form.dataset.enviando === '1') return false;
            bloquear(form, null);
            form.submit();
            return true;
        },
        enviando: function (form) {
            return !!form && form.dataset.enviando === '1';
        },
        liberar: liberar,
    };
})();
