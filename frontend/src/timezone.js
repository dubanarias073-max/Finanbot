const TIME_ZONE = 'America/Bogota'

export function todayIsoBogota() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]))
  return `${values.year}-${values.month}-${values.day}`
}

export function todayBogota() {
  const [year, month, day] = todayIsoBogota().split('-').map(Number)
  return new Date(year, month - 1, day, 12)
}
