// ════════════════════════════════════════════════════════════
//  regla_personalizable.js — FinanBot
//  Incluir con <script src="regla_personalizable.js"></script>
//  en recomendaciones.html Y perfil.html (antes de </body>)
// ════════════════════════════════════════════════════════════

const REGLA_KEY     = 'finanbot_regla_dist';
const REGLA_DEFAULT = { nec: 50, des: 30, aho: 20, nombre: 'Estándar 50/30/20' };

const PRESETS = [
    { nec: 50, des: 30, aho: 20, nombre: 'Estándar 50/30/20'  },
    { nec: 60, des: 20, aho: 20, nombre: 'Ahorradora 60/20/20'},
    { nec: 40, des: 20, aho: 40, nombre: 'Inversora 40/20/40' },
    { nec: 70, des: 20, aho: 10, nombre: 'Conservadora 70/20/10'},
    { nec: 50, des: 10, aho: 40, nombre: 'Agresiva 50/10/40'  },
];

let _reglaPanel = false;

// ── Leer / guardar ──────────────────────────────────────────
function getRegla() {
    try {
        return Object.assign({}, REGLA_DEFAULT,
            JSON.parse(localStorage.getItem(REGLA_KEY) || '{}'));
    } catch { return { ...REGLA_DEFAULT }; }
}
function setRegla(r) {
    localStorage.setItem(REGLA_KEY, JSON.stringify(r));
}

// ── Toggle panel ────────────────────────────────────────────
function toggleReglaPanel() {
    _reglaPanel = !_reglaPanel;
    const panel = document.getElementById('reglaCustomPanel');
    if (!panel) return;
    panel.classList.toggle('visible', _reglaPanel);
    if (_reglaPanel) _iniciarSliders();
}

function _iniciarSliders() {
    const r = getRegla();
    _setSlider('slNec', r.nec);
    _setSlider('slDes', r.des);
    _setSlider('slAho', r.aho);
    const rn = document.getElementById('rNombre');
    if (rn) rn.value = r.nombre;
    _actualizarSliderUI();
    _marcarPreset(r);
}

function _setSlider(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
}

// ── Slider input ────────────────────────────────────────────
function onSlider(campo) {
    let nec = +document.getElementById('slNec').value;
    let des = +document.getElementById('slDes').value;
    let aho = +document.getElementById('slAho').value;
    const suma = nec + des + aho;

    if (suma > 100) {
        const exceso = suma - 100;
        if (campo === 'nec') {
            const resto = des + aho;
            if (resto > 0) {
                des = Math.max(0, des - Math.round(exceso * des / resto));
                aho = Math.max(0, 100 - nec - des);
                document.getElementById('slDes').value = des;
                document.getElementById('slAho').value = aho;
            }
        } else if (campo === 'des') {
            const resto = nec + aho;
            if (resto > 0) {
                nec = Math.max(0, nec - Math.round(exceso * nec / resto));
                aho = Math.max(0, 100 - nec - des);
                document.getElementById('slNec').value = nec;
                document.getElementById('slAho').value = aho;
            }
        } else {
            const resto = nec + des;
            if (resto > 0) {
                nec = Math.max(0, nec - Math.round(exceso * nec / resto));
                des = Math.max(0, 100 - nec - aho);
                document.getElementById('slNec').value = nec;
                document.getElementById('slDes').value = des;
            }
        }
    }
    _actualizarSliderUI();
}

function _actualizarSliderUI() {
    const nec = +document.getElementById('slNec').value;
    const des = +document.getElementById('slDes').value;
    const aho = +document.getElementById('slAho').value;
    const suma = nec + des + aho;

    _setText('pNec', nec + '%');
    _setText('pDes', des + '%');
    _setText('pAho', aho + '%');

    const sumaEl = document.getElementById('sumaTotal');
    if (sumaEl) {
        sumaEl.textContent = suma + '%';
        sumaEl.className = 'suma-val ' + (suma === 100 ? 'ok' : 'err');
    }

    const btn = document.getElementById('btnGuardarRegla');
    if (btn) btn.disabled = suma !== 100;

    // Preview barra en el panel
    _setBarWidth('previewBarNec', nec);
    _setBarWidth('previewBarDes', des);
    _setBarWidth('previewBarAho', aho);
}

// ── Presets ─────────────────────────────────────────────────
function aplicarPreset(idx) {
    const p = PRESETS[idx];
    if (!p) return;
    document.getElementById('slNec').value = p.nec;
    document.getElementById('slDes').value = p.des;
    document.getElementById('slAho').value = p.aho;
    const rn = document.getElementById('rNombre');
    if (rn) rn.value = p.nombre;
    _actualizarSliderUI();
    _marcarPreset(p);
}

function _marcarPreset(r) {
    document.querySelectorAll('.preset-btn').forEach((btn, i) => {
        const p = PRESETS[i];
        btn.classList.toggle('activo', p && p.nec === r.nec && p.des === r.des && p.aho === r.aho);
    });
}

// ── Guardar ─────────────────────────────────────────────────
function guardarReglaPersonalizada() {
    const nec = +document.getElementById('slNec').value;
    const des = +document.getElementById('slDes').value;
    const aho = +document.getElementById('slAho').value;
    if (nec + des + aho !== 100) return;
    const nombre = (document.getElementById('rNombre')?.value.trim()) || `${nec}/${des}/${aho}`;
    const r = { nec, des, aho, nombre };
    setRegla(r);
    actualizarReglaUI(r);
    if (typeof toast === 'function') toast('✅', `Regla "${nombre}" guardada`);
    toggleReglaPanel();
}

function resetRegla() {
    setRegla({ ...REGLA_DEFAULT });
    _iniciarSliders();
    if (typeof toast === 'function') toast('🔄', 'Regla restaurada al 50/30/20');
}

// ── Actualizar UI de la sección regla ───────────────────────
function actualizarReglaUI(r, ingreso) {
    if (!r) r = getRegla();
    const ing = ingreso
        || (typeof datosFinancieros !== 'undefined' ? datosFinancieros.ingMensual : 0)
        || parseFloat(document.getElementById('ingresoMensual')?.value || 0);

    _setText('reglaNombreBadge', r.nombre);
    _setText('reglaPctNec', r.nec + '%');
    _setText('reglaPctDes', r.des + '%');
    _setText('reglaPctAho', r.aho + '%');

    if (ing > 0) {
        _setText('reglaMnto50', '$' + Math.round(ing * r.nec / 100).toLocaleString('es-CO'));
        _setText('reglaMnto30', '$' + Math.round(ing * r.des / 100).toLocaleString('es-CO'));
        _setText('reglaMnto20', '$' + Math.round(ing * r.aho / 100).toLocaleString('es-CO'));
    }

    _setBarWidth('barNec', r.nec);
    _setBarWidth('barDes', r.des);
    _setBarWidth('barAho', r.aho);

    const lNec = document.getElementById('lblBarNec');
    const lDes = document.getElementById('lblBarDes');
    const lAho = document.getElementById('lblBarAho');
    if (lNec) { lNec.textContent = r.nec + '% Nec.'; lDes.textContent = r.des + '% Des.'; lAho.textContent = r.aho + '% Aho.'; }
}

// ── Helpers ─────────────────────────────────────────────────
function _setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function _setBarWidth(id, pct) { const el = document.getElementById(id); if (el) el.style.width = pct + '%'; }