/* ==========================================================================
   PRECOST — Respaldo y restauración completa de los datos del usuario (S-005)
   MISIÓN VII · Overlay aditivo — no modifica el núcleo ni a otros overlays.

   Paridad SIECONS 11 (manual pág. 14: «copia de seguridad/duplicado de la
   aplicación»), mejorada: exportación PORTABLE a archivo JSON con TODAS las
   claves p3pro.* del navegador (presupuestos, plantillas, casos importados,
   historial de la calculadora, configuración y tema) y restauración segura
   desde ese archivo con validación estricta — nada se escribe si el archivo
   no pasa TODA la validación.

   Características:
   - 100 % cliente: funciona sin servidor (versión web estática de GitHub
     Pages y ejecución local por igual).
   - Modo reemplazo explícito con confirmación: restaurar devuelve el
     navegador exactamente al estado del respaldo (predecible, como la
     salvaguarda de SIECONS).
   - Validación: app PRECOST, formato 1, sección datos objeto, todas las
     claves con prefijo p3pro. y valores de texto; rechazo limpio de
     archivos ajenos o manipulados, sin escrituras parciales.
   - Atajo de teclado Alt+B (junto al Alt+C de la calculadora).
   - Nota de privacidad: si el usuario configuró una clave de API para el
     copiloto, queda incluida en el archivo (se advierte en el panel).

   Gancho de pruebas: window.__pcodRespaldoAPI {generar, validar, aplicar,
   descargar, claves, abrir} — usado por scripts/validar_vii_navegador.sh. */
(function () {
  "use strict";
  if (window.__pcodRespaldo) return;               // idempotente
  window.__pcodRespaldo = true;

  var PREFIJO = "p3pro.";
  var FORMATO = 1;

  /* ------------------------------------------------------------------ estilos */
  var CSS = [
    ".pcod4-fab{position:fixed;left:16px;bottom:16px;z-index:9000;display:inline-flex;gap:7px;",
    "align-items:center;border:1px solid var(--border,#c9cedb);border-radius:22px;padding:8px 15px;",
    "background:var(--primary,#1a5fb4);color:#fff;font-size:13px;cursor:pointer;",
    "box-shadow:0 3px 10px rgba(0,0,0,.18);font-family:system-ui,sans-serif}",
    ".pcod4-fab:hover{filter:brightness(1.08)}",
    ".pcod4-mask{position:fixed;inset:0;background:rgba(15,20,30,.45);z-index:9005;display:none;",
    "align-items:flex-start;justify-content:center;overflow:auto;padding:26px 10px}",
    ".pcod4-mask.pcod4-open{display:flex}",
    ".pcod4-win{background:var(--bg-card,#fff);color:inherit;border:1px solid var(--border,#d8dce6);",
    "border-radius:14px;max-width:640px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.28);padding:18px 20px;",
    "font-family:system-ui,sans-serif}",
    ".pcod4-win h2{margin:0;font-size:var(--fs-l,17px);display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}",
    ".pcod4-sub{color:var(--text-muted,#667);font-size:12px;margin:2px 0 12px}",
    ".pcod4-x{margin-left:auto;background:none;border:none;font-size:16px;cursor:pointer;color:inherit}",
    ".pcod4-estado{background:rgba(26,95,180,.07);border:1px solid var(--border-soft,#eceff4);border-radius:8px;",
    "padding:9px 12px;font-size:13px;margin:6px 0 12px;line-height:1.55}",
    ".pcod4-estado b{font-variant-numeric:tabular-nums}",
    ".pcod4-btn{min-height:36px;padding:6px 14px;border:1px solid var(--border,#c9cedb);border-radius:8px;",
    "background:var(--bg,#fff);color:inherit;font-size:13px;cursor:pointer}",
    ".pcod4-btn:hover{background:rgba(26,95,180,.07)}",
    ".pcod4-btn.pcod4-prim{background:var(--primary,#1a5fb4);color:#fff;border-color:var(--primary,#1a5fb4)}",
    ".pcod4-btn.pcod4-prim:hover{filter:brightness(1.08);background:var(--primary,#1a5fb4)}",
    ".pcod4-fila{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}",
    ".pcod4-nota{font-size:12px;color:var(--text-muted,#667);line-height:1.6;margin-top:12px;",
    "border-top:1px dashed var(--border-soft,#eceff4);padding-top:10px}",
    ".pcod4-nota code{background:rgba(26,95,180,.08);border-radius:4px;padding:0 4px}",
    ".pcod4-err{color:#b3342c;font-size:13px;margin:8px 0;display:none}",
    ".pcod4-ok{color:#20723f;font-size:13px;margin:8px 0;display:none}"
  ].join("");
  var st = document.createElement("style");
  st.id = "pcod4-styles";
  st.textContent = CSS;
  document.head.appendChild(st);

  /* --------------------------------------------------------------- utilidades */
  function $(id) { return document.getElementById(id); }

  function clavesP3() {
    var out = [];
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k && k.indexOf(PREFIJO) === 0) out.push(k);
    }
    return out.sort();
  }
  function contar(valor, silencioso) {
    try {
      var v = JSON.parse(valor);
      if (Array.isArray(v)) return v.length;
      if (v && typeof v === "object") return Object.keys(v).length;
      return silencioso ? 0 : 1;
    } catch (e) { return silencioso ? 0 : 1; }
  }

  /* ------------------------------------------------------------- exportación */
  function generarRespaldo() {
    var claves = clavesP3();
    if (!claves.length) return null;            /* honesto: nada que respaldar */
    var datos = {};
    claves.forEach(function (k) { datos[k] = localStorage.getItem(k); });
    return {
      app: "PRECOST",
      formato: FORMATO,
      fecha: new Date().toISOString(),
      claves: claves.length,
      datos: datos
    };
  }

  function descargarRespaldo() {
    var r = generarRespaldo();
    if (!r) {
      alert("Todavía no hay datos de PRECOST guardados en este navegador.\n" +
            "Cree o importe un presupuesto antes de generar un respaldo.");
      return null;
    }
    function s(n) { return (n < 10 ? "0" : "") + n; }
    var d = new Date();
    var nombre = "precost-respaldo-" + d.getFullYear() + s(d.getMonth() + 1) + s(d.getDate()) +
                 "-" + s(d.getHours()) + s(d.getMinutes()) + ".json";
    var blob = new Blob([JSON.stringify(r, null, 1)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
    return nombre;
  }

  /* ------------------------------------------------------------ restauración */
  /* Devuelve null si el respaldo es VÁLIDO; si no, el motivo del rechazo.
     Nada se escribe hasta que la validación completa pasa. */
  function validarRespaldo(obj) {
    if (!obj || typeof obj !== "object" || Array.isArray(obj))
      return "el archivo no contiene un objeto de respaldo";
    if (obj.app !== "PRECOST") return "el archivo no es un respaldo de PRECOST";
    if (obj.formato !== FORMATO)
      return "formato no soportado (esperado " + FORMATO + ", encontrado " + obj.formato + ")";
    if (!obj.datos || typeof obj.datos !== "object" || Array.isArray(obj.datos))
      return "falta la sección de datos";
    var claves = Object.keys(obj.datos);
    if (!claves.length) return "el respaldo está vacío";
    for (var i = 0; i < claves.length; i++) {
      var k = claves[i];
      if (k.indexOf(PREFIJO) !== 0) return "clave no permitida: " + k;
      if (typeof obj.datos[k] !== "string") return "valor inválido en " + k + " (se esperaba texto)";
      if (obj.datos[k].length > 8 * 1024 * 1024) return "valor sospechosamente grande en " + k;
    }
    return null;
  }

  /* Modo reemplazo: borra las claves p3pro.* actuales y escribe las del
     respaldo. Solo se llama tras confirmación explícita del usuario (o desde
     las pruebas, que restauran el estado original al terminar). */
  function aplicarRespaldo(obj) {
    var err = validarRespaldo(obj);
    if (err) return { ok: false, error: err };
    clavesP3().forEach(function (k) { localStorage.removeItem(k); });
    Object.keys(obj.datos).forEach(function (k) { localStorage.setItem(k, obj.datos[k]); });
    return { ok: true, claves: Object.keys(obj.datos).length };
  }

  function restaurarDesdeArchivo(file) {
    var fr = new FileReader();
    fr.onerror = function () { alert("No se pudo leer el archivo."); };
    fr.onload = function () {
      var obj = null;
      try { obj = JSON.parse(String(fr.result)); }
      catch (e) { alert("Respaldo rechazado — el archivo no es JSON válido."); return; }
      var err = validarRespaldo(obj);
      if (err) { alert("Respaldo rechazado — " + err + ".\nNo se modificó ningún dato."); return; }
      var nPresup = contar(obj.datos["p3pro.budgets"], true);
      var actuales = clavesP3().length;
      var msg = "Restaurar el respaldo del " + new Date(obj.fecha || Date.now()).toLocaleString("es") + "\n\n" +
                "Se REEMPLAZARÁN los datos actuales de este navegador (" + actuales + " claves p3pro.*) " +
                "por los del archivo (" + Object.keys(obj.datos).length + " claves, " + nPresup + " presupuestos).\n" +
                "Esta acción no se puede deshacer. ¿Continuar?";
      if (!confirm(msg)) return;
      var r = aplicarRespaldo(obj);
      if (r.ok) {
        alert("Respaldo restaurado (" + r.claves + " claves). La página se recargará para aplicar los cambios.");
        location.reload();
      } else {
        alert("Error al restaurar — " + r.error);
      }
    };
    fr.readAsText(file);
  }

  /* -------------------------------------------------------------------- panel */
  function refrescarEstado() {
    var el = $("pcod4-estado");
    if (!el) return;
    var claves = clavesP3();
    var nPresup = contar(localStorage.getItem("p3pro.budgets"), true);
    var nPlant = contar(localStorage.getItem("p3pro.userTemplates"), true);
    var tieneClaveIA = !!localStorage.getItem("p3pro.copilotKey");
    el.innerHTML = "En este navegador hay <b>" + claves.length + "</b> claves de PRECOST: " +
      "<b>" + nPresup + "</b> presupuestos, <b>" + nPlant + "</b> plantillas propias, " +
      "más configuración e historial." +
      (tieneClaveIA ? "<br><b>Nota:</b> incluye la clave de API del copiloto — guarde el archivo en un lugar seguro." : "");
    $("pcod4-exportar").disabled = claves.length === 0;
  }

  function construirUI() {
    if ($("pcod4-fab")) return;
    var b = document.createElement("button");
    b.id = "pcod4-fab";
    b.type = "button";
    b.innerHTML = "⭳ Respaldo";
    b.title = "Respaldo y restauración de los datos de PRECOST (Alt+B) — exporta o restaura todos los presupuestos, plantillas y configuración de este navegador";
    document.body.appendChild(b);

    var mask = document.createElement("div");
    mask.id = "pcod4-mask";
    mask.className = "pcod4-mask";
    mask.innerHTML =
      '<div class="pcod4-win" role="dialog" aria-label="Respaldo y restauración">' +
      '  <h2>Respaldo y restauración <button class="pcod4-x" id="pcod4-cerrar" title="Cerrar (Esc)">✕</button></h2>' +
      '  <div class="pcod4-sub">S-005 · copia de seguridad portable de todos los datos del usuario</div>' +
      '  <div class="pcod4-estado" id="pcod4-estado"></div>' +
      '  <div class="pcod4-fila">' +
      '    <button class="pcod4-btn pcod4-prim" id="pcod4-exportar">Descargar respaldo completo (.json)</button>' +
      '    <button class="pcod4-btn" id="pcod4-restaurar">Restaurar desde archivo…</button>' +
      '    <input type="file" id="pcod4-archivo" accept=".json,application/json" style="display:none">' +
      '  </div>' +
      '  <div class="pcod4-err" id="pcod4-err"></div>' +
      '  <div class="pcod4-nota">' +
      "    El respaldo incluye <b>todo</b> lo guardado en este navegador (prefijo <code>p3pro.*</code>): presupuestos, " +
      "    plantillas, casos importados, resultados de laboratorio, historial de la calculadora y configuración.<br>" +
      "    La restauración es <b>modo reemplazo</b>: el navegador queda exactamente como estaba al generar el respaldo. " +
      "    Guarde copias del archivo fuera del navegador (disco, USB, nube): los datos viven solo en este dispositivo " +
      "    y se pierden si se borra el historial del navegador." +
      "  </div>" +
      "</div>";
    document.body.appendChild(mask);

    b.addEventListener("click", abrir);
    $("pcod4-cerrar").addEventListener("click", cerrar);
    mask.addEventListener("click", function (e) { if (e.target === mask) cerrar(); });
    $("pcod4-exportar").addEventListener("click", function () {
      var nombre = descargarRespaldo();
      if (nombre) { mostrarOk("Respaldo generado: " + nombre); }
    });
    $("pcod4-restaurar").addEventListener("click", function () { $("pcod4-archivo").click(); });
    $("pcod4-archivo").addEventListener("change", function () {
      var f = this.files && this.files[0];
      this.value = "";                       /* permitir re-seleccionar el mismo archivo */
      if (f) restaurarDesdeArchivo(f);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && mask.classList.contains("pcod4-open")) cerrar();
      if (e.altKey && (e.key === "b" || e.key === "B")) { e.preventDefault(); abrir(); }
    });
  }

  function abrir() {
    refrescarEstado();
    $("pcod4-mask").classList.add("pcod4-open");
  }
  function cerrar() { $("pcod4-mask").classList.remove("pcod4-open"); }
  function mostrarOk(txt) {
    var el = $("pcod4-err");                 /* reutiliza la línea de mensajes */
    el.style.display = "block";
    el.style.color = "#20723f";
    el.textContent = txt;
  }

  /* ------------------------------------------------------- gancho de pruebas */
  window.__pcodRespaldoAPI = {
    generar: generarRespaldo,
    validar: validarRespaldo,
    aplicar: aplicarRespaldo,
    descargar: descargarRespaldo,
    claves: clavesP3,
    abrir: abrir,
    cerrar: cerrar
  };

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", construirUI);
  else construirUI();
})();
