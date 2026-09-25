import { useEffect, useRef, useState } from 'react'
import { CalendarReact, DashboardReact, ExportReact, FinanceReact, LearnReact, OnboardingReact, ProfileReact, RecommendationsReact, SimulationReact } from './ReactPages.jsx'

const API = '/api'
const SUGGESTIONS = ['¿Cómo organizo mis gastos?', 'Calcula el 20% de 500000', 'Quiero crear una meta de ahorro']

function textoSeguro(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;')
}

function renderMarkdown(value) {
  return textoSeguro(value).replace(/```([\s\S]*?)```/g, '<pre>$1</pre>').replace(/^### (.+)$/gm, '<h3>$1</h3>').replace(/^## (.+)$/gm, '<h2>$1</h2>').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>').replace(/`(.+?)`/g, '<code>$1</code>').replace(/\n/g, '<br />')
}

const routes = [
  ['Dashboard', '/', '⌂'], ['Finanzas', '/finanzas', '◈'], ['Chat IA', '/chat', '✦'],
  ['Calendario', '/calendario', '▣'], ['Recomendaciones', '/recomendaciones', '✧'],
  ['Simulador', '/simulador', '↗'], ['Aprende', '/aprende', '▤'], ['Perfil', '/perfil', '◉'],
  ['Exportar', '/exportar', '⇩'],
]

const legacyScreens = {
  '/': 'index.html',
  '/dashboard': 'pages/dashboard.html',
  '/login': 'pages/login.html',
  '/registro': 'pages/registro.html',
  '/onboarding': 'pages/onboarding.html',
  '/chat': 'pages/chat.html',
  '/finanzas': 'pages/finanzas.html',
  '/calendario': 'pages/calendario.html',
  '/recomendaciones': 'pages/recomendaciones.html',
  '/simulador': 'pages/simulador.html',
  '/aprende': 'pages/aprende.html',
  '/perfil': 'pages/perfil.html',
  '/exportar': 'pages/exportar.html',
}

function LegacyPage({ file }) {
  return <iframe className="legacy-screen" src={`/legacy/${file}`} title={`FinanBot ${file}`} />
}

function money(value) { return `$${Number(value || 0).toLocaleString('es-CO')}` }

function ReactShell({ title, subtitle, children, active }) {
  return <div className="react-shell"><aside className="app-sidebar"><div className="app-brand"><span><img src="/images/logo.png" alt="FinanBot" /></span><strong>FinanBot</strong></div><nav>{routes.map(([label, href, icon]) => <a className={active === href ? 'active' : ''} href={href} key={href}><i>{icon}</i>{label}</a>)}</nav><div className="app-sidebar-bottom"><a href="/login">⇥ Cerrar sesión</a><span><i /> API conectada</span></div></aside><main className="app-content"><header className="app-topbar"><div><p className="eyebrow">FinanBot · Finanzas personales</p><h1>{title}</h1><p className="page-subtitle">{subtitle}</p></div><span className="profile-pill">{JSON.parse(localStorage.getItem('usuario') || 'null')?.nombre || 'Invitado'} <b>●</b></span></header>{children}</main></div>
}

function LandingPage() { return <ReactShell title="Tu dinero, más claro." subtitle="Un centro inteligente para entender, organizar y hacer crecer tus finanzas." active="/"><div className="landing-hero"><div><span className="hero-chip">✦ Asistente financiero inteligente</span><h2>Decisiones pequeñas.<br /><em>Futuro más tranquilo.</em></h2><p>Registra tus movimientos, crea metas y conversa con FinanBot para avanzar con intención.</p><div className="page-actions"><a className="primary-action" href="/chat">Hablar con FinanBot →</a><a className="secondary-action" href="/finanzas">Ver mis finanzas</a></div></div><div className="landing-orbit"><div className="orbit-ring" /><span>💸</span><small>Tu balance<br />en un solo lugar</small></div></div><div className="metric-grid"><Metric value="01" label="Panel inteligente" /><Metric value="24/7" label="Asistencia financiera" /><Metric value="100%" label="Control personal" /></div></ReactShell> }
function Metric({ value, label }) { return <div className="metric"><strong>{value}</strong><span>{label}</span></div> }

function AuthPage({ register = false }) {
  const [form, setForm] = useState({ nombre: '', correo: '', contrasena: '' }); const [message, setMessage] = useState('')
  async function submit(event) { event.preventDefault(); const endpoint = register ? 'registro' : 'login'; const response = await fetch(`/api/auth/${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) }); const data = await response.json(); if (!response.ok) { setMessage(data.detail || 'No se pudo completar la solicitud'); return } if (!register) { localStorage.setItem('token', data.token); localStorage.setItem('usuario', JSON.stringify(data.usuario)); location.href = '/' } else { setMessage('Cuenta creada. Ya puedes iniciar sesión.'); } }
  return <div className="auth-screen"><div className="auth-card"><div className="auth-logo"><img src="/images/logo.png" alt="FinanBot" /></div><p className="eyebrow">FinanBot</p><h1>{register ? 'Crea tu cuenta' : 'Qué bueno verte.'}</h1><p className="muted">{register ? 'Empieza a tomar el control de tus finanzas.' : 'Ingresa para continuar con tu plan financiero.'}</p>{message && <div className="inline-alert">{message}</div>}<form onSubmit={submit}>{register && <label>Nombre completo<input required value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></label>}<label>Correo electrónico<input required type="email" value={form.correo} onChange={(e) => setForm({ ...form, correo: e.target.value })} /></label><label>Contraseña<input required type="password" value={form.contrasena} onChange={(e) => setForm({ ...form, contrasena: e.target.value })} /></label><button className="primary-action" type="submit">{register ? 'Crear cuenta →' : 'Iniciar sesión →'}</button></form><a className="auth-link" href={register ? '/login' : '/registro'}>{register ? 'Ya tengo una cuenta' : 'Crear una cuenta nueva'}</a></div></div>
}

function DashboardPage() { const [data, setData] = useState({ trans: [], metas: [], perfil: {} }); useEffect(() => { const h = { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }; Promise.all([fetch('/api/transacciones/', { headers: h }).then((r) => r.ok ? r.json() : []), fetch('/api/metas/', { headers: h }).then((r) => r.ok ? r.json() : []), fetch('/api/perfil/', { headers: h }).then((r) => r.ok ? r.json() : {})]).then(([trans, metas, perfil]) => setData({ trans, metas, perfil })).catch(() => {}) }, []); const ingresos = data.trans.filter((t) => t.tipo === 'ingreso').reduce((s, t) => s + Number(t.monto), 0); const gastos = data.trans.filter((t) => t.tipo === 'gasto').reduce((s, t) => s + Number(t.monto), 0); return <ReactShell title={`Hola, ${data.perfil?.nombre || 'bienvenido'} 👋`} subtitle="Este es el pulso de tus finanzas este mes." active="/"><div className="stat-grid"><StatCard label="Ingresos" value={money(ingresos)} tone="cyan" icon="↗" /><StatCard label="Gastos" value={money(gastos)} tone="pink" icon="↘" /><StatCard label="Balance" value={money(ingresos - gastos)} tone="green" icon="◒" /><StatCard label="Metas activas" value={data.metas.length} tone="yellow" icon="◎" /></div><div className="dashboard-grid"><section className="surface"><SectionTitle text="Accesos rápidos" /><div className="quick-grid"><a href="/finanzas">💸<span>Registrar movimiento</span></a><a href="/chat">🤖<span>Preguntar a FinanBot</span></a><a href="/simulador">📈<span>Simular inversión</span></a><a href="/aprende">📚<span>Aprender</span></a></div></section><section className="surface"><SectionTitle text="Últimos movimientos" /><div className="movement-list">{data.trans.slice(0, 5).map((item) => <div className="movement" key={item.id}><span>{item.tipo === 'gasto' ? '💸' : '💰'}</span><div><b>{item.categoria}</b><small>{item.descripcion || 'Sin descripción'}</small></div><strong className={item.tipo}>{money(item.monto)}</strong></div>)}{!data.trans.length && <Empty text="Aún no tienes movimientos registrados." />}</div></section></div></ReactShell> }
function StatCard({ label, value, tone, icon }) { return <div className={`stat-card ${tone}`}><span>{icon}</span><small>{label}</small><strong>{value}</strong></div> }
function SectionTitle({ text }) { return <div className="section-title"><h2>{text}</h2><span>•</span></div> }
function Empty({ text }) { return <div className="empty-state">◎<p>{text}</p></div> }

function FinancePage() { const [items, setItems] = useState([]); const [form, setForm] = useState({ tipo: 'gasto', monto: '', categoria: 'Alimentación', descripcion: '' }); const h = { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }; async function load() { const response = await fetch('/api/transacciones/', { headers: h }); if (response.ok) setItems(await response.json()) } useEffect(() => { load() }, []); async function save(e) { e.preventDefault(); const response = await fetch('/api/transacciones/', { method: 'POST', headers: { ...h, 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, monto: Number(form.monto), fecha: new Date().toISOString().slice(0, 10) }) }); if (response.ok) { setForm({ ...form, monto: '', descripcion: '' }); load() } } return <ReactShell title="Mis finanzas" subtitle="Registra y entiende cada movimiento." active="/finanzas"><div className="finance-layout"><section className="surface form-surface"><SectionTitle text="Nuevo movimiento" /><form onSubmit={save}><div className="segmented"><button type="button" className={form.tipo === 'gasto' ? 'selected gasto' : ''} onClick={() => setForm({ ...form, tipo: 'gasto' })}>💸 Gasto</button><button type="button" className={form.tipo === 'ingreso' ? 'selected ingreso' : ''} onClick={() => setForm({ ...form, tipo: 'ingreso' })}>💰 Ingreso</button></div><label>Monto<input required type="number" value={form.monto} onChange={(e) => setForm({ ...form, monto: e.target.value })} /></label><label>Categoría<select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>{['Alimentación', 'Transporte', 'Arriendo', 'Salud', 'Entretenimiento', 'Educación', 'Salario', 'Freelance', 'Otros gastos'].map((item) => <option key={item}>{item}</option>)}</select></label><label>Descripción<input value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} placeholder="Ej. Mercado del mes" /></label><button className="primary-action" type="submit">Guardar movimiento →</button></form></section><section className="surface"><SectionTitle text="Movimientos recientes" /><div className="movement-list">{items.slice(0, 12).map((item) => <div className="movement" key={item.id}><span>{item.tipo === 'gasto' ? '💸' : '💰'}</span><div><b>{item.categoria}</b><small>{item.descripcion || 'Sin descripción'} · {item.fecha}</small></div><strong className={item.tipo}>{money(item.monto)}</strong></div>)}{!items.length && <Empty text="Registra tu primer movimiento." />}</div></section></div></ReactShell> }

function CalendarPage() { return <ReactShell title="Calendario financiero" subtitle="Revisa el ritmo de tus movimientos por mes." active="/calendario"><div className="calendar-placeholder surface"><div className="calendar-icon">▦</div><h2>Tu calendario financiero</h2><p>La vista React está lista para conectarse al resumen mensual existente.</p><a className="primary-action" href="/finanzas">Ver movimientos →</a></div></ReactShell> }
function RecommendationsPage() { const [items, setItems] = useState([]); useEffect(() => { fetch('/api/recomendaciones/', { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } }).then((r) => r.ok ? r.json() : []).then(setItems).catch(() => {}) }, []); return <ReactShell title="Recomendaciones" subtitle="Ideas prácticas para mejorar tu salud financiera." active="/recomendaciones"><div className="recommendation-grid">{(items.length ? items : [{ titulo: 'Registra tus movimientos', descripcion: 'Con una foto clara de tus ingresos y gastos, FinanBot puede ayudarte a tomar mejores decisiones.', tipo: 'info', emoji: '✦' }]).map((item, index) => <article className="recommendation" key={item.id || index}><span>{item.emoji || '✦'}</span><small>{item.tipo || 'INFO'}</small><h2>{item.titulo || item.nombre}</h2><p>{item.descripcion || item.mensaje}</p><a href="/chat">Preguntar a FinanBot →</a></article>)}</div></ReactShell> }
function SimulationPage() { const [form, setForm] = useState({ capital: 1000000, tasa: 10, meses: 12 }); const [result, setResult] = useState(null); function calculate(e) { e.preventDefault(); const total = Number(form.capital) * (1 + Number(form.tasa) / 100) ** (Number(form.meses) / 12); setResult(total) } return <ReactShell title="Simulador" subtitle="Explora escenarios antes de tomar una decisión." active="/simulador"><div className="simulator-layout"><form className="surface simulation-form" onSubmit={calculate}><SectionTitle text="Parámetros" />{[['capital', 'Capital inicial'], ['tasa', 'Tasa anual (%)'], ['meses', 'Plazo (meses)']].map(([key, label]) => <label key={key}>{label}<input type="number" value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} /></label>)}<button className="primary-action" type="submit">Calcular escenario →</button></form><section className="surface simulation-result">{result ? <><small>VALOR PROYECTADO</small><strong>{money(result)}</strong><p>Ganancia estimada: {money(result - Number(form.capital))}</p></> : <Empty text="Completa los parámetros para ver el resultado." />}</section></div></ReactShell> }
function LearnPage() { const [query, setQuery] = useState(''); const [results, setResults] = useState([]); async function search(e) { e.preventDefault(); const response = await fetch(`/api/aprende/buscar?q=${encodeURIComponent(query)}`); if (response.ok) setResults(await response.json()) } return <ReactShell title="Aprende" subtitle="Conceptos financieros explicados de forma clara." active="/aprende"><form className="learn-search" onSubmit={search}><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Busca CDT, ahorro, deudas..." /><button className="primary-action">Buscar →</button></form><div className="article-grid">{results.length ? results.map((item) => <article className="article" key={item.id}><span>{item.emoji || '📚'}</span><small>{item.categoria}</small><h2>{item.titulo}</h2><p>{item.resumen || item.descripcion}</p></article>) : ['Cómo crear un presupuesto', 'Interés compuesto', 'Fondo de emergencia'].map((title) => <article className="article" key={title}><span>📚</span><small>Finanzas personales</small><h2>{title}</h2><p>Busca este tema para descubrir explicaciones, ejemplos y recomendaciones.</p></article>)}</div></ReactShell> }
function ProfilePage() { const [profile, setProfile] = useState({}); const h = { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }; useEffect(() => { fetch('/api/perfil/', { headers: h }).then((r) => r.ok ? r.json() : {}).then(setProfile).catch(() => {}) }, []); return <ReactShell title="Mi perfil" subtitle="Tu información y preferencias financieras." active="/perfil"><section className="profile-hero surface"><div className="profile-avatar">{(profile.nombre || 'U')[0]}</div><div><p className="eyebrow">Perfil activo</p><h2>{profile.nombre || 'Usuario'}</h2><p className="muted">{profile.correo || 'Completa tu información desde onboarding.'}</p></div></section><div className="profile-grid"><Info label="Ingreso mensual" value={money(profile.ingreso_mensual)} /><Info label="Meta de ahorro" value={money(profile.meta_ahorro)} /><Info label="Rol" value={profile.rol || 'Sin definir'} /></div></ReactShell> }
function Info({ label, value }) { return <div className="surface info-card"><small>{label}</small><strong>{value}</strong></div> }
function ExportPage() { const token = localStorage.getItem('token'); async function download(type) { const response = await fetch(`/api/exportar/${type}`, { headers: { Authorization: `Bearer ${token || ''}` } }); if (!response.ok) return; const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `finanbot-reporte.${type === 'excel' ? 'xlsx' : 'pdf'}`; link.click(); URL.revokeObjectURL(url) } return <ReactShell title="Exportar reportes" subtitle="Lleva tus datos contigo cuando los necesites." active="/exportar"><div className="export-grid"><button className="export-card excel" onClick={() => download('excel')}><span>▦</span><h2>Reporte Excel</h2><p>Analiza tus movimientos en una hoja de cálculo.</p><strong>Descargar →</strong></button><button className="export-card pdf" onClick={() => download('pdf')}><span>▤</span><h2>Reporte PDF</h2><p>Guarda un resumen limpio y fácil de compartir.</p><strong>Descargar →</strong></button></div></ReactShell> }

function OnboardingPage() { const [role, setRole] = useState(''); return <div className="auth-screen"><div className="auth-card onboarding"><div className="auth-logo">✦</div><p className="eyebrow">Primer paso</p><h1>Construyamos tu plan.</h1><p className="muted">Elige el perfil que mejor describe tu día a día.</p><div className="role-grid">{['Estudiante', 'Empleado', 'Independiente', 'Emprendedor'].map((item) => <button className={role === item ? 'selected' : ''} onClick={() => setRole(item)} key={item}>{item}</button>)}</div><a className={`primary-action ${!role ? 'disabled' : ''}`} href={role ? '/': undefined}>Continuar →</a></div></div> }

function SimpleRoute() {
  const path = location.pathname.replace(/\.html$/, '')
  const normalizedPath = path.startsWith('/pages/') ? path.replace('/pages', '') : path
  const file = legacyScreens[normalizedPath]
  if (file) return <LegacyPage file={file} />
  return <LegacyPage file="index.html" />
}

function ChatPage() {
  const token = localStorage.getItem('token')
  const storedUser = JSON.parse(localStorage.getItem('usuario') || 'null')
  const [user] = useState(storedUser)
  const [conversations, setConversations] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [conversationTitle, setConversationTitle] = useState('Selecciona o crea una conversación')
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)
  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  useEffect(() => {
    if (!token) return
    fetch(`${API}/chat-historial/conversaciones`, { headers }).then((response) => response.ok ? response.json() : []).then(setConversations).catch(() => setError('No pude cargar tu historial.'))
  }, [token])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isTyping])

  async function selectConversation(conversation) {
    setConversationId(conversation.id); setConversationTitle(`💬 ${conversation.titulo || 'Conversación'}`); setError('')
    try {
      const response = await fetch(`${API}/chat-historial/mensajes/${conversation.id}`, { headers })
      if (!response.ok) throw new Error()
      const history = await response.json()
      setMessages(history.flatMap((item) => [{ role: 'user', text: item.mensaje, time: item.hora }, { role: 'bot', text: item.respuesta, time: item.hora }]))
    } catch { setError('No pude abrir esta conversación.') }
  }

  async function newConversation() {
    if (!token) { setConversationId('guest'); setConversationTitle('💬 Modo invitado'); setMessages([{ role: 'bot', text: '👋 ¡Hola! Soy **FinanBot**, tu asistente financiero. ¿En qué te puedo ayudar?' }]); return }
    const response = await fetch(`${API}/chat-historial/conversaciones`, { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ titulo: 'Nueva conversación' }) })
    if (!response.ok) return
    const conversation = await response.json()
    setConversationId(conversation.id); setConversationTitle('💬 Nueva conversación'); setMessages([])
  }

  async function sendMessage(event, suggestedText = null) {
    event?.preventDefault()
    const text = (suggestedText ?? draft).trim()
    if (!text || isTyping) return
    let activeId = conversationId
    if (!activeId && token) {
      const conversationResponse = await fetch(`${API}/chat-historial/conversaciones`, { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ titulo: 'Nueva conversación' }) })
      if (!conversationResponse.ok) return
      const conversation = await conversationResponse.json()
      activeId = conversation.id
      setConversationId(activeId)
      setConversationTitle('💬 Nueva conversación')
    }
    setDraft(''); setError(''); setMessages((current) => [...current, { role: 'user', text }]); setIsTyping(true)
    try {
      const body = { mensaje: text }
      if (token && activeId && activeId !== 'guest') body.conversacion_id = activeId
      const response = await fetch(`${API}/chat/mensaje`, { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'No se pudo enviar el mensaje')
      setConversationId(data.conversacion_id || activeId); setMessages((current) => [...current, { role: 'bot', text: data.respuesta, actions: data.acciones || [] }])
      if (token) { const historyResponse = await fetch(`${API}/chat-historial/conversaciones`, { headers }); if (historyResponse.ok) setConversations(await historyResponse.json()) }
    } catch (sendError) { setError(sendError.message || 'No pude conectar con el servidor.') } finally { setIsTyping(false) }
  }

  return (
    <div className="chat-app">
      <aside className="chat-sidebar">
        <div className="brand-lockup"><div className="brand-mark"><img src="/images/logo.png" alt="FinanBot" /></div><div><strong>FinanBot</strong><span>Asistente financiero</span></div></div>
        <button className="new-chat" onClick={newConversation}>＋ Nueva conversación</button>
        <div className="history-heading">Historial</div>
        <div className="conversation-list">
          {!token && <div className="empty-history">Inicia sesión para guardar tus conversaciones.</div>}
          {token && !conversations.length && <div className="empty-history">Aún no tienes conversaciones.</div>}
          {conversations.map((conversation) => <button className={`conversation ${conversation.id === conversationId ? 'active' : ''}`} key={conversation.id} onClick={() => selectConversation(conversation)}><span>💬</span><span><strong>{conversation.titulo || 'Conversación'}</strong><small>{conversation.ultimo_mensaje || conversation.fecha}</small></span></button>)}
        </div>
        <div className="sidebar-footer"><span className="back-link">FinanBot React</span><span className="online"><i /> API conectada</span></div>
      </aside>
      <section className="chat-main">
        <header className="chat-header"><div className="mobile-brand"><span>🤖</span> FinanBot</div><div className="conversation-name">{conversationTitle}</div><div className="user-pill">{user ? user.nombre : 'Invitado'} <span>{user ? '●' : '○'}</span></div></header>
        <div className="ai-notice">✦ Respuestas inteligentes para tomar mejores decisiones con tu dinero.</div>
        <div className="messages" aria-live="polite">
          {!messages.length && <div className="welcome-chat"><div className="welcome-avatar">🤖</div><p className="kicker">Tu copiloto financiero</p><h1>¿Qué quieres resolver hoy?</h1><p>Pregúntame por tus gastos, metas, inversiones o cualquier concepto financiero.</p><div className="suggestion-grid">{SUGGESTIONS.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(null, suggestion)}>{suggestion}<span>→</span></button>)}</div></div>}
          {messages.map((message, index) => <article className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="message-avatar">{message.role === 'bot' ? '🤖' : (user?.nombre?.[0] || 'T')}</div><div className="message-content"><span className="message-name">{message.role === 'bot' ? 'FinanBot' : (user?.nombre || 'Tú')}</span><div className="bubble" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.text) }} />{message.actions?.length > 0 && <div className="message-actions">{message.actions.map((action, actionIndex) => action.link ? <a href={action.link} key={actionIndex}>{action.texto || action.label}</a> : <button onClick={() => sendMessage(null, action.texto || action.label)} key={actionIndex}>{action.texto || action.label}</button>)}</div>}</div></article>)}
          {isTyping && <div className="typing"><div className="message-avatar">🤖</div><div className="typing-bubble"><i /><i /><i /></div></div>}
          <div ref={bottomRef} />
        </div>
        {error && <div className="chat-error">⚠ {error}</div>}
        <form className="composer" onSubmit={sendMessage}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) sendMessage(event) }} placeholder="Escribe tu pregunta financiera..." rows="1" /><button className="send-button" aria-label="Enviar mensaje" disabled={!draft.trim() || isTyping}>➤</button></form>
        <small className="composer-hint">FinanBot puede cometer errores. Verifica la información importante.</small>
      </section>
    </div>
  )
}

export default SimpleRoute
