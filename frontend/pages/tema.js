// frontend/pages/tema.js

const TEMAS = {
    oscuro: {
        '--bg-body': 'radial-gradient(ellipse at top, #1a1a4e 0%, #0f0f2d 50%, #000010 100%)',
        '--color-texto': '#ffffff',
        '--sidebar-bg': 'rgba(255,255,255,0.03)',
        '--sidebar-border': 'rgba(168,85,247,0.2)',
        '--card-bg': 'rgba(255,255,255,0.04)',
        '--card-border': 'rgba(168,85,247,0.15)',
        '--label-color': '#c4b5fd',
        '--nav-active-bg': 'rgba(168,85,247,0.08)',
    },
    azul: {
        '--bg-body': 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #1e40af 100%)',
        '--color-texto': '#e0f2fe',
        '--sidebar-bg': 'rgba(15,23,42,0.85)',
        '--sidebar-border': 'rgba(96,165,250,0.25)',
        '--card-bg': 'rgba(30,58,95,0.65)',
        '--card-border': 'rgba(96,165,250,0.2)',
        '--label-color': '#93c5fd',
        '--nav-active-bg': 'rgba(96,165,250,0.12)',
    }
};

function aplicarTemaGlobal(tema) {
    const vars = TEMAS[tema] || TEMAS['oscuro'];
    const root = document.documentElement;

    // 1. Limpiamos estilos previos que JS pudo haber inyectado por error
    document.body.style.background = "";
    document.body.style.color = "";

    // 2. Aplicamos las variables al root
    Object.entries(vars).forEach(([prop, val]) => {
        root.style.setProperty(prop, val);
    });

    // 3. Agregamos un atributo al HTML para separar estilos en CSS si fuera necesario
    root.setAttribute('data-theme', tema);

    localStorage.setItem('finanbot_tema', tema);
}

// Ejecución inmediata
(function() {
    const t = localStorage.getItem('finanbot_tema') || 'oscuro';
    aplicarTemaGlobal(t);
})();
