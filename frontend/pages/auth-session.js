function cerrarSesion(event) {
    event?.preventDefault();
    const destino = event?.currentTarget?.href || 'index-legacy.html';

    window.FinanbotLocal?.clearMode();
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    window.top.location.href = destino;
}

async function cerrarSesionDispositivo(event) {
    event?.preventDefault();
    const destino = event?.currentTarget?.href || 'index-legacy.html';
    const modoInvitado = window.FinanbotLocal?.active;
    if (modoInvitado) {
        window.FinanbotLocal.clearData();
        window.top.location.href = destino;
        return;
    }

    const habiaSesion = Boolean(localStorage.getItem('token'));

    try {
        if (habiaSesion) {
            const respuesta = await fetch('/api/auth/logout', { method: 'POST' });
            if (!respuesta.ok) {
                throw new Error(`No se pudo borrar la cookie del dispositivo (${respuesta.status}).`);
            }
        }
    } catch (error) {
        console.error('Error cerrando la sesión del dispositivo:', error);
        alert('No se pudo confirmar el cierre de sesión en el servidor. Se cerrará la sesión local.');
    } finally {
        localStorage.clear();
        window.top.location.href = destino;
    }
}

async function cerrarSesionCompleto(event) {
    if (confirm('¿Cerrar sesión?')) {
        await cerrarSesionDispositivo(event);
    }
}
