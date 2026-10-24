/* ============================================================================
 * OVERLAY PRECODI — MISIÓN III-B · Fase 5 (integración vertical en PRECOST)
 * ----------------------------------------------------------------------------
 * Script 100% ADITIVO: lo inyecta el servidor local (scripts/servidor_precodi.py)
 * al servir el HTML original; el archivo PRECOST-v9.17.html en disco NO se
 * modifica. No toca el catálogo embebido, ni las vistas existentes, ni el
 * contrato PRECOST-AI-JSON: solo añade un botón flotante y un panel propio
 * con estilos prefijados (.pcod-) consultando la API local /api/*.
 *
 * MISIÓN VIII — paridad «literal» en la web: cuando la API local no está
 * disponible (GitHub Pages) y existe la capa de datos embebidos
 * (window.__pcodEstatico, overlay estatico.js), las MISMAS consultas se
 * resuelven desde dist/data/*.json con idénticas formas de respuesta. Cada
 * fetch tiene .catch: nunca queda una búsqueda colgada (razón por la que
 * este overlay antes se excluía del artefacto estático — ya no).
 * ==========================================================================*/
(function () {
  "use strict";
  if (window.__pcodOverlay) return;            // idempotente
  window.__pcodOverlay = true;

  /* ---------------------------------------------------------------- estilos */
  var css = [
    ".pcod-fab{position:fixed;bottom:18px;right:18px;z-index:2147483000;background:#1a5fb4;color:#fff;",
    "border:none;border-radius:22px;padding:11px 18px;font:600 13px/1 system-ui,sans-serif;cursor:pointer;",
    "box-shadow:0 4px 14px rgba(0,0,0,.35)}",
    ".pcod-fab:hover{background:#12488a}",
    ".pcod-panel{position:fixed;top:0;right:0;bottom:0;width:min(480px,96vw);z-index:2147483001;",
    "background:#14161b;color:#e8eaed;display:none;flex-direction:column;font:13px/1.45 system-ui,sans-serif;",
    "box-shadow:-6px 0 24px rgba(0,0,0,.5);border-left:1px solid #2b2f3a}",
    ".pcod-panel.pcod-open{display:flex}",
    ".pcod-h{padding:12px 14px;border-bottom:1px solid #2b2f3a;display:flex;gap:8px;align-items:center}",
    ".pcod-h b{font-size:14px;color:#8cf}",
    ".pcod-h small{color:#9aa0a6;flex:1}",
    ".pcod-x{background:#2b2f3a;color:#e8eaed;border:none;border-radius:6px;cursor:pointer;padding:4px 9px;font-size:12px}",
    ".pcod-body{overflow:auto;padding:12px 14px;flex:1}",
    ".pcod-row{display:flex;gap:6px;margin-bottom:10px}",
    ".pcod-inp{flex:1;background:#1e2128;color:#e8eaed;border:1px solid #333846;border-radius:6px;padding:7px 9px;font-size:13px}",
    ".pcod-sel{background:#1e2128;color:#e8eaed;border:1px solid #333846;border-radius:6px;padding:7px 6px;font-size:12px;max-width:150px}",
    ".pcod-btn{background:#1a5fb4;color:#fff;border:none;border-radius:6px;padding:7px 13px;font-size:13px;cursor:pointer}",
    ".pcod-res{width:100%;border-collapse:collapse;margin-top:4px}",
    ".pcod-res td{padding:6px 6px;border-bottom:1px solid #23262e;vertical-align:top}",
    ".pcod-res tr{cursor:pointer}.pcod-res tr:hover td{background:#1b1e25}",
    ".pcod-cod{color:#8cf;font-family:ui-monospace,monospace;white-space:nowrap}",
    ".pcod-num{text-align:right;white-space:nowrap;font-family:ui-monospace,monospace}",
    ".pcod-dim{color:#9aa0a6}",
    ".pcod-box{background:#1b1e25;border:1px solid #2b2f3a;border-radius:8px;padding:9px 11px;margin:8px 0}",
    ".pcod-prov{font-size:11px;color:#9aa0a6;word-break:break-all}",
    ".pcod-tbl{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0}",
    ".pcod-tbl th{text-align:left;color:#9aa0a6;font-weight:600;border-bottom:1px solid #2b2f3a;padding:4px 6px}",
    ".pcod-tbl td{padding:4px 6px;border-bottom:1px solid #20232b}",
    ".pcod-ok{color:#5ad677}.pcod-dif{color:#f0c674}",
    ".pcod-tag{display:inline-block;background:#23304a;color:#8cf;border-radius:4px;padding:1px 6px;font-size:11px;margin-right:4px}",
    ".pcod-comp{color:#9aa0a6;font-size:11px}",
    ".pcod-h3{margin:4px 0 2px;font-size:14px;color:#fff}",
    ".pcod-caso{background:#12351f;border:1px solid #1d5c33;color:#9fe0ae;border-radius:6px;",
    "padding:6px 10px;font-size:12px;cursor:pointer;margin-bottom:10px}"
  ].join("");
  var st = document.createElement("style");
  st.id = "pcod-styles";
  st.textContent = css;
  document.head.appendChild(st);

  /* ------------------------------------------------------------- estructura */
  var fab = document.createElement("button");
  fab.className = "pcod-fab";
  fab.textContent = "▤ Catálogo PRECODI";
  fab.title = "Consultar el catálogo PRECODI importado (SQLite local, solo lectura)";

  var panel = document.createElement("div");
  panel.className = "pcod-panel";
  panel.innerHTML =
    '<div class="pcod-h"><b>PRECODI</b><small>catálogo importado · SQLite local</small>' +
    '<button class="pcod-x" id="pcod-close">✕</button></div>' +
    '<div class="pcod-body">' +
    '  <div class="pcod-caso" id="pcod-caso">▶ Caso de prueba documentado: partida 012141 (raíz 2017)</div>' +
    '  <div class="pcod-row">' +
    '    <input class="pcod-inp" id="pcod-q" placeholder="Código o descripción (p. ej. 012141 o «roca»)" />' +
    '    <button class="pcod-btn" id="pcod-buscar">Buscar</button>' +
    '  </div>' +
    '  <div class="pcod-row">' +
    '    <select class="pcod-sel" id="pcod-ver"></select>' +
    '    <span class="pcod-dim" id="pcod-verinfo" style="align-self:center;flex:1"></span>' +
    '  </div>' +
    '  <div id="pcod-cont"></div>' +
    '</div>';
  document.body.appendChild(fab);
  document.body.appendChild(panel);

  var cont = panel.querySelector("#pcod-cont");
  var selVer = panel.querySelector("#pcod-ver");
  var verInfo = panel.querySelector("#pcod-verinfo");
  var input = panel.querySelector("#pcod-q");
  var fuente = "servidor";                       // MISIÓN VIII: servidor | web

  function etiquetaFuente() {
    var s = panel.querySelector(".pcod-h small");
    if (s) s.textContent = fuente === "web"
      ? "catálogo PRECODI · datos embebidos (web)"
      : "catálogo importado · SQLite local";
  }

  fab.addEventListener("click", function () {
    panel.classList.toggle("pcod-open");
    if (panel.classList.contains("pcod-open")) { cargarVersiones(); input.focus(); }
  });
  panel.querySelector("#pcod-close").addEventListener("click", function () { panel.classList.remove("pcod-open"); });
  panel.querySelector("#pcod-buscar").addEventListener("click", buscar);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") buscar(); });
  panel.querySelector("#pcod-caso").addEventListener("click", function () { detalle("012141"); });
  selVer.addEventListener("change", function () {
    var v = versionActual();
    verInfo.textContent = v ? (v.partidas.toLocaleString() + " partidas · " + v.normas.toLocaleString() + " normas") : "";
  });

  /* ------------------------------------------------------------------- datos */
  var versiones = [];
  function conVersiones(d) {
    versiones = d.versiones || [];
    selVer.innerHTML = "";
    versiones.forEach(function (v) {
      if (v.partidas === 0) return;                    // referencias sin filas propias
      var o = document.createElement("option");
      o.value = v.id;
      o.textContent = v.catalogo + " · " + v.version;
      selVer.appendChild(o);
    });
    // por defecto: la última versión PRECODI con normas
    var conNormas = versiones.filter(function (v) { return v.normas > 0; });
    if (conNormas.length) selVer.value = String(conNormas[conNormas.length - 1].id);
    selVer.dispatchEvent(new Event("change"));
    cont.innerHTML = '<div class="pcod-dim">Escriba un código o texto para buscar en el catálogo' +
      (fuente === "web" ? " (datos PRECODI embebidos: sin servidor)." : " importado.") + "</div>";
  }
  function cargarVersiones() {
    fetch("/api/versiones").then(function (r) { return r.json(); }).then(function (d) {
      fuente = "servidor"; etiquetaFuente(); conVersiones(d);
    }).catch(function () {
      /* MISIÓN VIII: sin servidor local → datos embebidos de la web */
      if (window.__pcodEstatico) {
        window.__pcodEstatico.versiones().then(function (d) {
          fuente = "web"; etiquetaFuente(); conVersiones(d);
        }).catch(function (e) {
          cont.innerHTML = '<div class="pcod-dim">Catálogo PRECODI no disponible: ' +
            "inicie el servidor local o publique los datos embebidos (dist/data).</div>";
        });
      } else {
        cont.innerHTML = '<div class="pcod-dim">Capa local PRECODI no disponible ' +
          "(inicie scripts/servidor_precodi.py).</div>";
      }
    });
  }
  function versionActual() {
    var id = parseInt(selVer.value, 10);
    return versiones.filter(function (v) { return v.id === id; })[0] || null;
  }

  function buscar() {
    var q = input.value.trim();
    if (!q) return;
    cont.innerHTML = '<div class="pcod-dim">Buscando…</div>';
    var ver = selVer.value ? parseInt(selVer.value, 10) : null;
    fetch("/api/partidas?q=" + encodeURIComponent(q) + (ver != null ? "&version_id=" + ver : "") + "&limit=60")
      .then(function (r) { return r.json(); })
      .then(function (d) { conResultados(q, d); })
      .catch(function () {
        /* MISIÓN VIII: fallback a los datos embebidos (misma forma de respuesta) */
        if (window.__pcodEstatico) {
          window.__pcodEstatico.partidas(q, ver, 60).then(function (d) { conResultados(q, d); })
            .catch(function (e) {
              cont.innerHTML = '<div class="pcod-dim">Error en la búsqueda: ' +
                String(e && e.message || e) + "</div>";
            });
        } else {
          cont.innerHTML = '<div class="pcod-dim">Capa local PRECODI no disponible.</div>';
        }
      });
  }

  function conResultados(q, d) {
    if (!d.resultados.length) { cont.innerHTML = '<div class="pcod-dim">Sin resultados para «' + q + '».</div>'; return; }
    var html = '<table class="pcod-res">' + d.resultados.map(function (p) {
      return "<tr data-cod='" + p.codigo + "'><td class='pcod-cod'>" + p.codigo +
        "</td><td>" + esc(p.descripcion) + ' <span class="pcod-dim">(' + esc(p.unidad || "") + ")</span></td>" +
        "<td class='pcod-num'>" + (p.costo_total_mn == null ? "—" : p.costo_total_mn.toFixed(2)) + "</td></tr>";
    }).join("") + "</table>";
    cont.innerHTML = html + '<div class="pcod-dim">' + d.n + ' resultado(s) — costo MN de la versión seleccionada' +
      (fuente === "web" ? " · datos embebidos" : "") + "</div>";
    [].forEach.call(cont.querySelectorAll("tr[data-cod]"), function (tr) {
      tr.addEventListener("click", function () { detalle(tr.getAttribute("data-cod")); });
    });
  }

  function detalle(codigo) {
    cont.innerHTML = '<div class="pcod-dim">Cargando ' + codigo + '…</div>';
    var ver = selVer.value ? parseInt(selVer.value, 10) : null;
    fetch("/api/partida/" + codigo + (ver != null ? "?version_id=" + ver : ""))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.error) { cont.innerHTML = '<div class="pcod-dim">' + esc(d.error) + "</div>"; return; }
        renderDetalle(d);
      })
      .catch(function () {
        /* MISIÓN VIII: fallback a los datos embebidos (misma forma de respuesta) */
        if (window.__pcodEstatico) {
          window.__pcodEstatico.partida(codigo, ver).then(function (d) {
            if (d.error) { cont.innerHTML = '<div class="pcod-dim">' + esc(d.error) + "</div>"; return; }
            renderDetalle(d);
          }).catch(function (e) {
            cont.innerHTML = '<div class="pcod-dim">Error al cargar la partida: ' +
              String(e && e.message || e) + "</div>";
          });
        } else {
          cont.innerHTML = '<div class="pcod-dim">Capa local PRECODI no disponible.</div>';
        }
      });
  }

  function renderDetalle(d) {
    var p = d.partida;
    var h = '<div class="pcod-h3">' + p.codigo + " · " + esc(p.descripcion) + "</div>";
    h += '<div><span class="pcod-tag">' + esc(p.catalogo) + " " + esc(p.version) + "</span>" +
      '<span class="pcod-tag">um: ' + esc(p.unidad || "?") + (p.factor_unidad && p.factor_unidad !== 1 ? " (×" + p.factor_unidad + ")" : "") + "</span>" +
      (p.capitulo ? '<span class="pcod-tag">cap. ' + esc(p.capitulo) + "</span>" : "") + "</div>";

    h += '<div class="pcod-box"><div class="pcod-prov">FUENTE: ' + esc(p.fuente_archivo || "") +
      "<br>SHA-256: " + esc((p.fuente_sha256 || "").slice(0, 32)) + "… · importada: " + esc(p.fecha_importacion || "") +
      "</div></div>";

    if (d.normas.length) {
      h += '<table class="pcod-tbl"><tr><th>Recurso</th><th>Coef.</th><th>Precio MN</th><th>Subtotal</th></tr>';
      d.normas.forEach(function (n) {
        var comps = (n.componentes || []).map(function (c) {
          return "· " + c.tipo_componente + " " + c.codigo_componente + " ×" + c.coeficiente +
            (c.precio_mn != null ? " (" + c.precio_mn.toFixed(4) + ")" : "");
        }).join(" ");
        h += "<tr><td><span class='pcod-tag'>" + n.tipo + "</span>" + esc(n.codigo_recurso) +
          " " + esc(n.recurso_desc || "(sin nomenclador)") +
          (comps ? '<div class="pcod-comp">' + comps + "</div>" : "") + "</td>" +
          '<td class="pcod-num">' + n.coeficiente + "</td>" +
          '<td class="pcod-num">' + (n.precio_mn == null ? "—" : n.precio_mn.toFixed(4)) + "</td>" +
          '<td class="pcod-num">' + n.subtotal.toFixed(4) + "</td></tr>";
      });
      h += "</table>";

      h += '<div class="pcod-box"><b>Subtotales por tipo (Σ coef×precio):</b><br>';
      Object.keys(d.subtotales).forEach(function (k) {
        h += esc(k) + ": <span class='pcod-num'>" + d.subtotales[k].toFixed(4) + "</span> &nbsp; ";
      });
      h += "</div>";

      h += '<div class="pcod-box"><b>Verificación contra la fuente:</b>';
      [["cmmn", "CMMN (materiales+juegos+semis)"], ["chmn", "CHMN (mano de obra)"],
       ["cemn", "CEMN (equipos)"]].forEach(function (par) {
        var v = d.verificacion[par[0]];
        if (!v) return;
        var cls = v.coincide ? "pcod-ok" : "pcod-dif";
        var sim = v.coincide ? "✓" : "Δ";
        h += '<div class="' + cls + '">' + sim + " " + par[1] + ": almacenado " + v.almacenado.toFixed(4) +
          " · recalculado " + v.recalculado.toFixed(4) + " (Δ " + v.delta.toFixed(4) + " ≤ tol " +
          v.tolerancia.toPrecision(3) + ")</div>";
      });
      h += '<div class="pcod-prov">' + esc(d.verificacion.regla) + "</div></div>";
    } else {
      h += '<div class="pcod-dim">Esta versión no contiene descomposición para la partida ' +
        '(el catálogo PRECOST 2025 embebido no trae normas; las normas están en las versiones PRECODI).</div>';
    }

    if (d.otras_versiones.length) {
      h += '<div class="pcod-box"><b>La misma partida en otras versiones:</b><br>';
      d.otras_versiones.forEach(function (o) {
        h += '<span class="pcod-tag">' + esc(o.catalogo) + " " + esc(o.version) + "</span> " +
          (o.costo_total_mn == null ? "—" : o.costo_total_mn.toFixed(2)) + " " + esc(o.unidad || "") + "<br>";
      });
      h += "</div>";
    }
    cont.innerHTML = h;
  }

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
})();
