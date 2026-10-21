(() => {
  const timeZone = 'America/Bogota';
  const dateFormatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });

  function partsFor(date = new Date()) {
    return Object.fromEntries(
      dateFormatter.formatToParts(date).map(({ type, value }) => [type, value]),
    );
  }

  function todayIso() {
    const { year, month, day } = partsFor();
    return `${year}-${month}-${day}`;
  }

  function today() {
    const [year, month, day] = todayIso().split('-').map(Number);
    return new Date(year, month - 1, day, 12);
  }

  function yesterday() {
    const date = today();
    date.setDate(date.getDate() - 1);
    return date;
  }

  function fromIsoDate(value) {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day, 12);
  }

  function todayLabel(options) {
    return today().toLocaleDateString('es-CO', options);
  }

  function currentTimeLabel(options = { hour: '2-digit', minute: '2-digit' }) {
    return new Intl.DateTimeFormat('es-CO', { ...options, timeZone }).format(new Date());
  }

  window.FinanbotTime = { todayIso, today, yesterday, fromIsoDate, todayLabel, currentTimeLabel };
})();
