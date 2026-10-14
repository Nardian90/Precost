/* ============================================================================
 * OVERLAY III-C — DESCOMPOSICIONES PRECODI EN LA PESTAÑA RECURSOS DEL EDITOR
 * ----------------------------------------------------------------------------
 * Script 100% ADITIVO (igual que overlay/precodi.js de III-B): lo inyecta el
 * servidor local al servir el HTML original; el archivo PRECOST-v9.17.html en
 * disco NO se modifica (SHA-256 verificado por request).
 *
 * Qué hace:
 *   - Amplía la pestaña Recursos del editor de presupuestos con la
 *     descomposición POR PARTIDA: partida → norma PRECODI → componentes
 *     (materiales, mano de obra, equipos, juegos, semielaborados) con
 *     coeficiente, precio, importe y fuente/versiones.
 *   - Si la partida pertenece al presupuesto: cantidad presupuestada editable
 *     (mecanismo existente de PRECOST), consumo = coef × cantidad, importes y
 *     subtotales reproducibles, y vínculo persistente (snapshot it.normaPreco
 *     guardado con el presupuesto en localStorage p3pro.budgets).
 *   - Selector de versión de normas y de fuente de precios (misma versión,
 *     otra versión PRECODI o PRECOST 2025 embebido) con informe de
 *     compatibilidad y advertencias explícitas. Nunca mezcla en silencio.
 *
 * Qué NO hace:
 *   - No modifica el catálogo embebido, las vistas existentes, el contrato
 *     PRECOST-AI-JSON ni los endpoints de III-B.
 *   - No sustituye el precio unitario del motor de PRECOST: la descomposición
 *     se muestra y compara, con su fuente, sin sobrescribir nada.
 *   - No actualiza retroactivamente presupuestos históricos: el snapshot es
 *     inmutable salvo acción explícita del usuario.
 * ==========================================================================*/
(function () {
  "use strict";
  if (window.__pcodRecursos) return;               // idempotente
  window.__pcodRecursos = true;

  /* ------------------------------------------------------------------ estilos */
  var CSS = [
    ".pcod2{margin:0 0 18px;border:1px solid var(--border,#d8dce6);border-radius:12px;padding:14px;background:var(--bg-card,#fff)}",
    ".pcod2 h2{margin:0 0 4px;font-size:var(--fs-l,17px);display:flex;gap:8px;align-items:center;flex-wrap:wrap}",
    ".pcod2 .pcod2-sub{color:var(--text-muted,#667);font-size:var(--fs-s,12.5px);margin:0 0 10px}",
    ".pcod2-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}",
    ".pcod2-bar select,.pcod2-bar input{min-height:34px;padding:4px 8px;border:1px solid var(--border,#c9cedb);border-radius:8px;background:var(--bg,#fff);color:inherit;font-size:13px}",
    ".pcod2-bar input{min-width:190px;flex:1}",
    ".pcod2-chip{display:inline-flex;gap:4px;align-items:center;border:1px solid var(--border,#c9cedb);border-radius:14px;",
    "padding:2px 10px;font-size:12px;cursor:pointer;user-select:none;background:var(--bg,#fff)}",
    ".pcod2-chip.pcod2-off{opacity:.45;text-decoration:line-through}",
    ".pcod2-head{display:flex;gap:8px;flex-wrap:wrap;align-items:baseline;margin:10px 0 2px}",
    ".pcod2-head b{font-size:15px}",
    ".pcod2-tag{display:inline-block;background:rgba(26,95,180,.1);color:var(--primary,#1a5fb4);border-radius:5px;padding:1px 7px;font-size:11.5px;margin:0 4px 4px 0}",
    ".pcod2-tag.pcod2-warn{background:rgba(224,154,0,.14);color:#9a6700}",
    ".pcod2-tag.pcod2-ok{background:rgba(46,160,67,.12);color:#1a7f37}",
    ".pcod2-tag.pcod2-dim{background:rgba(120,126,140,.12);color:#57606a}",
    ".pcod2-tbl{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0}",
    ".pcod2-tbl th{text-align:left;border-bottom:2px solid var(--border,#d8dce6);padding:4px 6px;white-space:nowrap}",
    ".pcod2-tbl td{border-bottom:1px solid var(--border-soft,#eceff4);padding:4px 6px;vertical-align:top}",
    ".pcod2-tbl td.num,.pcod2-tbl th.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}",
    ".pcod2-tbl tr.pcod2-comp{cursor:pointer}.pcod2-tbl tr.pcod2-comp:hover td{background:rgba(26,95,180,.05)}",
    ".pcod2-tbl tr.pcod2-det td{background:rgba(120,126,140,.05);font-size:12px;color:var(--text-muted,#667)}",
    ".pcod2-tbl tr.pcod2-hijo td{background:rgba(120,126,140,.06)}",
    ".pcod2-tbl .pcod2-code{font-family:ui-monospace,monospace;font-size:11.5px}",
    ".pcod2-box{border:1px solid var(--border,#d8dce6);border-radius:8px;padding:8px 11px;margin:8px 0;font-size:12.5px}",
    ".pcod2-box.pcod2-warnbox{border-color:#e0a000;background:rgba(224,154,0,.06)}",
    ".pcod2-box .pcod2-prov{font-size:11px;color:var(--text-muted,#667);word-break:break-all}",
    ".pcod2-mini{font-size:11px;color:var(--text-muted,#667)}",
    ".pcod2-cant{min-height:32px;padding:3px 6px;width:110px;border:1px solid var(--border,#c9cedb);border-radius:8px;font-variant-numeric:tabular-nums}",
    ".pcod2-tot td{font-weight:700;border-top:2px solid var(--border,#d8dce6)}",
    ".pcod2-res{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0}",
    ".pcod2-res .pcod2-vrow{border:1px solid var(--border,#d8dce6);border-radius:8px;padding:5px 9px;cursor:pointer;font-size:12.5px}",
    ".pcod2-res .pcod2-vrow:hover{background:rgba(26,95,180,.07)}"
  ].join("");
  var st = document.createElement("style");
  st.id = "pcod2-styles";
  st.textContent = CSS;
  document.head.appendChild(st);

  /* ------------------------------------------------------------------ estado */
  var S = {
    itemIdx: null,            // índice en b.items (modo presupuesto) o null (catálogo)
    codigo: null,             // código consultado
    versionId: null,          // versión de normas (default: 2017-raíz)
    precioVersionId: null,    // fuente de precios (default: = versionId)
    data: null,               // última respuesta de /api/descomposicion (o snapshot offline)
    offline: false,           // true = renderizado desde snapshot sin servidor
    servidorOk: null,
    versiones: [],            // catálogo de versiones (API)
    filtros: {},              // {tipo: bool}
    expandidos: {},           // {"tipo|codigo": bool} filas de detalle / juegos
    resultadosBusqueda: null
  };
  var TIPOS_ORDEN = ["material", "mano_obra", "equipo", "juego", "semielaborado"];
  var ETIQUETAS = {
    material: "Material", mano_obra: "Mano de obra", equipo: "Equipo",
    juego: "Juego", semielaborado: "Semielaborado"
  };

  /* ------------------------------------------------------- utilidades propias */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  /* coeficiente Float32: mostrar con 7 dígitos significativos (precisión
     float32) recortando ceros; el valor exacto se conserva en el atributo
     title y en el detalle. NUNCA se redondea el valor de cálculo. */
  function fmtCoef(v) {
    if (v == null) return "—";
    var t = parseFloat(Number(v).toPrecision(7));
    return String(t);
  }
  /* precios/importes Money 4 decimales: hasta 4 decimales, sin ceros finales
     superfluos; los totales de presentación usan 4 decimales fijos. */
  function fmtM(v, fijos) {
    if (v == null || isNaN(v)) return "—";
    if (fijos) return Number(v).toFixed(4);
    var t = parseFloat(Number(v).toFixed(4));
    return String(t);
  }
  function api(ruta) {
    return fetch(ruta).then(function (r) {
      if (!r.ok && r.status !== 404) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }
  /* etiqueta de versión ("PRECODI 2017-raíz") */
  function etiquetaVersion(v) { return (v.catalogo || "") + " " + (v.version || ""); }
  function etiquetaVersionPorId(id) {
    var v = S.versiones.filter(function (x) { return x.id === id; })[0];
    return v ? etiquetaVersion(v) : ("versión " + id);
  }

  /* ================================================================= RENDER */
  function render(b, r) {
    var host = document.getElementById("tab-recursos");
    if (!host) return;
    var sec = document.createElement("div");
    sec.className = "pcod2";
    sec.id = "pcod2-seccion";
    host.insertBefore(sec, host.firstChild);

    if (S.servidorOk === null) { sondearServidor(b, r); }
    var partidasPresupuesto = b ? b.items.map(function (it, i) {
      return { it: it, i: i };
    }).filter(function (x) { return x.it.tipo === "partida"; }) : [];

    var h = "";
    h += '<h2>' + (typeof ico === "function" ? ico("package") : "▤") +
      ' Descomposición por partida <span class="pcod2-tag">normas PRECODI</span></h2>';
    h += '<p class="pcod2-sub">Seleccione una partida del presupuesto o consulte el catálogo ' +
      'PRECODI importado para ver su norma de composición: recursos, coeficientes, precios, ' +
      'consumos y subtotales reproducibles. El precio unitario del presupuesto NO se modifica.</p>';

    /* --- barra de selección --- */
    h += '<div class="pcod2-bar">';
    h += '<select id="pcod2-sel" title="Partida del presupuesto actual">';
    h += '<option value="">— Partida del presupuesto… —</option>';
    partidasPresupuesto.forEach(function (x) {
      var sel = S.itemIdx === x.i ? " selected" : "";
      h += '<option value="' + x.i + '"' + sel + '>' + esc(x.it.codigo) + " · " +
        esc(String(x.it.descripcion || "").slice(0, 60)) +
        (x.it.normaPreco ? " ✓" : "") + '</option>';
    });
    h += '<option value="__cat__"' + (S.itemIdx === null && S.codigo ? " selected" : "") +
      '>— Consultar catálogo PRECODI… —</option>';
    h += '</select>';
    if (S.itemIdx === null) {
      h += '<input id="pcod2-q" placeholder="Código o descripción (catálogo PRECODI)" value="' +
        esc(S.q || "") + '">';
      h += '<button class="btn sm" id="pcod2-buscar">Buscar</button>';
    }
    if (S.servidorOk) {
      h += '<select id="pcod2-ver" title="Versión del catálogo PRECODI (normas)">';
      S.versiones.forEach(function (v) {
        if (!v.normas) return;
        h += '<option value="' + v.id + '"' + (v.id === S.versionId ? " selected" : "") + '>' +
          "Normas: " + esc(v.catalogo) + " " + esc(v.version) + '</option>';
      });
      h += '</select>';
      h += '<select id="pcod2-fuente" title="Fuente de los precios de los recursos">';
      h += '<option value="">Precios: misma versión</option>';
      S.versiones.forEach(function (v) {
        if (v.id === S.versionId || !v.recursos) return;
        h += '<option value="' + v.id + '"' + (v.id === S.precioVersionId ? " selected" : "") +
          '>Precios: ' + esc(v.catalogo) + " " + esc(v.version) + '</option>';
      });
      h += '</select>';
    }
    h += '</div>';

    /* --- aviso de servidor no disponible --- */
    if (S.servidorOk === false) {
      var haySnapshot = S.itemIdx != null && b && b.items[S.itemIdx] && b.items[S.itemIdx].normaPreco;
      h += '<div class="pcod2-box pcod2-warnbox"><b>Capa local PRECODI no disponible.</b> ' +
        (haySnapshot
          ? "Se muestra la descomposición vinculada a este presupuesto (snapshot guardado; no se pueden consultar otras partidas del catálogo hasta que se inicie <code>scripts/servidor_precodi.py</code>)."
          : "Para consultar descomposiciones del catálogo PRECODI, inicie el servidor local: <code>python3 scripts/servidor_precodi.py</code>. Las descomposiciones ya vinculadas a partidas del presupuesto se muestran desde su snapshot guardado.") +
        '</div>';
    }

    /* --- resultados de búsqueda de catálogo --- */
    if (S.itemIdx === null && S.resultadosBusqueda) {
      if (S.resultadosBusqueda.length) {
        h += '<div class="pcod2-res">' + S.resultadosBusqueda.map(function (p, j) {
          return '<span class="pcod2-vrow" data-pcod2res="' + j + '"><code class="pcod2-code">' +
            esc(p.codigo) + '</code> · ' + esc(String(p.descripcion).slice(0, 52)) +
            ' <i>(' + esc(p.unidad || "?") + ')</i></span>';
        }).join("") + '</div>';
      } else {
        h += '<div class="note">Sin resultados en el catálogo PRECODI para «' + esc(S.q || "") + '».</div>';
      }
    }

    /* --- detalle de la partida seleccionada --- */
    if (S.codigo) h += renderDetalle(b, r, partidasPresupuesto);

    sec.innerHTML = h;
    wire(b, r, sec);
  }

  /* --------------------------------------------------- detalle de la partida */
  function renderDetalle(b, r, partidasPresupuesto) {
    var d = S.data;
    if (!d) return '<div class="note">Cargando ' + esc(S.codigo) + '…</div>';
    if (d.error) {
      var vers = (d.versiones_disponibles || []).map(function (v) {
        return '<span class="pcod2-tag">' + esc(v.version) + '</span>';
      }).join("");
      return '<div class="pcod2-box pcod2-warnbox">' + esc(d.error) +
        (vers ? '<br>Versiones donde existe: ' + vers : "") + '</div>';
    }
    var p = d.partida;
    var enPresupuesto = S.itemIdx != null && b && b.items[S.itemIdx];
    var it = enPresupuesto ? b.items[S.itemIdx] : null;
    var cantidad = it ? (Number(it.cantidad) || 0) : null;

    var h = "";
    /* cabecera: código, descripción, unidad, fuente y versión */
    h += '<div class="pcod2-head"><b><code class="pcod2-code">' + esc(p.codigo) + '</code> ' +
      esc(p.descripcion) + '</b></div>';
    h += '<div>';
    h += '<span class="pcod2-tag">um: ' + esc(p.unidad || "?") +
      (p.factor_unidad && p.factor_unidad !== 1 ? " (×" + esc(p.factor_unidad) + ")" : "") + '</span>';
    h += '<span class="pcod2-tag' + (enPresupuesto ? ' pcod2-ok' : ' pcod2-dim') + '">' +
      (enPresupuesto ? "EN EL PRESUPUESTO" : "CONSULTA DE CATÁLOGO") + '</span>';
    h += '<span class="pcod2-tag">' + esc(p.catalogo) + " " + esc(p.version) + '</span>';
    if (d.fuentes_precio) {
      h += '<span class="pcod2-tag pcod2-warn">precios: ' +
        esc(d.fuentes_precio.version_precios.catalogo) + " " +
        esc(d.fuentes_precio.version_precios.version) + '</span>';
    }
    h += '</div>';
    h += '<div class="pcod2-mini">FUENTE: ' + esc(p.fuente_archivo || "") + ' · SHA-256 ' +
      esc(String(p.fuente_sha256 || "").slice(0, 16)) + '… · importada ' +
      esc(p.fecha_importacion || "?") + '</div>';

    /* partida sin norma */
    if (!d.tiene_norma) {
      h += '<div class="pcod2-box pcod2-warnbox">Esta partida <b>no tiene norma de composición</b> ' +
        'en la versión seleccionada (' + esc(p.version) + '). Se conservan sus datos de origen ' +
        '(precio unitario ' + fmtM(p.costo_total_mn, true) + ' MN/' + esc(p.unidad || "?") +
        '). No se inventan componentes.</div>';
      if ((d.otras_versiones || []).some(function (o) { return o.n_normas > 0; })) {
        h += '<div class="pcod2-mini">Otras versiones con norma: ' +
          d.otras_versiones.filter(function (o) { return o.n_normas > 0; }).map(function (o) {
            return '<button class="btn sm" data-pcod2ver="' + o.version_id + '">' +
              esc(o.catalogo) + " " + esc(o.version) + " (" + o.n_normas + ")</button>";
          }).join(" ") + '</div>';
      }
      return h;
    }

    /* cantidad presupuestada (modo presupuesto) */
    if (enPresupuesto) {
      h += '<div class="pcod2-bar"><span>Cantidad presupuestada (' + esc(it.um || p.unidad || "?") +
        '):</span> <input type="number" class="pcod2-cant" id="pcod2-cant" step="0.0001" min="0" value="' +
        (cantidad || 0) + '">' +
        '<span class="pcod2-mini">Se guarda con el presupuesto (mecanismo existente); ' +
        'recalcula consumos e importes. La norma no se modifica.</span></div>';
    } else if (b) {
      h += '<div class="pcod2-bar"><button class="btn sm primary" id="pcod2-add">+ Añadir esta partida al presupuesto</button>' +
        '<span class="pcod2-mini">Se añade con cantidad 1 y procedencia PRECODI; ajústela después.</span></div>';
    }

    /* advertencias */
    if ((d.advertencias || []).length) {
      h += '<div class="pcod2-box pcod2-warnbox"><b>Advertencias (' + d.advertencias.length + '):</b><ul>' +
        d.advertencias.map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") +
        '</ul><span class="pcod2-mini">Se conserva la información de origen; nada se descarta en silencio.</span></div>';
    }

    /* informe de compatibilidad de precios entre versiones */
    if (d.fuentes_precio) {
      var fp = d.fuentes_precio;
      h += '<div class="pcod2-box pcod2-warnbox"><b>Combinación de versiones:</b> normas de <b>' +
        esc(fp.version_normas.catalogo) + " " + esc(fp.version_normas.version) +
        '</b> con precios de <b>' + esc(fp.version_precios.catalogo) + " " +
        esc(fp.version_precios.version) + '</b>: ' + fp.resueltos + "/" + fp.total +
        " recursos con precio directo (" + fp.porcentaje + "%)." +
        (fp.sin_resolver.length
          ? " Para " + fp.sin_resolver.length + " recurso(s) se usa el precio propio de la versión de la norma (marcado «respaldo»): " +
            esc(fp.sin_resolver.join(", ")) + "."
          : "") +
        (fp.recursos_unidad_distinta.length
          ? " " + fp.recursos_unidad_distinta.length + " recurso(s) con unidad distinta entre versiones (ver detalle por fila)."
          : "") +
        ' <b>Verifique la compatibilidad de códigos, unidades y semántica antes de usar estos importes.</b></div>';
    }

    /* filtros por tipo (default: todos los tipos presentes activos; solo se
       respeta la desactivación explícita del usuario — evita heredar filtros
       entre partidas con distinta composición) */
    var comps = d.componentes || [];
    var tiposPresentes = TIPOS_ORDEN.filter(function (t) {
      return comps.some(function (c) { return c.tipo === t; });
    });
    h += '<div class="pcod2-bar">';
    tiposPresentes.forEach(function (t) {
      var n = comps.filter(function (c) { return c.tipo === t; }).length;
      h += '<span class="pcod2-chip' + (S.filtros[t] === false ? " pcod2-off" : "") + '" data-pcod2tipo="' + t + '">' +
        esc(ETIQUETAS[t] || t) + " (" + n + ")</span>";
    });
    h += '<span class="pcod2-chip" data-pcod2todo="1">' +
      (todosExpandidos(comps) ? "Contraer todo" : "Expandir todo") + '</span>';
    h += '</div>';

    /* tabla de componentes */
    var cols = 8 + (enPresupuesto ? 2 : 0);
    h += '<div class="tblwrap"><table class="pcod2-tbl"><thead><tr>' +
      "<th>Tipo</th><th>Código</th><th>Descripción</th><th>Um</th>" +
      '<th class="num">Coef.</th><th class="num">Precio MN</th><th class="num">Importe/um</th>' +
      (enPresupuesto
        ? '<th class="num">Consumo</th><th class="num">Importe total</th>' : "") +
      "<th>Fuente</th></tr></thead><tbody>";
    tiposPresentes.forEach(function (t) {
      if (S.filtros[t] === false) return;
      comps.filter(function (c) { return c.tipo === t; }).forEach(function (c) {
        h += filaComponente(c, enPresupuesto, cantidad, false);
        var clave = c.tipo + "|" + c.codigo;
        if (S.expandidos[clave]) h += filaDetalle(c, cantidad, cols, false);
        (c.hijos || []).forEach(function (hj) {
          h += filaComponente(hj, enPresupuesto, cantidad, true, c);
          if (S.expandidos[hj.tipo + "|" + hj.codigo + "|h"]) h += filaDetalle(hj, cantidad, cols, true, c);
        });
      });
    });
    /* subtotales por tipo */
    h += '<tr class="pcod2-tot"><td colspan="5">Subtotal materiales</td>' +
      '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.subtotales.material, true) + '</td><td colspan="2"></td></tr>';
    if (d.subtotales.mano_obra != null)
      h += '<tr class="pcod2-tot"><td colspan="5">Subtotal mano de obra</td>' +
        '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.subtotales.mano_obra, true) + '</td><td colspan="2"></td></tr>';
    if (d.subtotales.equipo != null)
      h += '<tr class="pcod2-tot"><td colspan="5">Subtotal equipos</td>' +
        '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.subtotales.equipo, true) + '</td><td colspan="2"></td></tr>';
    if (d.subtotales.juego != null)
      h += '<tr class="pcod2-tot"><td colspan="5">Subtotal juegos de trabajo</td>' +
        '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.subtotales.juego, true) + '</td><td colspan="2"></td></tr>';
    if (d.subtotales.semielaborado != null)
      h += '<tr class="pcod2-tot"><td colspan="5">Subtotal semielaborados</td>' +
        '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.subtotales.semielaborado, true) + '</td><td colspan="2"></td></tr>';
    h += '<tr class="pcod2-tot"><td colspan="5">TOTAL descomposición (Σ coef×precio, MN/' +
      esc(p.unidad || "?") + ')</td>' +
      '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.total, true) + '</td><td colspan="2"></td></tr>';
    if (enPresupuesto && cantidad != null)
      h += '<tr class="pcod2-tot"><td colspan="5">TOTAL para la obra (× cantidad ' + fmtCoef(cantidad) + ')</td>' +
        '<td class="num" colspan="' + (enPresupuesto ? 3 : 1) + '">' + fmtM(d.total * cantidad, true) + '</td><td colspan="2"></td></tr>';
    h += '</tbody></table></div>';
    h += '<div class="pcod2-mini">Importe/um = coeficiente × precio unitario · Consumo = coeficiente × cantidad presupuestada · ' +
      'Importe total = consumo × precio. Los componentes de juegos y semielaborados (filas indentadas) son ' +
      'informativos: los subtotales usan el precio del juego/semielaborado (modelo F1/F7/F8 verificado).</div>';

    /* verificación contra la fuente */
    if (d.verificacion) {
      h += '<div class="pcod2-box"><b>Verificación contra los costos almacenados en la fuente:</b>';
      [["cmmn", "Materiales (CMMN)"], ["chmn", "Mano de obra (CHMN)"], ["cemn", "Equipos (CEMN)"]]
        .forEach(function (par) {
          var v = d.verificacion[par[0]];
          if (!v) return;
          h += '<div>' + (v.coincide ? "✓" : "Δ") + " " + par[1] + ": almacenado " +
            fmtM(v.almacenado, true) + " · recalculado " + fmtM(v.recalculado, true) +
            " (Δ " + Number(v.delta).toFixed(6) + ")</div>";
        });
      h += '<div class="pcod2-mini">' + esc(d.verificacion.regla) + '</div></div>';
    }

    /* comparación con el PU del presupuesto (motor PRECOST) — nunca se sobrescribe */
    if (enPresupuesto && r && r.items && r.items[S.itemIdx] != null) {
      var rc = r.items[S.itemIdx];
      var dif = rc.precio - d.total;
      h += '<div class="pcod2-box"><b>Comparación con el precio unitario del presupuesto (motor PRECOST):</b><br>' +
        "PU del presupuesto: " + (typeof fmt === "function" ? fmt(rc.precio) : rc.precio) +
        " CUP (" + esc(rc.precioFuente || "?") + ", catálogo 2025 con ajustes A.H/A.E y flags M/H/E) · " +
        "PU descomposición PRECODI: " + fmtM(d.total, true) + " MN (" + esc(p.catalogo) + " " +
        esc(p.version) + (d.fuentes_precio ? " + precios " + esc(d.fuentes_precio.version_precios.version) : "") + ") · " +
        "diferencia " + fmtM(dif, true) + "." +
        '<div class="pcod2-mini">Son bases de precios de años distintos con reglas de ajuste propias: ' +
        'esta comparación es informativa. El PU del presupuesto NO se modifica al consultar la descomposición.</div></div>';
    }

    /* snapshot / persistencia */
    if (enPresupuesto && it) {
      if (it.normaPreco) {
        h += '<div class="pcod2-box"><b>Descomposición vinculada a este presupuesto</b> (snapshot ' +
          esc((it.normaPreco.vinculado || "").replace("T", " ").slice(0, 19)) + " · normas " +
          esc(it.normaPreco.version || "?") + ") — se guarda y recupera con el presupuesto; " +
          'los cambios de catálogo no la alteran retroactivamente. ' +
          '<button class="btn sm" id="pcod2-snap-upd">Actualizar snapshot con la vista actual</button> ' +
          '<button class="btn sm danger" id="pcod2-snap-del">Quitar vínculo</button></div>';
      } else {
        h += '<div class="pcod2-box pcod2-warnbox">Descomposición aún no vinculada al presupuesto: ' +
          'vincúlela para que persista al guardar y recargar. ' +
          '<button class="btn sm primary" id="pcod2-snap-add">Vincular al presupuesto</button></div>';
      }
    }

    /* la misma partida en otras versiones */
    if ((d.otras_versiones || []).length) {
      h += '<div class="pcod2-box"><b>La misma partida en otras versiones:</b><br>' +
        d.otras_versiones.map(function (o) {
          return '<button class="btn sm" data-pcod2ver="' + o.version_id + '" title="Consultar esta versión">' +
            esc(o.catalogo) + " " + esc(o.version) + '</button> ' +
            (o.n_normas ? o.n_normas + " normas · " : "sin normas · ") +
            (o.costo_total_mn == null ? "—" : fmtM(o.costo_total_mn, true)) + " MN · " + esc(o.unidad || "?");
        }).join("<br>") + '</div>';
    }

    /* traza de cálculo */
    h += '<div class="pcod2-box"><b>Traza de cálculo:</b> ' +
      'PU descomposición = Σ(coeficiente × precio unitario) por componente de primer nivel; ' +
      'consumo del recurso = coeficiente × cantidad presupuestada (' +
      (cantidad != null ? fmtCoef(cantidad) : "no aplica en consulta de catálogo") + "); " +
      'importe del recurso = consumo × precio unitario; subtotal por tipo = Σ importes; ' +
      'total de obra = cantidad × PU descomposición. Coeficientes importados con el valor Float32 ' +
      'exacto de la fuente; precios con 4 decimales exactos (Jet Currency). El redondeo mostrado es ' +
      'solo de presentación (4 decimales); el cálculo no redondea.</div>';

    return h;
  }

  function todosExpandidos(comps) {
    return comps.every(function (c) { return S.expandidos[c.tipo + "|" + c.codigo]; });
  }

  function filaComponente(c, enPresupuesto, cantidad, esHijo, padre) {
    var clave = c.tipo + "|" + c.codigo + (esHijo ? "|h" : "");
    var expandible = !esHijo && (c.hijos || []).length > 0;
    var consumo = enPresupuesto && cantidad != null && c.coeficiente != null
      ? c.coeficiente * cantidad : null;
    var importeTotal = consumo != null && c.precio_mn != null ? consumo * c.precio_mn : null;
    var marca = expandible ? (S.expandidos[c.tipo + "|" + c.codigo] ? "▾ " : "▸ ") : "";
    var fuente = [];
    if (c.precio_respaldo) fuente.push('<span class="pcod2-tag pcod2-warn" title="Sin precio en la versión de precios seleccionada: se usa el precio de la versión de la norma">respaldo</span>');
    if (c.advertencia) fuente.push('<span class="pcod2-tag pcod2-warn" title="' + esc(c.advertencia) + '">⚠</span>');
    if (!c.resuelto) fuente.push('<span class="pcod2-tag pcod2-warn">sin nomenclador</span>');
    if (!esHijo) fuente.push('<span class="pcod2-tag pcod2-dim">' + esc(ETIQUETAS[c.tipo] || c.tipo) + '</span>');
    return '<tr class="pcod2-comp' + (esHijo ? " pcod2-hijo" : "") + '" data-pcod2clave="' + esc(clave) + '"' +
      (expandible ? ' title="Ampliar/contraer' + ((c.hijos || []).length ? " componentes del juego/semielaborado y detalle" : " detalle") + '"' : ' title="Ver detalle"') + '>' +
      "<td>" + marca + esc(esHijo ? "↳ " + (ETIQUETAS[c.tipo] || c.tipo) : (ETIQUETAS[c.tipo] || c.tipo)) + "</td>" +
      '<td><code class="pcod2-code">' + esc(c.codigo) + "</code></td>" +
      "<td>" + esc(c.descripcion || "(sin nomenclador — referencia de origen)") +
      (c.cod_norma && c.cod_norma !== "S/C" ? ' <span class="pcod2-mini">norma ' + esc(c.cod_norma) + "</span>" : "") + "</td>" +
      "<td>" + esc(c.unidad || "?") + "</td>" +
      '<td class="num" title="Valor importado exacto: ' + esc(String(c.coeficiente)) + '">' + fmtCoef(c.coeficiente) + "</td>" +
      '<td class="num">' + fmtM(c.precio_mn) + "</td>" +
      '<td class="num">' + fmtM(c.importe, true) + "</td>" +
      (enPresupuesto
        ? '<td class="num">' + (consumo == null ? "—" : fmtM(consumo, true)) + "</td>" +
          '<td class="num">' + (importeTotal == null ? "—" : fmtM(importeTotal, true)) + "</td>"
        : "") +
      "<td>" + fuente.join("") + "</td></tr>";
  }

  function filaDetalle(c, cantidad, cols, esHijo, padre) {
    var consumo = cantidad != null && c.coeficiente != null ? c.coeficiente * cantidad : null;
    var compuesto = esHijo && padre && padre.coeficiente != null
      ? padre.coeficiente * c.coeficiente : null;
    var t = "<b>Detalle:</b> " + esc(ETIQUETAS[c.tipo] || c.tipo) + " " + esc(c.codigo) +
      " · " + esc(c.descripcion || "(referencia sin nomenclador)") +
      " · um " + esc(c.unidad || "?") +
      " · coef exacto " + esc(String(c.coeficiente)) +
      (c.um_norma ? " · um norma " + esc(c.um_norma) : "") +
      (c.cod_norma && c.cod_norma !== "S/C" ? " · código norma " + esc(c.cod_norma) : "") +
      " · precio " + fmtM(c.precio_mn, true) + " MN";
    if (c.advertencia) t += " · <b>advertencia:</b> " + esc(c.advertencia);
    if (compuesto != null) t += " · coeficiente compuesto por um de partida = coef juego (" +
      fmtCoef(padre.coeficiente) + ") × coef componente (" + fmtCoef(c.coeficiente) + ") = " + fmtCoef(compuesto);
    if (consumo != null) t += " · consumo para la obra = " + fmtCoef(c.coeficiente) + " × " +
      fmtCoef(cantidad) + " = " + fmtM(consumo, true);
    if (consumo != null && c.precio_mn != null) t += " · importe = " + fmtM(consumo * c.precio_mn, true);
    return '<tr class="pcod2-det"><td colspan="' + cols + '">' + t + "</td></tr>";
  }

  /* ============================================================== EVENTOS */
  function wire(b, r, sec) {
    var $ = function (sel) { return sec.querySelector(sel); };

    var sel = $("#pcod2-sel");
    if (sel) sel.addEventListener("change", function () {
      S.resultadosBusqueda = null;
      if (sel.value === "__cat__") { S.itemIdx = null; }
      else if (sel.value === "") { S.itemIdx = null; S.codigo = null; S.data = null; }
      else {
        S.itemIdx = parseInt(sel.value, 10);
        S.codigo = b.items[S.itemIdx].codigo;
        cargar(b);
      }
      render(b, r);
    });

    var q = $("#pcod2-q"), bBuscar = $("#pcod2-buscar");
    function buscarCatalogo() {
      var t = (q ? q.value : "").trim();
      if (!t) return;
      S.q = t;
      api("/api/partidas?q=" + encodeURIComponent(t) + "&version_id=" + S.versionId + "&limit=25")
        .then(function (d) {
          S.resultadosBusqueda = d.resultados || [];
          render(b, r);
        })
        .catch(function () { S.resultadosBusqueda = []; render(b, r); });
    }
    if (bBuscar) bBuscar.addEventListener("click", buscarCatalogo);
    if (q) q.addEventListener("keydown", function (e) { if (e.key === "Enter") buscarCatalogo(); });

    sec.querySelectorAll("[data-pcod2res]").forEach(function (el) {
      el.addEventListener("click", function () {
        var p = S.resultadosBusqueda[parseInt(el.getAttribute("data-pcod2res"), 10)];
        if (!p) return;
        S.itemIdx = null; S.codigo = p.codigo; S.data = null;
        cargar(b); render(b, r);
      });
    });

    var ver = $("#pcod2-ver");
    if (ver) ver.addEventListener("change", function () {
      S.versionId = parseInt(ver.value, 10);
      S.precioVersionId = S.versionId;      // al cambiar de normas, precios de la misma versión
      S.filtros = {}; S.expandidos = {};
      if (S.codigo) cargar(b);
      render(b, r);
    });
    var fuente = $("#pcod2-fuente");
    if (fuente) fuente.addEventListener("change", function () {
      S.precioVersionId = fuente.value ? parseInt(fuente.value, 10) : S.versionId;
      if (S.codigo) cargar(b);
      render(b, r);
    });

    var cant = $("#pcod2-cant");
    if (cant) cant.addEventListener("change", function () {
      if (S.itemIdx == null || !b) return;
      /* MECANISMO EXISTENTE de PRECOST (idéntico al handler data-qidx de la
         pestaña Partidas): actualizar cantidad → touch → recálculo completo. */
      b.items[S.itemIdx].cantidad = Math.max(0, Number(cant.value) || 0);
      if (typeof touch === "function") touch(b);
      if (typeof renderEditor === "function") renderEditor();
    });

    var add = $("#pcod2-add");
    if (add) add.addEventListener("click", function () {
      if (!b || !S.data || !S.data.partida) return;
      var p = S.data.partida;
      /* mismo patrón que abrirBuscadorPartidas(), con procedencia PRECODI */
      b.items.push({
        codigo: p.codigo, descripcion: p.descripcion, um: p.unidad || "u",
        tipo: "partida", flags: "MHE", cantidad: 1,
        precio: (typeof DB !== "undefined" && DB.P && DB.P[p.codigo]) ? null : (p.costo_total_mn != null ? p.costo_total_mn : 0),
        coef: 1, capitulo: p.capitulo || "", subcapitulo: String(p.codigo).slice(0, 4),
        src: { fuente: "precodi", catalogo: p.catalogo, version: p.version, sha256: p.fuente_sha256 }
      });
      if (typeof touch === "function") touch(b);
      if (typeof toast === "function") toast("➕ " + p.codigo + " añadida (procedencia PRECODI " + p.version + ")");
      S.itemIdx = b.items.length - 1;
      if (typeof renderEditor === "function") renderEditor();
    });

    sec.querySelectorAll("[data-pcod2tipo]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var t = chip.getAttribute("data-pcod2tipo");
        S.filtros[t] = !S.filtros[t];
        render(b, r);
      });
    });
    var todo = sec.querySelector("[data-pcod2todo]");
    if (todo) todo.addEventListener("click", function () {
      var comps = (S.data && S.data.componentes) || [];
      var expandir = !todosExpandidos(comps);
      comps.forEach(function (c) { S.expandidos[c.tipo + "|" + c.codigo] = expandir; });
      render(b, r);
    });
    sec.querySelectorAll("[data-pcod2clave]").forEach(function (tr) {
      tr.addEventListener("click", function () {
        var clave = tr.getAttribute("data-pcod2clave");
        var esHijo = clave.endsWith("|h");
        S.expandidos[clave] = !S.expandidos[clave];
        render(b, r);
      });
    });
    sec.querySelectorAll("[data-pcod2ver]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        S.versionId = parseInt(btn.getAttribute("data-pcod2ver"), 10);
        S.precioVersionId = S.versionId;
        S.filtros = {}; S.expandidos = {};
        if (S.codigo) cargar(b);
        render(b, r);
      });
    });

    var snapAdd = $("#pcod2-snap-add"), snapUpd = $("#pcod2-snap-upd"), snapDel = $("#pcod2-snap-del");
    if (snapAdd) snapAdd.addEventListener("click", function () { vincular(b, r); });
    if (snapUpd) snapUpd.addEventListener("click", function () { vincular(b, r); });
    if (snapDel) snapDel.addEventListener("click", function () {
      if (S.itemIdx == null || !b) return;
      delete b.items[S.itemIdx].normaPreco;
      if (typeof touch === "function") touch(b);
      if (typeof toast === "function") toast("Descomposición desvinculada del presupuesto");
      if (typeof renderEditor === "function") renderEditor();
    });
  }

  function vincular(b, r) {
    if (S.itemIdx == null || !b || !S.data || !S.data.partida) return;
    var d = S.data;
    b.items[S.itemIdx].normaPreco = {
      vinculado: new Date().toISOString(),
      version_id: d.partida.version_id, version: d.partida.version,
      catalogo: d.partida.catalogo,
      fuente_archivo: d.partida.fuente_archivo, fuente_sha256: d.partida.fuente_sha256,
      fecha_importacion: d.partida.fecha_importacion,
      precio_version_id: S.precioVersionId,
      partida: {
        codigo: d.partida.codigo, descripcion: d.partida.descripcion,
        unidad: d.partida.unidad, costo_total_mn: d.partida.costo_total_mn
      },
      componentes: d.componentes, subtotales: d.subtotales, total: d.total,
      verificacion: d.verificacion, duplicados: d.duplicados,
      advertencias: d.advertencias, fuentes_precio: d.fuentes_precio
    };
    if (typeof touch === "function") touch(b);
    if (typeof toast === "function") toast("✓ Descomposición vinculada al presupuesto (se guarda con él)");
    if (typeof renderEditor === "function") renderEditor();
  }

  /* ================================================================ DATOS */
  function sondearServidor(b, r) {
    api("/api/versiones").then(function (d) {
      S.servidorOk = true;
      S.versiones = d.versiones || [];
      if (!S.versionId) {
        /* preferencia documentada: 2017-raíz > 2011-sbd2008 > 2007-v7.22 > v7.21 */
        var conNormas = S.versiones.filter(function (v) { return v.normas > 0; });
        var orden = ["2017-raiz", "2011-sbd2008", "2007-v7.22", "2007-v7.21"];
        var elegida = null;
        for (var i = 0; i < orden.length && !elegida; i++) {
          conNormas.forEach(function (v) { if (v.version === orden[i] && !elegida) elegida = v; });
        }
        if (!elegida && conNormas.length) elegida = conNormas[conNormas.length - 1];
        S.versionId = elegida ? elegida.id : null;
        S.precioVersionId = S.versionId;
      }
      render(b, r);
    }).catch(function () {
      S.servidorOk = false;
      render(b, r);
    });
  }

  function cargar(b) {
    if (!S.codigo) return;
    /* sin servidor: degradar a snapshot si existe */
    if (S.servidorOk === false) {
      S.data = (S.itemIdx != null && b && b.items[S.itemIdx]) ? b.items[S.itemIdx].normaPreco : null;
      S.offline = true;
      return;
    }
    var url = "/api/descomposicion/" + encodeURIComponent(S.codigo) +
      "?version_id=" + S.versionId +
      (S.precioVersionId && S.precioVersionId !== S.versionId
        ? "&precio_version_id=" + S.precioVersionId : "");
    S.offline = false;
    api(url).then(function (d) {
      if (d.error) { S.data = d; renderSiEditor(); return; }
      S.data = d;
      /* vínculo automático la primera vez que se consulta una partida del
         presupuesto (persistencia por defecto; inmutable salvo acción explícita) */
      if (S.itemIdx != null && b && b.items[S.itemIdx] && !b.items[S.itemIdx].normaPreco) {
        vincular(b, null);
      } else {
        renderSiEditor();
      }
    }).catch(function (e) {
      S.servidorOk = false;
      S.data = (S.itemIdx != null && b && b.items[S.itemIdx]) ? b.items[S.itemIdx].normaPreco : null;
      S.offline = true;
      renderSiEditor();
    });
  }

  function renderSiEditor() {
    if (typeof renderEditor === "function" &&
        typeof state !== "undefined" && state.view === "editor") {
      renderEditor();
    }
  }

  /* ============================================================ INTEGRACIÓN */
  /* Amplía renderTabRecursos de PRECOST en tiempo de ejecución: la función
     original se ejecuta íntegra (su contenido permanece) y luego se antepone
     esta sección. El archivo HTML en disco no se modifica. */
  if (typeof window.renderTabRecursos === "function") {
    var _original = window.renderTabRecursos;
    window.renderTabRecursos = function (b, r) {
      _original(b, r);
      try { render(b, r); }
      catch (e) { /* la pestaña original ya está renderizada: nunca romper PRECOST */ }
    };
    /* si la app arranca directamente en el editor, repintar para incluir la sección */
    if (typeof state !== "undefined" && state.view === "editor" &&
        typeof renderEditor === "function") {
      setTimeout(function () {
        try { renderEditor(); } catch (e) { /* noop */ }
      }, 300);
    }
  }
})();
