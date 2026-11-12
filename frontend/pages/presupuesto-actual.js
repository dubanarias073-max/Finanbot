/* FinanBot · "El presupuesto que tienes actualmente"
 * Tarjeta compacta debajo del saludo: título grande con degradado a la izquierda y el
 * balance total a la derecha. En el Dashboard queda en la misma fila que el tip financiero.
 * El perfil pequeño se queda arriba a la derecha (el del dashboard ya existe; en Mis Finanzas
 * y Calendario se agrega uno igual).
 * Uso, una línea al final del <body> de dashboard.html, finanzas.html y calendario.html:
 *   <script src="presupuesto-actual.js"></script>
 * El balance es el mismo del "Acumulado total" del Dashboard (no cuenta fechas futuras).
 */
(function () {
    'use strict';
    if (window.__presupuestoActual) return;
    window.__presupuestoActual = true;

    var CSS = [
        '.fb-pres-row{display:grid;grid-template-columns:minmax(0,1.9fr) minmax(0,1fr);gap:20px;margin:0 0 24px;align-items:stretch;}',
        '.fb-pres-row:not(:has(.tip-card.visible)){grid-template-columns:minmax(0,1fr);}',
        '.fb-pres-row .tip-card{margin-bottom:0;}',

        '.fb-pres{position:relative;overflow:hidden;display:flex;align-items:center;justify-content:space-between;gap:18px;',
        '  padding:26px 30px;min-height:116px;border-radius:20px;',
        '  background:var(--card-bg,rgba(255,255,255,.04));border:1px solid var(--card-border,rgba(139,92,246,.15));}',
        '.fb-pres::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;',
        '  background:linear-gradient(90deg,transparent 2%,#5EEAD4 30%,#60a5fa 65%,transparent 98%);opacity:.9;}',
        '.fb-pres.negativo::before{background:linear-gradient(90deg,transparent 2%,#f472b6 30%,#8B5CF6 65%,transparent 98%);}',
        '.fb-pres-texto{min-width:0;}',
        '.fb-pres-titulo{font-size:clamp(20px,2.6vw,31px);font-weight:800;line-height:1.15;letter-spacing:-.3px;',
        '  background:linear-gradient(90deg,#60a5fa,#5EEAD4);-webkit-background-clip:text;background-clip:text;',
        '  -webkit-text-fill-color:transparent;color:#60a5fa;}',
        '.fb-pres-sub{font-size:12px;color:var(--muted,#6b7280);margin-top:6px;}',
        '.fb-pres-valor{font-size:clamp(28px,3.6vw,42px);font-weight:800;line-height:1;white-space:nowrap;color:var(--fb-text,#fff);}',
        '.fb-pres.negativo .fb-pres-valor{color:#f472b6;}',

        '.fb-pres-perfil{display:flex;align-items:center;gap:10px;background:rgba(139,92,246,.1);border:1px solid rgba(139,92,246,.2);',
        '  border-radius:50px;padding:6px 15px 6px 7px;max-width:100%;}',
        '.fb-pres-avatar{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#6D5BD0,#5EEAD4);display:flex;',
        '  align-items:center;justify-content:center;font-weight:700;font-size:13px;color:#fff;overflow:hidden;flex-shrink:0;}',
        '.fb-pres-avatar img{width:100%;height:100%;object-fit:cover;}',
        '.fb-pres-nombre{font-size:13px;color:var(--fb-lav,#c4b5fd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;}',

        '@media (max-width:992px){.fb-pres-row{grid-template-columns:minmax(0,1fr)!important;gap:16px;}}',
        '@media (max-width:640px){',
        '  .fb-pres{padding:20px 18px;min-height:0;flex-direction:column;align-items:flex-start;gap:12px;}',
        '  .fb-pres-nombre{display:none;}.fb-pres-perfil{padding:6px;}',
        '}',
        '@media (max-width:760px){.topbar-actions .fb-pres-perfil{grid-column:1/-1;justify-self:end;}}'
    ].join('\n');

    function token() {
        try {
            return (window.FinanbotLocal && window.FinanbotLocal.active)
                ? window.FinanbotLocal.token
                : localStorage.getItem('token');
        } catch (e) { return null; }
    }
    function hoyIso() {
        try { if (window.FinanbotTime && FinanbotTime.todayIso) return FinanbotTime.todayIso(); } catch (e) {}
        var d = new Date();
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }
    function auth() { return { headers: { Authorization: 'Bearer ' + token() } }; }
    function $(id) { return document.getElementById(id); }
    function conSigno(v) { return (v < 0 ? '-' : '') + '$' + Math.abs(Math.round(v)).toLocaleString('es-CO'); }

    var perfilPropio = false;

    function montar() {
        var main = document.querySelector('.main');
        if (!main) return false;
        if ($('fbPres')) return true;

        var style = document.createElement('style');
        style.textContent = CSS;
        document.head.appendChild(style);

        var card = document.createElement('section');
        card.className = 'fb-pres';
        card.id = 'fbPres';
        card.innerHTML =
            '<div class="fb-pres-texto">' +
                '<div class="fb-pres-titulo">El presupuesto que tienes actualmente</div>' +
                '<div class="fb-pres-sub" id="fbPresSub">Balance total acumulado</div>' +
            '</div>' +
            '<div class="fb-pres-valor" id="fbPresValor">$0</div>';

        var fila = document.createElement('div');
        fila.className = 'fb-pres-row';
        fila.appendChild(card);

        // Debajo del saludo y los botones (la barra .topbar)
        var topbar = main.querySelector('.topbar');
        if (topbar && topbar.parentNode === main) main.insertBefore(fila, topbar.nextSibling);
        else main.insertBefore(fila, main.firstChild);

        // Dashboard: el tip financiero se acomoda en la misma fila, a la derecha
        var tip = $('tipCard');
        if (tip) fila.appendChild(tip);

        // Perfil pequeño arriba a la derecha: si la página no lo tiene, se agrega uno igual
        if (topbar && !topbar.querySelector('.user-badge')) {
            var cont = topbar.querySelector('.topbar-right, .topbar-actions') || topbar;
            var p = document.createElement('div');
            p.className = 'fb-pres-perfil';
            p.innerHTML = '<div class="fb-pres-avatar" id="fbPresAvatar">U</div><span class="fb-pres-nombre" id="fbPresNombre"></span>';
            cont.appendChild(p);
            perfilPropio = true;
        }
        return true;
    }

    function pintarNombre(nombre, correo) {
        var n = (nombre || '').trim() || (correo || '').trim() || 'Usuario';
        var elN = $('fbPresNombre'), elA = $('fbPresAvatar');
        if (elN) elN.textContent = n;
        if (elA && !elA.querySelector('img')) elA.textContent = n.charAt(0).toUpperCase();
    }

    async function cargarPerfil() {
        if (!perfilPropio) return;           // en el dashboard ya lo llena su propio script
        try {
            if (window.FinanbotLocal && window.FinanbotLocal.active) {
                var r = await fetch('/api/perfil/');
                if (r.ok) { var p = await r.json(); pintarNombre(p.nombre || 'Invitado', p.correo); }
            } else {
                var u = JSON.parse(localStorage.getItem('usuario') || '{}');
                pintarNombre(u.nombre, u.correo);
            }
        } catch (e) { /* queda "Usuario" */ }
        if (!token()) return;
        try {
            var f = await fetch('/api/perfil/foto', auth());
            if (!f.ok) return;
            var img = document.createElement('img');
            img.alt = 'Foto de perfil';
            img.src = URL.createObjectURL(await f.blob());
            var av = $('fbPresAvatar');
            if (av) { av.textContent = ''; av.appendChild(img); }
        } catch (e) { /* sin foto: se queda la inicial */ }
    }

    // El número "corre" suavemente hasta el nuevo valor
    var valorMostrado = 0, animId = null;
    function animarValor(destino) {
        var el = $('fbPresValor');
        if (!el) return;
        if (animId) cancelAnimationFrame(animId);
        var reducir = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
        var desde = valorMostrado, t0 = null, dur = 700;
        if (reducir || desde === destino) { valorMostrado = destino; el.textContent = conSigno(destino); return; }
        function paso(t) {
            if (t0 === null) t0 = t;
            var k = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - k, 3);
            el.textContent = conSigno(desde + (destino - desde) * e);
            if (k < 1) animId = requestAnimationFrame(paso);
            else { valorMostrado = destino; el.textContent = conSigno(destino); }
        }
        animId = requestAnimationFrame(paso);
    }

    async function cargarBalance() {
        if (!token()) return;
        try {
            var r = await fetch('/api/transacciones/', auth());
            if (!r.ok) return;
            var data = await r.json();
            var lista = Array.isArray(data) ? data : (data.transacciones || []);
            var hoy = hoyIso(), ing = 0, gas = 0;
            lista.forEach(function (t) {
                if ((t.fecha || '').slice(0, 10) > hoy) return;          // fechas futuras no cuentan
                var m = Number(t.monto) || 0;
                if (t.tipo === 'ingreso') ing += m; else if (t.tipo === 'gasto') gas += m;
            });
            var bal = Math.round(ing - gas);
            var card = $('fbPres');
            if (!card) return;
            card.classList.toggle('negativo', bal < 0);
            animarValor(bal);
            $('fbPresSub').textContent = bal < 0
                ? 'Estás gastando más de lo que has recibido'
                : bal === 0 ? 'Aún no tienes saldo disponible' : 'Balance total acumulado: ingresos menos gastos';
        } catch (e) { console.error('Presupuesto actual:', e); }
    }

    window.actualizarPresupuesto = cargarBalance;

    // Se refresca solo cuando la página guarda/edita/borra movimientos o metas.
    var fetchOriginal = window.fetch;
    if (typeof fetchOriginal === 'function') {
        window.fetch = function (url, opts) {
            var p = fetchOriginal.apply(this, arguments);
            try {
                var metodo = ((opts && opts.method) || 'GET').toUpperCase();
                var u = String(typeof url === 'string' ? url : (url && url.url) || '');
                if (metodo !== 'GET' && /\/api\/(transacciones|metas)/.test(u)) {
                    p.then(function (res) { if (res && res.ok) setTimeout(cargarBalance, 500); }).catch(function () {});
                }
            } catch (e) {}
            return p;
        };
    }
    document.addEventListener('visibilitychange', function () { if (!document.hidden) cargarBalance(); });

    function iniciar() {
        if (!montar()) return;
        cargarPerfil();
        cargarBalance();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
    else iniciar();
})();