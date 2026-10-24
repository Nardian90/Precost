/* ============================================================================
 * OVERLAY IV — CALCULADORA DE COSTOS DE ACTIVIDAD (SIECONS §Manual pág. 18)
 * ----------------------------------------------------------------------------
 * Script 100% ADITIVO (patrón de overlay/precodi.js y overlay/recursos.js):
 * lo inyecta el servidor local al servir el HTML original; el archivo
 * PRECOST-v9.17.html en disco NO se modifica (SHA-256 verificado por request).
 *
 * Función SIECONS replicada (MATRIZ_PARIDAD S-080):
 *   «Calculadora: Evalúa y calcula el precio de una actividad con
 *    coeficientes personalizados.»
 *
 * Qué hace:
 *   - Abre con el botón flotante 🧮 o con Alt+C desde cualquier vista.
 *   - Busca una actividad por código (catálogo embebido, offline) o por
 *     texto (servidor PRECODI si está activo).
 *   - Carga la descomposición (endpoint III-C /api/descomposicion) con
 *     selección de versión de normas y de fuente de precios.
 *   - Permite editar coeficiente y precio de cada recurso, aplicar un
 *     coeficiente global de ajuste y una cantidad a evaluar.
 *   - Recalcula EN VIVO CMMN/CHMN/CEMN, total unitario y total evaluado,
 *     con importe = coef × precio por recurso (traza completa).
 *   - Compara contra el precio unitario oficial (motor PRECOST embebido y
 *     PRECODI de la versión) mostrando Δ% — nunca sobrescribe nada.
 *   - Exporta JSON, copia resumen al portapapeles y guarda historial
 *     (localStorage p3pro.calcHist — clave nueva, aditiva).
 *   - Sin servidor local: modo degradado honesto con PU agregado embebido
 *     (mat/mo/eq/total de DB.P) y aviso explícito.
 *
 * Qué NO hace:
 *   - No modifica el catálogo embebido, las vistas, el motor de cálculo ni
 *     los presupuestos existentes (p3pro.budgets intacto).
 *   - No mezcla versiones en silencio: cada número muestra su fuente.
 * ==========================================================================*/
(function () {
  "use strict";
  if (window.__pcodCalc) return;               // idempotente
  window.__pcodCalc = true;

  /* ------------------------------------------------------------------ estilos */
  var CSS = [
    "#pcod3-fab{position:fixed;right:16px;bottom:16px;z-index:9000;display:inline-flex;gap:6px;",
    "align-items:center;border:1px solid var(--border,#c9cedb);border-radius:22px;padding:8px 14px;",
    "background:var(--primary,#1a5fb4);color:#fff;font-size:13px;cursor:pointer;box-shadow:0 3px 10px rgba(0,0,0,.18)}",
    "#pcod3-fab:hover{filter:brightness(1.08)}",
    "#pcod3-mask{position:fixed;inset:0;background:rgba(15,20,30,.45);z-index:9001;display:flex;",
    "align-items:flex-start;justify-content:center;overflow:auto;padding:26px 10px}",
    "#pcod3-win{background:var(--bg-card,#fff);color:inherit;border:1px solid var(--border,#d8dce6);",
    "border-radius:14px;max-width:960px;width:100%;box-shadow:0 12px 40px rgba(0,0,0,.28);padding:18px 20px}",
    "#pcod3-win h2{margin:0;font-size:var(--fs-l,17px);display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}",
    "#pcod3-sub{color:var(--text-muted,#667);font-size:12px;margin:2px 0 12px}",
    ".pcod3-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}",
    ".pcod3-bar input,.pcod3-bar select{min-height:34px;padding:4px 8px;border:1px solid var(--border,#c9cedb);",
    "border-radius:8px;background:var(--bg,#fff);color:inherit;font-size:13px}",
    ".pcod3-bar input{min-width:200px;flex:1}",
    ".pcod3-btn{min-height:34px;padding:4px 12px;border:1px solid var(--border,#c9cedb);border-radius:8px;",
    "background:var(--bg,#fff);color:inherit;font-size:13px;cursor:pointer}",
    ".pcod3-btn:hover{background:rgba(26,95,180,.07)}",
    ".pcod3-btn.pcod3-prim{background:var(--primary,#1a5fb4);color:#fff;border-color:var(--primary,#1a5fb4)}",
    ".pcod3-tbl{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0}",
    ".pcod3-tbl th{text-align:left;border-bottom:2px solid var(--border,#d8dce6);padding:4px 6px;white-space:nowrap}",
    ".pcod3-tbl td{border-bottom:1px solid var(--border-soft,#eceff4);padding:4px 6px;vertical-align:top}",
    ".pcod3-tbl td.num,.pcod3-tbl th.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}",
    ".pcod3-tbl .pcod3-code{font-family:ui-monospace,monospace;font-size:11.5px}",
    ".pcod3-in{min-height:30px;width:96px;border:1px solid var(--border,#c9cedb);border-radius:7px;",
    "text-align:right;font-variant-numeric:tabular-nums;padding:2px 6px;background:var(--bg,#fff);color:inherit}",
    ".pcod3-in.pcod3-bad{border-color:#d33;background:rgba(221,51,51,.07)}",
    ".pcod3-tot td{font-weight:700;border-top:2px solid var(--border,#d8dce6)}",
    ".pcod3-res{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}",
    ".pcod3-res>div{border:1px solid var(--border,#d8dce6);border-radius:10px;padding:8px 12px;min-width:120px}",
    ".pcod3-res b{font-size:16px;font-variant-numeric:tabular-nums}",
    ".pcod3-res .pcod3-k{font-size:11px;color:var(--text-muted,#667)}",
    ".pcod3-tag{display:inline-block;background:rgba(26,95,180,.1);color:var(--primary,#1a5fb4);border-radius:5px;",
    "padding:1px 7px;font-size:11.5px;margin:0 4px 4px 0}",
    ".pcod3-tag.pcod3-warn{background:rgba(224,154,0,.14);color:#9a6700}",
    ".pcod3-tag.pcod3-ok{background:rgba(46,160,67,.12);color:#a7f37}",
    ".pcod3-box{border:1px solid var(--border,#d8dce6);border-radius:8px;padding:8px 11px;margin:8px 0;font-size:12.5px}",
    ".pcod3-box.pcod3-warnbox{border-color:#e0a000;background:rgba(224,154,0,.06)}",
    ".pcod3-mini{font-size:11px;color:var(--text-muted,#667)}",
    ".pcod3-hist{list-style:none;margin:6px 0 0;padding:0}",
    ".pcod3-hist li{display:flex;gap:8px;align-items:baseline;padding:3px 0;border-bottom:1px dashed var(--border-soft,#eceff4);font-size:12px}",
    ".pcod3-hist li span{color:var(--text-muted,#667)}",
    ".pcod3-hist li button{margin-left:auto}",
    "@media (max-width:720px){#pcod3-win{padding:12px}.pcod3-in{width:72px}}"
  ].join("");
  var st = document.createElement("style");
  st.id = "pcod3-styles";
  st.textContent = CSS;
  document.head.appendChild(st);

  /* ------------------------------------------------------------------ estado */
  var S = {
    abierto: false,
    versiones: [],           // catálogo de versiones del servidor
    versionId: null,         // normas (default 2017-raíz = la de mayor cobertura)
    precioVersionId: null,   // precios
    codigo: null,
    data: null,              // respuesta /api/descomposicion
    modo: "servidor",        // "servidor" | "embebido"
    ediciones: {},           // idx → {coef, precio} del usuario
    global: 1,               // coeficiente global de ajuste
    cantidad: 1,
    historial: []
  };
  var HIST_KEY = "p3pro.calcHist";

  /* --------------------------------------------------------------- helpers */
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(v, f) {
    if (v == null || isNaN(v)) return "—";
    var t = parseFloat(Number(v).toFixed(f == null ? 4 : f));
    return String(t);
  }
  function fmtM(v) {
    if (v == null || isNaN(v)) return "—";
    return Number(v).toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function api(ruta) {
    return fetch(ruta).then(function (r) {
      if (!r.ok && r.status !== 404) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  function cargarHistorial() {
    try { S.historial = JSON.parse(localStorage.getItem(HIST_KEY) || "[]"); }
    catch (e) { S.historial = []; }
  }
  function guardarHistorial(entrada) {
    S.historial.unshift(entrada);
    S.historial = S.historial.slice(0, 10);
    try { localStorage.setItem(HIST_KEY, JSON.stringify(S.historial)); } catch (e) { /* noop */ }
  }

  /* ------------------------------------------------------------ cálculo núcleo */
  /* Recalcula los subtotales a partir de componentes + ediciones del usuario.
   * importe = coef × precio (misma fórmula que la pestaña Recursos de III-C).
   * Nunca redondea en cálculo; el redondeo es solo de presentación (fmt). */
  function recalcular() {
    var out = { mat: 0, mo: 0, eq: 0, sinPrecio: 0, malos: [] };
    if (!S.data || !S.data.componentes) return out;
    S.data.componentes.forEach(function (c, i) {
      var ed = S.ediciones[i] || {};
      var coef = ed.coef != null ? ed.coef : c.coeficiente;
      var precio = ed.precio != null ? ed.precio : c.precio_mn;
      if (coef == null || isNaN(coef) || precio == null || isNaN(precio)) {
        out.sinPrecio++;
        if ((ed.coef != null && isNaN(ed.coef)) || (ed.precio != null && isNaN(ed.precio)))
          out.malos.push(i);
        return;
      }
      var imp = coef * precio;
      if (c.tipo === "material") out.mat += imp;
      else if (c.tipo === "mano_obra") out.mo += imp;
      else if (c.tipo === "equipo") out.eq += imp;
      else { /* juegos/semis: se reparten por tipo de sus componentes internos
                cuando el endpoint los trae expandidos; a nivel de fila se
                muestran como su propio subtotal conceptual */
        out["otros"] = (out["otros"] || 0) + imp;
      }
    });
    out.total = out.mat + out.mo + out.eq + (out.otros || 0);
    out.totalAjustado = out.total * (S.global || 1);
    out.totalEvaluado = out.totalAjustado * (S.cantidad || 0);
    return out;
  }

  /* ------------------------------------------------------------- PU embebido */
  function puEmbebido(codigo) {
    try {
      var p = DB.P[codigo];
      if (!p) return null;
      return { desc: p[0], um: p[1], total: p[2], mat: p[3], mo: p[4], eq: p[5], peso: p[6] };
    } catch (e) { return null; }
  }

  /* --------------------------------------------------------------- render UI */
  function fab() {
    if ($("pcod3-fab")) return;
    var b = document.createElement("button");
    b.id = "pcod3-fab";
    b.type = "button";
    b.title = "Calculadora de costos de actividad (Alt+C) — evaluar el precio de una actividad con coeficientes personalizados";
    b.setAttribute("aria-label", b.title);
    b.textContent = "🧮 Calculadora";
    b.addEventListener("click", abrir);
    document.body.appendChild(b);
    /* MISIÓN VII: coexistencia visual — si el botón del catálogo PRECODI
       (precodi.js, abajo-derecha) ya está en la página, apilar encima en
       lugar de solaparse (ambos botones quedan visibles y accesibles). */
    if (document.querySelector(".pcod-fab")) b.style.bottom = "58px";
  }

  function abrir() {
    if (S.abierto) { $("pcod3-cod") && $("pcod3-cod").focus(); return; }
    S.abierto = true;
    cargarHistorial();
    var mask = document.createElement("div");
    mask.id = "pcod3-mask";
    mask.innerHTML =
      '<div id="pcod3-win" role="dialog" aria-modal="true" aria-label="Calculadora de costos de actividad">' +
      "<h2>🧮 Calculadora de costos de actividad</h2>" +
      '<div id="pcod3-sub">Función S-80 del manual SIECONS («Evalúa y calcula el precio de una actividad con ' +
      "coeficientes personalizados»), integrada a PRECOST con descomposición PRECODI versionada. " +
      "El cálculo es coef × precio por recurso; nada se sobrescribe.</div>" +
      '<div class="pcod3-bar">' +
      '<input id="pcod3-cod" list="pcod3-dl" placeholder="Código de actividad (p. ej. 012141) o texto…" ' +
      'aria-label="Código o texto de búsqueda" autocomplete="off">' +
      "<datalist id=\"pcod3-dl\"></datalist>" +
      '<button id="pcod3-go" class="pcod3-btn pcod3-prim" type="button">Consultar</button>' +
      '<select id="pcod3-vn" aria-label="Versión de normas" title="Versión de normas"></select>' +
      '<select id="pcod3-vp" aria-label="Fuente de precios" title="Fuente de precios"></select>' +
      '<button id="pcod3-cerrar" class="pcod3-btn" type="button" title="Cerrar (Esc)">✕ Cerrar</button>' +
      "</div>" +
      '<div id="pcod3-cuerpo"></div>' +
      "</div>";
    document.body.appendChild(mask);
    $("pcod3-cerrar").addEventListener("click", cerrar);
    $("pcod3-go").addEventListener("click", consultar);
    $("pcod3-cod").addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); consultar(); }
    });
    mask.addEventListener("mousedown", function (ev) {
      if (ev.target === mask) cerrar();
    });
    $("pcod3-cod").focus();
    precargarDatalist();
    cargarVersiones();
    pintarVacio();
  }

  function cerrar() {
    var m = $("pcod3-mask");
    if (m) m.remove();
    S.abierto = false;
  }

  function pintarVacio() {
    $("pcod3-cuerpo").innerHTML =
      '<div class="pcod3-box">Escriba un código de actividad (p. ej. <b>012141</b>) y pulse ' +
      "<b>Consultar</b>. También funciona sin servidor local: en ese caso se evalúa el " +
      "precio unitario oficial embebido (modo degradado, indicado en pantalla).</div>" +
      pintarHistorial();
  }

  function pintarHistorial() {
    if (!S.historial.length) return "";
    var h = '<div class="pcod3-box" style="margin-top:10px"><b>Historial reciente</b>' +
      '<ul class="pcod3-hist">';
    S.historial.forEach(function (e, i) {
      h += '<li><span class="pcod3-code">' + esc(e.codigo) + "</span> " + esc((e.desc || "").slice(0, 44)) +
        ' <span>· total ' + fmtM(e.total) + " · ×" + fmt(e.global, 2) + " · " + esc(e.version) + "</span>" +
        '<button class="pcod3-btn" type="button" data-pc3h="' + i + '">Abrir</button></li>';
    });
    h += "</ul></div>";
    return h;
  }

  function precargarDatalist() {
    try {
      var dl = $("pcod3-dl"), n = 0;
      Object.keys(DB.P).slice(0, 3000).forEach(function (c) {
        var o = document.createElement("option");
        o.value = c;
        dl.appendChild(o);
        n++;
      });
    } catch (e) { /* sin catálogo embebido accesible: el servidor resuelve */ }
  }

  function cargarVersiones() {
    api("/api/versiones").then(function (d) {
      var sn = $("pcod3-vn"), sp = $("pcod3-vp");
      if (!sn || !sp) return;   /* MISIÓN V: cierre de la calculadora mientras
                                   cargaba — carrera latente de IV: sin guarda,
                                   la promesa rechazaba con «Cannot set properties
                                   of null (outerHTML)». Nunca romper PRECOST. */
      S.versiones = d.versiones || [];
      sn.innerHTML = ""; sp.innerHTML = "";
      var mejor = null;
      S.versiones.forEach(function (v) {
        if (v.estado !== "importada") return;
        var o1 = document.createElement("option");
        o1.value = v.id;
        o1.textContent = (v.catalogo || "") + " " + v.version + " (" + (v.descomponibles || 0).toLocaleString("es") + " descomp.)";
        sn.appendChild(o1.cloneNode(true));
        sp.appendChild(o1.cloneNode(true));
        if (v.version === "2017-raiz") mejor = v.id;
      });
      if (mejor == null && S.versiones.length) mejor = S.versiones[0].id;
      S.versionId = S.versionId || mejor;
      S.precioVersionId = S.precioVersionId || mejor;
      sn.value = S.versionId; sp.value = S.precioVersionId;
      sn.onchange = function () { S.versionId = +sn.value; if (S.codigo) consultar(); };
      sp.onchange = function () { S.precioVersionId = +sp.value; if (S.codigo) consultar(); };
    }).catch(function () {
      var sn2 = $("pcod3-vn"), sp2 = $("pcod3-vp");
      if (sn2) sn2.outerHTML = '<span class="pcod3-mini">sin servidor local</span>';
      if (sp2) sp2.outerHTML = "";
      S.modo = "embebido";
    });
  }

  function consultar() {
    var q = ($("pcod3-cod").value || "").trim();
    if (!q) { $("pcod3-cod").focus(); return; }
    S.ediciones = {}; S.global = 1; S.cantidad = 1;
    $("pcod3-cuerpo").innerHTML = '<div class="pcod3-box">Consultando…</div>';
    if (/^\d+$/.test(q)) {
      S.codigo = q;
      cargarDescomposicion();
    } else {
      api("/api/partidas?q=" + encodeURIComponent(q) +
          (S.versionId ? "&version_id=" + S.versionId : "") + "&limit=8")
        .then(function (d) {
          var r = (d.resultados || d.partidas || [])[0];
          if (!r) throw new Error("sin resultados");
          S.codigo = r.codigo;
          cargarDescomposicion();
        })
        .catch(function () {
          // respaldo embebido: primera partida cuya descripción contenga el texto
          try {
            for (var c in DB.P) {
              if (String(DB.P[c][0]).toUpperCase().indexOf(q.toUpperCase()) >= 0) {
                S.codigo = c; cargarDescomposicion(); return;
              }
            }
          } catch (e) { /* noop */ }
          $("pcod3-cuerpo").innerHTML =
            '<div class="pcod3-box pcod3-warnbox">No se encontró ninguna actividad para «' +
            esc(q) + "». Pruebe con el código (p. ej. 012141) o con el servidor local activo.</div>" +
            pintarHistorial();
        });
    }
  }

  function cargarDescomposicion() {
    var url = "/api/descomposicion/" + encodeURIComponent(S.codigo) +
              "?version_id=" + (S.versionId || "") +
              "&precio_version_id=" + (S.precioVersionId || S.versionId || "");
    api(url).then(function (d) {
      if (d.error) { modoEmbebido(d.error); return; }
      S.modo = "servidor";
      S.data = d;
      pintarResultado();
    }).catch(function () { modoEmbebido("sin conexión con el servidor local"); });
  }

  function modoEmbebido(motivo) {
    S.modo = "embebido";
    var pu = puEmbebido(S.codigo);
    if (!pu) {
      $("pcod3-cuerpo").innerHTML =
        '<div class="pcod3-box pcod3-warnbox">Código <b>' + esc(S.codigo) + "</b> no encontrado" +
        " (" + esc(motivo) + "). Verifique el código o active el servidor local " +
        "(scripts/servidor_precodi.py).</div>" + pintarHistorial();
      return;
    }
    S.data = null;
    var html =
      '<div class="pcod3-box pcod3-warnbox"><b>Modo degradado (sin servidor local):</b> ' +
      esc(motivo) + ". Se evalúa el precio unitario <b>oficial embebido</b> de PRECOST 2025 " +
      "(agregado mat/mo/eq, sin descomposición por recurso). Para editar la descomposición " +
      "recurso a recurso, active el servidor local.</div>" +
      cabeceraPartida({ codigo: S.codigo, descripcion: pu.desc, unidad: pu.um }, pu) +
      '<div class="pcod3-res">' +
      celdaRes("PU oficial embebido", fmtM(pu.total)) +
      celdaRes("× ajuste global", fmt(S.global, 4)) +
      celdaRes("PU evaluado", '<span id="pcod3-puEv">' + fmtM(pu.total * S.global) + "</span>") +
      celdaRes("Total evaluación (×" + fmt(S.cantidad, 4) + ")",
               '<span id="pcod3-totEv">' + fmtM(pu.total * S.global * S.cantidad) + "</span>") +
      "</div>" +
      '<div class="pcod3-bar">Coeficiente global: <input id="pcod3-glob" class="pcod3-in" type="number" ' +
      'step="any" value="1" min="0" aria-label="Coeficiente global de ajuste"> ' +
      "Cantidad a evaluar: <input id=\"pcod3-cant\" class=\"pcod3-in\" type=\"number\" step=\"any\" " +
      'value="1" min="0" aria-label="Cantidad a evaluar"></div>' +
      '<div class="pcod3-bar"><button id="pcod3-json" class="pcod3-btn" type="button">⬇ Exportar JSON</button>' +
      '<button id="pcod3-copiar" class="pcod3-btn" type="button">⧉ Copiar resumen</button>' +
      '<button id="pcod3-hist-save" class="pcod3-btn" type="button">★ Guardar en historial</button></div>';
    $("pcod3-cuerpo").innerHTML = html;
    $("pcod3-cod").value = S.codigo;
    engancharControlesEmbebido(pu);
  }

  function celdaRes(k, v) {
    return '<div><div class="pcod3-k">' + esc(k) + '</div><b>' + v + "</b></div>";
  }

  function cabeceraPartida(p, pu) {
    var umExtra = "";
    if (pu && p.unidad && pu.um && String(p.unidad).toUpperCase() !== String(pu.um).toUpperCase()) {
      umExtra = ' <span class="pcod3-tag pcod3-warn" title="La unidad publicada por PRECOST difiere de la ' +
        "unidad PRECODI/SBD de la misma partida (hallazgo de la auditoría de fidelidad IV)\">UM publicada: " +
        esc(pu.um) + " · PRECODI: " + esc(p.unidad) + "</span>";
    }
    return '<div class="pcod3-box"><b class="pcod3-code">' + esc(p.codigo) + "</b> — " + esc(p.descripcion) +
      '<br><span class="pcod3-mini">UM: ' + esc(p.unidad || pu.um) + umExtra + "</span></div>";
  }

  function pintarResultado() {
    var d = S.data, pu = puEmbebido(S.codigo);
    var r = recalcular();
    var cuerpo = "";
    cuerpo += cabeceraPartida(d.partida, pu);

    if (!d.tiene_norma) {
      cuerpo += '<div class="pcod3-box pcod3-warnbox">Esta partida no tiene descomposición en la versión ' +
        esc(d.partida.version) + ". Se evalúa el PU embebido.</div>";
    }
    if ((d.advertencias || []).length) {
      cuerpo += '<div class="pcod3-box pcod3-warnbox"><b>Advertencias de la fuente:</b><br>' +
        d.advertencias.map(esc).join("<br>") + "</div>";
    }

    /* tabla de componentes editable */
    cuerpo += '<table class="pcod3-tbl" id="pcod3-tbl"><thead><tr>' +
      "<th>Tipo</th><th>Código</th><th>Descripción</th><th>UM</th>" +
      '<th class="num">Coef.</th><th class="num">Precio</th><th class="num">Importe</th></tr></thead><tbody>';
    d.componentes.forEach(function (c, i) {
      var ed = S.ediciones[i] || {};
      var coef = ed.coef != null ? ed.coef : c.coeficiente;
      var precio = ed.precio != null ? ed.precio : c.precio_mn;
      var imp = (coef != null && precio != null && !isNaN(coef) && !isNaN(precio)) ? coef * precio : null;
      cuerpo += "<tr>" +
        "<td>" + esc(c.tipo_nombre || c.tipo) + "</td>" +
        '<td class="pcod3-code">' + esc(c.codigo) + "</td>" +
        "<td>" + esc(c.descripcion || "—") +
        (c.advertencia ? '<br><span class="pcod3-mini">⚠ ' + esc(c.advertencia) + "</span>" : "") +
        (c.precio_respaldo ? '<br><span class="pcod3-mini">precio de respaldo (versión de la norma)</span>' : "") +
        "</td>" +
        "<td>" + esc(c.unidad || "—") + "</td>" +
        '<td class="num"><input class="pcod3-in" data-pc3i="' + i + '" data-pc3f="coef" type="number" step="any" ' +
        'value="' + (coef == null ? "" : coef) + '" aria-label="Coeficiente de ' + esc(c.codigo) + '"></td>' +
        '<td class="num"><input class="pcod3-in" data-pc3i="' + i + '" data-pc3f="precio" type="number" step="any" ' +
        'value="' + (precio == null ? "" : precio) + '" aria-label="Precio de ' + esc(c.codigo) + '"></td>' +
        '<td class="num" id="pcod3-imp' + i + '">' + (imp == null ? "—" : fmt(imp)) + "</td>" +
        "</tr>";
      (c.hijos || []).forEach(function (h) {
        cuerpo += '<tr class="pcod3-hij"><td class="pcod3-mini">↳ ' + esc(h.tipo_nombre || h.tipo) + "</td>" +
          '<td class="pcod3-code">' + esc(h.codigo) + '</td><td class="pcod3-mini">' + esc(h.descripcion) + "</td>" +
          '<td class="pcod3-mini">' + esc(h.unidad || "") + '</td><td class="num pcod3-mini">' + fmt(h.coeficiente) +
          '</td><td class="num pcod3-mini">' + fmt(h.precio_mn) + '</td><td class="num pcod3-mini">' +
          fmt(h.importe) + "</td></tr>";
      });
    });
    cuerpo += "</tbody></table>";

    /* controles */
    cuerpo += '<div class="pcod3-bar">Coeficiente global de ajuste: ' +
      '<input id="pcod3-glob" class="pcod3-in" type="number" step="any" value="' + S.global + '" min="0" ' +
      'aria-label="Coeficiente global de ajuste"> Cantidad a evaluar: ' +
      '<input id="pcod3-cant" class="pcod3-in" type="number" step="any" value="' + S.cantidad + '" min="0" ' +
      'aria-label="Cantidad a evaluar"></div>';

    /* resultados */
    cuerpo += '<div class="pcod3-res" id="pcod3-res">' +
      celdaRes("CMMN (materiales)", '<span id="pcod3-rMat">' + fmt(r.mat) + "</span>") +
      celdaRes("CHMN (mano de obra)", '<span id="pcod3-rMo">' + fmt(r.mo) + "</span>") +
      celdaRes("CEMN (equipos)", '<span id="pcod3-rEq">' + fmt(r.eq) + "</span>") +
      (r.otros ? celdaRes("Juegos/Semis", '<span id="pcod3-rOt">' + fmt(r.otros) + "</span>") : "") +
      celdaRes("Total unitario", '<span id="pcod3-rTot">' + fmt(r.totalAjustado) + "</span>") +
      celdaRes("Total evaluación", '<span id="pcod3-rEv">' + fmt(r.totalEvaluado) + "</span>") +
      "</div>";

    /* comparación contra PU oficiales (nunca sobrescribe) */
    var puPrecodi = d.partida.costo_total_mn;
    var deltas = [];
    if (pu) deltas.push({ n: "PU motor PRECOST (embebido 2025)", v: pu.total });
    if (puPrecodi != null) deltas.push({ n: "PU " + d.partida.version, v: puPrecodi });
    if (deltas.length) {
      cuerpo += '<div class="pcod3-box"><b>Comparación (referencia, sin sobrescribir):</b><br>';
      deltas.forEach(function (x) {
        var dd = r.total ? ((r.total - x.v) / x.v) * 100 : null;
        cuerpo += '<span class="pcod3-tag">' + esc(x.n) + ": " + fmtM(x.v) + "</span>";
        if (dd != null)
          cuerpo += '<span class="pcod3-tag ' + (Math.abs(dd) <= 1 ? "pcod3-ok" : "pcod3-warn") + '">Δ ' +
            (dd >= 0 ? "+" : "") + dd.toFixed(2) + "%</span><br>";
      });
      cuerpo += '<span class="pcod3-mini">La descomposición se calcula con normas de ' + esc(d.partida.version) +
        " y precios de la fuente seleccionada; el PU embebido es la publicación oficial 2025.</span></div>";
    }

    /* traza y acciones */
    cuerpo += '<div class="pcod3-box pcod3-mini">Trazabilidad: importe = coef × precio por recurso · ' +
      "cálculo sin redondeo intermedio (presentación a 2–4 dec) · normas: " + esc(d.partida.version) +
      (d.verificacion ? " · verificación contra costos almacenados: " +
        ["cmmn", "chmn", "cemn"].map(function (k) {
          return k.toUpperCase() + " " + (d.verificacion[k] && d.verificacion[k].coincide ? "✓" : "✗");
        }).join(" ") : "") + "</div>";
    cuerpo += '<div class="pcod3-bar"><button id="pcod3-json" class="pcod3-btn" type="button">⬇ Exportar JSON</button>' +
      '<button id="pcod3-copiar" class="pcod3-btn" type="button">⧉ Copiar resumen</button>' +
      '<button id="pcod3-hist-save" class="pcod3-btn" type="button">★ Guardar en historial</button>' +
      '<span class="pcod3-mini" id="pcod3-estado"></span></div>';
    cuerpo += pintarHistorial();

    $("pcod3-cuerpo").innerHTML = cuerpo;
    $("pcod3-cod").value = S.codigo;
    engancharControles();
  }

  function engancharControles() {
    /* entradas por recurso */
    Array.prototype.forEach.call(
      document.querySelectorAll('#pcod3-tbl input[data-pc3i]'), function (inp) {
        inp.addEventListener("input", function () {
          var i = +inp.getAttribute("data-pc3i"), f = inp.getAttribute("data-pc3f");
          var v = inp.value === "" ? null : parseFloat(inp.value);
          if (v != null && isNaN(v)) { inp.classList.add("pcod3-bad"); }
          else { inp.classList.remove("pcod3-bad"); }
          if (!S.ediciones[i]) S.ediciones[i] = {};
          S.ediciones[i][f] = v;
          refrescar();
        });
      });
    var g = $("pcod3-glob"), c = $("pcod3-cant");
    if (g) g.addEventListener("input", function () {
      S.global = parseFloat(g.value);
      if (isNaN(S.global)) S.global = 1;
      refrescar();
    });
    if (c) c.addEventListener("input", function () {
      S.cantidad = parseFloat(c.value);
      if (isNaN(S.cantidad)) S.cantidad = 0;
      refrescar();
    });
    $("pcod3-json").addEventListener("click", exportarJSON);
    $("pcod3-copiar").addEventListener("click", copiarResumen);
    $("pcod3-hist-save").addEventListener("click", guardarEnHistorial);
    Array.prototype.forEach.call(
      document.querySelectorAll("#pcod3-cuerpo button[data-pc3h]"), function (b) {
        b.addEventListener("click", function () {
          var e = S.historial[+b.getAttribute("data-pc3h")];
          if (!e) return;
          $("pcod3-cod").value = e.codigo;
          if (e.version_id && S.versionId) { S.versionId = e.version_id; $("pcod3-vn").value = e.version_id; }
          consultar();
        });
      });
  }

  function engancharControlesEmbebido(pu) {
    var g = $("pcod3-glob"), c = $("pcod3-cant");
    function ev() {
      $("pcod3-puEv").textContent = fmtM(pu.total * (isNaN(S.global) ? 1 : S.global));
      $("pcod3-totEv").textContent = fmtM(pu.total * (isNaN(S.global) ? 1 : S.global) *
                                            (isNaN(S.cantidad) ? 0 : S.cantidad));
    }
    if (g) g.addEventListener("input", function () {
      S.global = parseFloat(g.value); ev();
    });
    if (c) c.addEventListener("input", function () {
      S.cantidad = parseFloat(c.value); ev();
    });
    $("pcod3-json").addEventListener("click", exportarJSON);
    $("pcod3-copiar").addEventListener("click", copiarResumen);
    $("pcod3-hist-save").addEventListener("click", guardarEnHistorial);
  }

  function refrescar() {
    var r = recalcular();
    if ($("pcod3-rMat")) $("pcod3-rMat").textContent = fmt(r.mat);
    if ($("pcod3-rMo")) $("pcod3-rMo").textContent = fmt(r.mo);
    if ($("pcod3-rEq")) $("pcod3-rEq").textContent = fmt(r.eq);
    if ($("pcod3-rOt")) $("pcod3-rOt").textContent = fmt(r.otros || 0);
    if ($("pcod3-rTot")) $("pcod3-rTot").textContent = fmt(r.totalAjustado);
    if ($("pcod3-rEv")) $("pcod3-rEv").textContent = fmt(r.totalEvaluado);
    if (S.data && S.data.componentes) {
      S.data.componentes.forEach(function (comp, i) {
        var celda = $("pcod3-imp" + i);
        if (!celda) return;
        var ed = S.ediciones[i] || {};
        var coef = ed.coef != null ? ed.coef : comp.coeficiente;
        var precio = ed.precio != null ? ed.precio : comp.precio_mn;
        celda.textContent = (coef != null && precio != null && !isNaN(coef) && !isNaN(precio))
          ? fmt(coef * precio) : "—";
      });
    }
  }

  function exportarJSON() {
    var r = recalcular();
    var pu = puEmbebido(S.codigo);
    var doc = {
      herramienta: "PRECOST 9.17 — Calculadora de costos de actividad (overlay IV, S-80)",
      codigo: S.codigo,
      modo: S.modo,
      global: S.global, cantidad: S.cantidad,
      resultado: r,
      descomposicion: S.data ? {
        version_normas: S.data.partida.version,
        componentes: S.data.componentes.map(function (c, i) {
          var ed = S.ediciones[i] || {};
          return {
            tipo: c.tipo, codigo: c.codigo, descripcion: c.descripcion,
            unidad: c.unidad,
            coef_original: c.coeficiente, coef_usado: ed.coef != null ? ed.coef : c.coeficiente,
            precio_original: c.precio_mn, precio_usado: ed.precio != null ? ed.precio : c.precio_mn,
            advertencia: c.advertencia || null
          };
        })
      } : null,
      pu_embebido: pu,
      pu_precodi: S.data ? S.data.partida.costo_total_mn : null
    };
    var blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "calculadora_" + (S.codigo || "actividad") + ".json";
    a.click();
    URL.revokeObjectURL(a.href);
    if ($("pcod3-estado")) $("pcod3-estado").textContent = "JSON exportado.";
  }

  function resumenTexto() {
    var r = recalcular();
    var pu = puEmbebido(S.codigo);
    return "PRECOST · Calculadora de actividad " + S.codigo +
      "\nTotal unitario: " + fmt(r.totalAjustado) + " (× ajuste " + fmt(S.global, 4) + ")" +
      "\nCMMN " + fmt(r.mat) + " · CHMN " + fmt(r.mo) + " · CEMN " + fmt(r.eq) +
      "\nTotal evaluación (×" + fmt(S.cantidad, 4) + "): " + fmt(r.totalEvaluado) +
      (pu ? "\nPU oficial embebido: " + fmtM(pu.total) : "") +
      (S.data ? "\nNormas: " + S.data.partida.version : "");
  }

  function copiarResumen() {
    var t = resumenTexto();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(t).then(function () {
        if ($("pcod3-estado")) $("pcod3-estado").textContent = "Resumen copiado.";
      }).catch(function () { fallbackCopiar(t); });
    } else fallbackCopiar(t);
  }
  function fallbackCopiar(t) {
    var ta = document.createElement("textarea");
    ta.value = t;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); if ($("pcod3-estado")) $("pcod3-estado").textContent = "Resumen copiado."; }
    catch (e) { /* noop */ }
    ta.remove();
  }

  function guardarEnHistorial() {
    var r = recalcular();
    guardarHistorial({
      codigo: S.codigo,
      desc: (S.data ? S.data.partida.descripcion : (puEmbebido(S.codigo) || {}).desc) || "",
      total: r.totalAjustado, global: S.global,
      version: S.data ? S.data.partida.version : "embebido",
      version_id: S.versionId, ts: new Date().toISOString()
    });
    pintarResultado();
  }

  /* ------------------------------------------------------------- integración */
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && S.abierto) { cerrar(); return; }
    if (ev.altKey && (ev.key === "c" || ev.key === "C")) {
      ev.preventDefault();
      S.abierto ? cerrar() : abrir();
    }
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fab);
  } else { fab(); }
})();
