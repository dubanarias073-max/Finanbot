/* FinanBot - registro de la PWA y botón "Instalar app" */
(function () {
  'use strict';

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/legacy/pages/sw.js', { scope: '/legacy/pages/' }).catch(function () {});
    });
  }

  if (window.self !== window.top) return; // dentro de un iframe: sin barra de instalar

  var standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  if (standalone) return;

  var deferred = null;
  var dismissedKey = 'finanbot_pwa_dismissed';
  function dismissed() { try { return localStorage.getItem(dismissedKey) === '1'; } catch (e) { return false; } }
  function remember() { try { localStorage.setItem(dismissedKey, '1'); } catch (e) {} }

  function makeBar(text, actionLabel, onAction) {
    if (dismissed() || document.getElementById('finanbot-install')) return;
    var bar = document.createElement('div');
    bar.id = 'finanbot-install';
    bar.style.cssText = 'position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:99999;' +
      'display:flex;align-items:center;gap:12px;max-width:calc(100vw - 32px);padding:10px 14px;border-radius:14px;' +
      'background:#11112B;color:#fff;border:1px solid #5EEAD4;box-shadow:0 8px 30px rgba(0,0,0,.45);' +
      'font:600 14px "DM Sans","Segoe UI",sans-serif';
    var span = document.createElement('span');
    span.textContent = text;
    bar.appendChild(span);
    if (actionLabel) {
      var btn = document.createElement('button');
      btn.textContent = actionLabel;
      btn.style.cssText = 'border:0;border-radius:10px;padding:8px 14px;background:#5EEAD4;color:#0B0B22;font:700 14px inherit;cursor:pointer';
      btn.onclick = function () { onAction(bar); };
      bar.appendChild(btn);
    }
    var close = document.createElement('button');
    close.setAttribute('aria-label', 'Cerrar');
    close.textContent = '×';
    close.style.cssText = 'border:0;background:transparent;color:#9ca3af;font-size:20px;line-height:1;cursor:pointer';
    close.onclick = function () { remember(); bar.remove(); };
    bar.appendChild(close);
    document.body.appendChild(bar);
  }

  // Android / Windows / macOS / Linux (Chrome, Edge)
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
    makeBar('Instala FinanBot como app', 'Instalar', function (bar) {
      deferred.prompt();
      deferred.userChoice.finally(function () { deferred = null; bar.remove(); });
    });
  });

  window.addEventListener('appinstalled', function () {
    var b = document.getElementById('finanbot-install');
    if (b) b.remove();
  });

  // iPhone / iPad (Safari no dispara beforeinstallprompt)
  var ua = navigator.userAgent;
  var isIOS = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isSafari = /safari/i.test(ua) && !/crios|fxios|edgios/i.test(ua);
  if (isIOS && isSafari) {
    window.addEventListener('load', function () {
      setTimeout(function () {
        makeBar('Para instalar: toca Compartir y luego "Añadir a pantalla de inicio"', null, null);
      }, 1500);
    });
  }
})();
