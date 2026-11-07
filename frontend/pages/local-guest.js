(function () {
    const GUEST_FLAG = 'finanbot_guest_mode';
    const DATA_KEY = 'finanbot_guest_data_v1';
    const GUEST_SETTING_PREFIX = 'finanbot_guest_setting_v1:';
    const guestSettings = new Set([
        'finanbot_regla_dist',
        'finanbot_prefs',
        'finanbot_notif_rec',
        'finanbot_simulacion_realizada',
        'finanbot_registro',
        'finanbot_tema',
    ]);
    const guestUrl = new URLSearchParams(location.search).get('invitado') === 'true';
    if (guestUrl) localStorage.setItem(GUEST_FLAG, '1');

    const storageGetItem = Storage.prototype.getItem;
    const storageSetItem = Storage.prototype.setItem;
    const storageRemoveItem = Storage.prototype.removeItem;
    function enModoInvitado() {
        return storageGetItem.call(localStorage, GUEST_FLAG) === '1';
    }
    function claveInvitado(storage, key) {
        return storage === localStorage && enModoInvitado() && guestSettings.has(String(key))
            ? GUEST_SETTING_PREFIX + key
            : key;
    }
    Storage.prototype.getItem = function (key) {
        return storageGetItem.call(this, claveInvitado(this, key));
    };
    Storage.prototype.setItem = function (key, value) {
        return storageSetItem.call(this, claveInvitado(this, key), value);
    };
    Storage.prototype.removeItem = function (key) {
        return storageRemoveItem.call(this, claveInvitado(this, key));
    };

    const originalFetch = window.fetch.bind(window);
    const defaults = {
        gasto: [
            ['🍔', 'Alimentación'], ['🚌', 'Transporte'], ['🏠', 'Arriendo'],
            ['💊', 'Salud'], ['🎬', 'Entretenimiento'], ['📚', 'Educación'],
            ['👗', 'Ropa'], ['⚡', 'Servicios'], ['🐾', 'Mascotas'],
            ['🎁', 'Regalos'], ['✈️', 'Viajes'], ['📦', 'Otros gastos'],
        ],
        ingreso: [
            ['💼', 'Salario'], ['🧑‍💻', 'Freelance'], ['📈', 'Inversión'],
            ['🏪', 'Negocio'], ['🎁', 'Regalo'], ['💵', 'Otros ingresos'],
        ],
    };

    function leerDatos() {
        try {
            const guardado = JSON.parse(localStorage.getItem(DATA_KEY) || 'null');
            if (guardado && typeof guardado === 'object') {
                const ocultas = guardado.categoriasOcultas || {};
                const eliminadas = guardado.categoriasEliminadas || {};
                return {
                    transacciones: Array.isArray(guardado.transacciones) ? guardado.transacciones : [],
                    metas: Array.isArray(guardado.metas) ? guardado.metas : [],
                    perfil: { nombre: 'Invitado', correo: '', ingreso_mensual: 0, meta_ahorro: 0, ...(guardado.perfil || {}) },
                    categorias: guardado.categorias || {},
                    categoriasOcultas: {
                        gasto: Array.isArray(ocultas.gasto) ? ocultas.gasto : [],
                        ingreso: Array.isArray(ocultas.ingreso) ? ocultas.ingreso : [],
                    },
                    categoriasEliminadas: {
                        gasto: Array.isArray(eliminadas.gasto) ? eliminadas.gasto : [],
                        ingreso: Array.isArray(eliminadas.ingreso) ? eliminadas.ingreso : [],
                    },
                    foto: guardado.foto || '',
                    nextId: Number(guardado.nextId) || 1,
                };
            }
        } catch (error) {
            console.error('No se pudieron leer los datos locales del modo invitado:', error);
        }
        return {
            transacciones: [],
            metas: [],
            perfil: { nombre: 'Invitado', correo: '', ingreso_mensual: 0, meta_ahorro: 0, fecha_salario: null },
            categorias: {},
            categoriasOcultas: { gasto: [], ingreso: [] },
            categoriasEliminadas: { gasto: [], ingreso: [] },
            foto: '',
            nextId: 1,
        };
    }

    let data = leerDatos();
    function guardar() {
        try {
            localStorage.setItem(DATA_KEY, JSON.stringify(data));
        } catch (error) {
            console.error('No se pudieron guardar los datos locales del modo invitado:', error);
            throw error;
        }
    }

    function respuestaJson(value, status = 200) {
        return new Response(JSON.stringify(value), {
            status,
            headers: { 'Content-Type': 'application/json; charset=utf-8' },
        });
    }

    function categorias(tipo) {
        const personalizadas = data.categorias[tipo] || [];
        const ocultas = data.categoriasOcultas[tipo] || [];
        const eliminadas = data.categoriasEliminadas[tipo] || [];
        const predeterminadas = defaults[tipo]
            .filter(([, nombre]) => !eliminadas.includes(nombre))
            .map(([icono, nombre]) => ({
                icono, nombre, tipo, oculta: ocultas.includes(nombre), personalizada: false,
                protegida: nombre === (tipo === 'gasto' ? 'Otros gastos' : 'Otros ingresos'),
            }));
        const otros = predeterminadas.find(c => c.protegida);
        const lista = [...predeterminadas.filter(c => !c.protegida), ...personalizadas];
        if (otros) lista.push(otros);
        return lista;
    }

    function serializarCategorias() {
        return Object.fromEntries(['gasto', 'ingreso'].map(tipo => [
            tipo, categorias(tipo).map(c => ({
                ...c, movimientos: data.transacciones.filter(t => t.categoria === c.nombre).length,
            })),
        ]));
    }

    function parseBody(init) {
        if (!init || !init.body || typeof init.body !== 'string') return {};
        try { return JSON.parse(init.body); }
        catch (error) {
            console.error('Solicitud local de invitado con JSON inválido:', error);
            throw error;
        }
    }

    function csvBlob(rows) {
        const csv = rows.map(row => row.map(value =>
            `"${String(value ?? '').replace(/"/g, '""')}"`,
        ).join(',')).join('\r\n');
        return new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' });
    }

    function pdfBlob(titulo, lineas) {
        const limpiar = texto => String(texto).normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^\x20-\x7E]/g, '?')
            .replace(/[()\\]/g, '\\$&')
            .slice(0, 110);
        const contenido = ['BT', '/F1 11 Tf', '50 790 Td', '(FinanBot - ' + limpiar(titulo) + ') Tj'];
        lineas.slice(0, 48).forEach(linea => contenido.push('0 -15 Td', `(${limpiar(linea)}) Tj`));
        contenido.push('ET');
        const stream = contenido.join('\n');
        const objetos = [
            '<< /Type /Catalog /Pages 2 0 R >>',
            '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
            '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
            `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
        ];
        let pdf = '%PDF-1.4\n';
        const offsets = [0];
        objetos.forEach((objeto, indice) => {
            offsets.push(pdf.length);
            pdf += `${indice + 1} 0 obj\n${objeto}\nendobj\n`;
        });
        const xref = pdf.length;
        pdf += `xref\n0 ${offsets.length}\n0000000000 65535 f \n`;
        offsets.slice(1).forEach(offset => { pdf += `${String(offset).padStart(10, '0')} 00000 n \n`; });
        pdf += `trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
        return new Blob([pdf], { type: 'application/pdf' });
    }

    function mesActualLocal() {
        const hoy = new Date();
        return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
    }

    function fechaActualLocal() {
        const hoy = new Date();
        return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
    }

    async function atenderLocal(path, init, search) {
        const metodo = (init?.method || 'GET').toUpperCase();
        const body = parseBody(init);
        const transacciones = data.transacciones;
        const metas = data.metas;

        if (path === '/api/transacciones/' || path === '/api/transacciones') {
            if (metodo === 'GET') return respuestaJson([...transacciones].sort((a, b) => (b.fecha || '').localeCompare(a.fecha || '')));
            if (metodo === 'POST') {
                const nueva = { ...body, id: data.nextId++, monto: Number(body.monto), fecha: body.fecha || fechaActualLocal() };
                transacciones.push(nueva); guardar();
                return respuestaJson(nueva, 201);
            }
        }
        if (path === '/api/transacciones/categorias/mias') {
            if (metodo === 'GET') return respuestaJson(serializarCategorias());
            if (metodo === 'POST') {
                const tipo = body.tipo;
                const nombre = String(body.nombre || '').trim();
                if (!['gasto', 'ingreso'].includes(tipo) || nombre.length < 2) {
                    return respuestaJson({ detail: 'Indica un nombre válido y el tipo de categoría.' }, 400);
                }
                const predeterminada = defaults[tipo].find(([, existente]) => existente.toLowerCase() === nombre.toLowerCase());
                if (predeterminada && (data.categoriasEliminadas[tipo] || []).includes(predeterminada[1])) {
                    data.categoriasEliminadas[tipo] = data.categoriasEliminadas[tipo].filter(c => c !== predeterminada[1]);
                    data.categoriasOcultas[tipo] = data.categoriasOcultas[tipo].filter(c => c !== predeterminada[1]);
                    guardar();
                    return respuestaJson({ mensaje: 'Categoría predeterminada restaurada.', nombre: predeterminada[1] });
                }
                if (categorias(tipo).some(c => c.nombre.toLowerCase() === nombre.toLowerCase())) {
                    return respuestaJson({ detail: 'Ya existe una categoría con ese nombre.' }, 409);
                }
                data.categorias[tipo] ||= [];
                data.categorias[tipo].push({
                    nombre, tipo, icono: body.icono || (tipo === 'gasto' ? '📦' : '💵'),
                    oculta: false, personalizada: true, protegida: false,
                });
                guardar();
                return respuestaJson({ mensaje: 'Categoría creada localmente.', nombre, tipo }, 201);
            }
        }
        const categoria = path.match(/^\/api\/transacciones\/categorias\/mias\/(.+)$/);
        if (categoria && metodo === 'PATCH') {
            const nombre = decodeURIComponent(categoria[1]);
            const item = ['gasto', 'ingreso'].flatMap(categorias).find(c => c.nombre === nombre);
            if (!item) return respuestaJson({ detail: 'Categoría no encontrada.' }, 404);
            if (item.protegida && body.oculta) {
                return respuestaJson({ detail: 'La categoría Otros no se puede ocultar.' }, 400);
            }
            if (item.personalizada) {
                const propia = data.categorias[item.tipo].find(c => c.nombre === nombre);
                if (typeof body.oculta === 'boolean') propia.oculta = body.oculta;
                if (body.icono) propia.icono = String(body.icono).slice(0, 10);
            } else if (typeof body.oculta === 'boolean') {
                const ocultas = data.categoriasOcultas[item.tipo];
                data.categoriasOcultas[item.tipo] = body.oculta
                    ? [...new Set([...ocultas, nombre])]
                    : ocultas.filter(c => c !== nombre);
            }
            guardar();
            return respuestaJson({ mensaje: 'Categoría actualizada localmente.' });
        }
        if (categoria && metodo === 'DELETE') {
            const nombre = decodeURIComponent(categoria[1]);
            const item = ['gasto', 'ingreso'].flatMap(categorias).find(c => c.nombre === nombre);
            if (!item) return respuestaJson({ detail: 'Categoría no encontrada.' }, 404);
            if (item.protegida) return respuestaJson({ detail: 'La categoría Otros no se puede eliminar.' }, 400);
            const movidos = data.transacciones.filter(t => t.categoria === nombre).length;
            const tipo = item.tipo;
            const destino = tipo === 'gasto' ? 'Otros gastos' : 'Otros ingresos';
            data.transacciones = data.transacciones.map(t => t.categoria === nombre
                ? { ...t, categoria: destino, icono: tipo === 'gasto' ? '📦' : '💵' }
                : t);
            if (item.personalizada) {
                data.categorias[tipo] = data.categorias[tipo].filter(c => c.nombre !== nombre);
            } else {
                data.categoriasEliminadas[tipo].push(nombre);
            }
            guardar();
            return respuestaJson({ mensaje: 'Categoría eliminada localmente.', movidos, destino });
        }
        if (path === '/api/transacciones/categorias' && metodo === 'GET') {
            return respuestaJson({
                ...Object.fromEntries(['gasto', 'ingreso'].map(tipo => [
                    tipo, categorias(tipo).map(({ nombre, icono }) => ({ nombre, icono })),
                ])),
                meta: [],
            });
        }
        if (path === '/api/transacciones/periodos' && metodo === 'GET') {
            const grupos = {};
            transacciones.forEach(t => {
                const key = (t.fecha || '').slice(0, 7);
                if (!key) return;
                grupos[key] ||= [];
                grupos[key].push(t);
            });
            return respuestaJson(Object.entries(grupos).sort(([a], [b]) => b.localeCompare(a)).map(([key, lista], index) => {
                const ingresos = lista.filter(t => t.tipo === 'ingreso').reduce((s, t) => s + t.monto, 0);
                const gastos = lista.filter(t => t.tipo === 'gasto').reduce((s, t) => s + t.monto, 0);
                const [anio, mes] = key.split('-').map(Number);
                return {
                    id: anio * 100 + mes, anio, mes, label: `${String(mes).padStart(2, '0')}/${anio}`,
                    ingresos_total: ingresos, gastos_total: gastos, balance: ingresos - gastos,
                    activo: index === 0 && key === mesActualLocal(),
                };
            }));
        }
        const periodo = path.match(/^\/api\/transacciones\/periodos\/([^/]+)$/);
        if (periodo && metodo === 'DELETE') {
            const id = Number(decodeURIComponent(periodo[1]));
            const anio = Math.floor(id / 100), mes = id % 100;
            if (!Number.isInteger(id) || mes < 1 || mes > 12) {
                return respuestaJson({ detail: 'Identificador de periodo inválido.' }, 400);
            }
            const key = `${anio}-${String(mes).padStart(2, '0')}`;
            const antes = data.transacciones.length;
            data.transacciones = data.transacciones.filter(t => (t.fecha || '').slice(0, 7) !== key);
            if (data.transacciones.length === antes) return respuestaJson({ detail: 'No hay movimientos en ese periodo.' }, 404);
            guardar();
            return respuestaJson({ mensaje: 'Periodo eliminado.' });
        }
        if (path === '/api/transacciones/periodos/reset' && metodo === 'POST') {
            const mesActual = mesActualLocal();
            const antes = data.transacciones.length;
            data.transacciones = data.transacciones.filter(t => (t.fecha || '').slice(0, 7) !== mesActual);
            guardar();
            return respuestaJson({ mensaje: `Mes actual reiniciado (${antes - data.transacciones.length} movimientos eliminados).` });
        }
        const transaccion = path.match(/^\/api\/transacciones\/(\d+)$/);
        if (transaccion) {
            const id = Number(transaccion[1]);
            const index = transacciones.findIndex(t => Number(t.id) === id);
            if (index < 0) return respuestaJson({ detail: 'Movimiento no encontrado.' }, 404);
            if (metodo === 'GET') return respuestaJson(transacciones[index]);
            if (metodo === 'PUT' || metodo === 'PATCH') {
                data.transacciones[index] = { ...transacciones[index], ...body, monto: Number(body.monto ?? transacciones[index].monto) };
                guardar(); return respuestaJson(data.transacciones[index]);
            }
            if (metodo === 'DELETE') {
                const [eliminada] = data.transacciones.splice(index, 1);
                guardar(); return respuestaJson(eliminada);
            }
        }
        if (path === '/api/metas/' || path === '/api/metas') {
            if (metodo === 'GET') return respuestaJson(metas);
            if (metodo === 'POST') {
                const nueva = {
                    ...body, id: data.nextId++, monto_objetivo: Number(body.monto_objetivo) || 0,
                    monto_actual: Number(body.monto_actual) || 0,
                    completada: Number(body.monto_actual) >= Number(body.monto_objetivo),
                };
                metas.push(nueva); guardar(); return respuestaJson(nueva, 201);
            }
        }
        const meta = path.match(/^\/api\/metas\/(\d+)$/);
        if (meta) {
            const id = Number(meta[1]);
            const index = metas.findIndex(m => Number(m.id) === id);
            if (index < 0) return respuestaJson({ detail: 'Meta no encontrada.' }, 404);
            if (metodo === 'PUT' || metodo === 'PATCH') {
                data.metas[index] = { ...metas[index], ...body };
                data.metas[index].monto_actual = Number(data.metas[index].monto_actual) || 0;
                data.metas[index].completada = data.metas[index].monto_actual >= Number(data.metas[index].monto_objetivo);
                guardar(); return respuestaJson(data.metas[index]);
            }
            if (metodo === 'DELETE') {
                const [eliminada] = data.metas.splice(index, 1);
                guardar(); return respuestaJson(eliminada);
            }
        }
        if (path === '/api/perfil/' || path === '/api/perfil') {
            if (metodo === 'GET') return respuestaJson({ ...data.perfil, tiene_foto_perfil: Boolean(data.foto), onboarding_completado: true });
            if (metodo === 'PUT' || metodo === 'PATCH') {
                data.perfil = { ...data.perfil, ...body };
                guardar(); return respuestaJson({ ...data.perfil, tiene_foto_perfil: Boolean(data.foto) });
            }
        }
        if (path === '/api/perfil/foto') {
            if (metodo === 'GET') {
                if (!data.foto) return respuestaJson({ detail: 'No hay foto de perfil.' }, 404);
                const response = await originalFetch(data.foto);
                return new Response(await response.blob(), { headers: { 'Content-Type': response.headers.get('Content-Type') || 'image/jpeg' } });
            }
            if (metodo === 'POST') {
                const archivo = init.body instanceof FormData ? init.body.get('archivo') : null;
                if (!archivo) return respuestaJson({ detail: 'Selecciona una imagen.' }, 400);
                data.foto = await new Promise((resolve, reject) => {
                    const lector = new FileReader();
                    lector.onload = () => resolve(lector.result);
                    lector.onerror = () => reject(lector.error);
                    lector.readAsDataURL(archivo);
                });
                guardar(); return respuestaJson({ mensaje: 'Foto guardada localmente.' });
            }
            if (metodo === 'DELETE') {
                data.foto = ''; guardar(); return respuestaJson({ mensaje: 'Foto eliminada.' });
            }
        }
        const calendario = path.match(/^\/api\/calendario\/(\d{4})\/(\d{1,2})$/);
        if (calendario && metodo === 'GET') {
            const anio = Number(calendario[1]), mes = Number(calendario[2]);
            const lista = transacciones.filter(t => {
                const fecha = new Date(`${t.fecha}T00:00:00`);
                return fecha.getFullYear() === anio && fecha.getMonth() + 1 === mes;
            });
            const ingresos = lista.filter(t => t.tipo === 'ingreso').reduce((s, t) => s + t.monto, 0);
            const gastos = lista.filter(t => t.tipo === 'gasto').reduce((s, t) => s + t.monto, 0);
            return respuestaJson({
                anio, mes, nombre_mes: new Intl.DateTimeFormat('es-CO', { month: 'long' }).format(new Date(anio, mes - 1, 1)),
                hay_transacciones: lista.length > 0, total_ingresos: ingresos, total_gastos: gastos,
                balance: ingresos - gastos, num_movimientos: lista.length,
                movimientos: lista.map(t => ({ ...t, icono: t.icono || '💸' })),
            });
        }
        const mesesDisponibles = path.match(/^\/api\/calendario\/disponibles\/(\d{4})$/);
        if (mesesDisponibles && metodo === 'GET') {
            const anio = Number(mesesDisponibles[1]);
            return respuestaJson(Array.from({ length: 12 }, (_, index) => {
                const mes = index + 1;
                const prefix = `${anio}-${String(mes).padStart(2, '0')}`;
                const total = transacciones.filter(t => (t.fecha || '').startsWith(prefix)).length;
                return {
                    mes, nombre_mes: new Intl.DateTimeFormat('es-CO', { month: 'long' }).format(new Date(anio, index, 1)),
                    hay_transacciones: total > 0, num_movimientos: total,
                };
            }));
        }
        if (path === '/api/transacciones/ubicaciones' && metodo === 'GET') {
            const tipo = new URLSearchParams(search).get('tipo');
            return respuestaJson(transacciones.filter(t => t.latitud != null && t.longitud != null && (!tipo || t.tipo === tipo)));
        }
        if (path.startsWith('/api/recomendaciones/')) return respuestaJson([]);
        if (path === '/api/transacciones/lugares-cercanos') return respuestaJson([]);
        if (path === '/api/exportar/pdf' || path === '/api/exportar/excel' || /^\/api\/calendario\/reporte\/\d{4}\/\d{1,2}/.test(path)) {
            if (!transacciones.length) return respuestaJson({ detail: 'No hay movimientos para exportar.' }, 404);
            const filas = [['Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto'], ...transacciones.map(t => [t.fecha, t.tipo, t.categoria, t.descripcion, t.monto])];
            const parametros = new URLSearchParams(search);
            const reporteMes = path.match(/^\/api\/calendario\/reporte\/(\d{4})\/(\d{1,2})$/);
            const mesLista = reporteMes
                ? transacciones.filter(t => (t.fecha || '').slice(0, 7) === `${reporteMes[1]}-${String(reporteMes[2]).padStart(2, '0')}`)
                : transacciones;
            if (!mesLista.length) return respuestaJson({ detail: 'No hay movimientos para exportar.' }, 404);
            const filasReporte = [['Fecha', 'Tipo', 'Categoría', 'Descripción', 'Monto'],
                ...mesLista.map(t => [t.fecha, t.tipo, t.categoria, t.descripcion, t.monto])];
            const esExcel = path.endsWith('/excel') || parametros.get('formato') === 'excel';
            const blob = esExcel ? csvBlob(filasReporte) : pdfBlob('Reporte financiero', filasReporte.slice(1).map(f => f.join(' | ')));
            return new Response(blob, { headers: { 'Content-Type': blob.type } });
        }
        if (path === '/api/simulaciones/exportar' && metodo === 'POST') {
            const filas = [['Capital inicial', 'Tasa anual', 'Plazo (meses)', 'Aporte mensual', 'Tipo'],
                [body.capital_inicial, body.tasa_retorno, body.plazo_meses, body.aporte_mensual, body.nombre_tipo]];
            return new Response(csvBlob(filas), { headers: { 'Content-Type': 'text/csv;charset=utf-8' } });
        }
        if (path === '/api/aprende' || path.startsWith('/api/aprende/')) return originalFetch(input, init);
        return respuestaJson({ detail: 'Esta función todavía no está disponible sin conexión a una cuenta.' }, 501);
    }

    window.FinanbotLocal = {
        get active() { return enModoInvitado(); },
        get token() { return this.active ? 'guest-local' : null; },
        clearMode() { localStorage.removeItem(GUEST_FLAG); },
        clearData() {
            this.clearMode();
            storageRemoveItem.call(localStorage, DATA_KEY);
            guestSettings.forEach(key => storageRemoveItem.call(localStorage, GUEST_SETTING_PREFIX + key));
            ['fb_inv_msgs', 'fb_inv_cool', 'fb_inv_chat'].forEach(key => storageRemoveItem.call(localStorage, key));
        },
    };

    window.fetch = function (input, init) {
        if (!window.FinanbotLocal.active) return originalFetch(input, init);
        const rawUrl = typeof input === 'string' ? input : input.url;
        const url = new URL(rawUrl, location.href);
        if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return originalFetch(input, init);
        if (url.pathname === '/api/chat/mensaje' || url.pathname.startsWith('/api/chat/') ||
            url.pathname.startsWith('/api/aprende/')) return originalFetch(input, init);
        return atenderLocal(url.pathname, init || (input instanceof Request ? input : {}), url.search);
    };

    if (window.FinanbotLocal.active) {
        document.addEventListener('DOMContentLoaded', () => {
            const banner = document.createElement('div');
            banner.className = 'local-guest-banner';
            banner.textContent = 'Modo invitado: tus datos se guardan solo en este navegador.';
            banner.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:12000;background:#17172f;color:#e5e7eb;border:1px solid #8B5CF6;border-radius:12px;padding:9px 13px;font:12px Segoe UI,sans-serif;box-shadow:0 6px 24px #0008';
            document.body.appendChild(banner);
        });
    }
})();
