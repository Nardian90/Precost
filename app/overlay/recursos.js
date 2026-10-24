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
 * MISIÓN V (S-050 + S-052, MATRIZ_PARIDAD §M5, manual págs. 32–35):
 *   - S-050 Indicadores M/H/E por A.C. y especificación: barra de palomitas
 *     M/H/E ligada al mecanismo EXISTENTE it.flags (mismo campo que edita el
 *     selector de la pestaña Partidas — sin modelo duplicado). Quitar una
 *     palomita desactiva los recursos de la norma de esa familia y activa
 *     «especificar recursos» de esa familia; reponerla descarta lo especificado
 *     y vuelve a la norma (confirmación explícita si hay datos que perder).
 *   - S-052 Cargar normas por defecto y modificar cantidad/precio: las
 *     descomposiciones de partidas DEL PRESUPUESTO se vuelven editables.
 *     Toda edición vive en it.edicionRecursos (capa propia del presupuesto,
 *     guardada con él vía touch()/saveBudgets — p3pro.budgets) y JAMÁS toca
 *     la norma (snapshot normaPreco intacto), el catálogo embebido ni la BD.
 *     Recalcula importe=coef×precio, subtotales por tipo, total y total de
 *     obra (×cantidad) con precisión completa; cada cambio muestra original
 *     → editado y es reversible por fila, por familia o en bloque.
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
    ".pcod2-res .pcod2-vrow:hover{background:rgba(26,95,180,.07)}",
    /* ---- MISIÓN V: edición de recursos (S-050/S-052) ---- */
    ".pcod2-flg{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--border,#c9cedb);border-radius:8px;",
    "padding:3px 10px;font-size:12.5px;cursor:pointer;user-select:none;background:var(--bg,#fff)}",
    ".pcod2-flg b{display:inline-flex;width:15px;height:15px;align-items:center;justify-content:center;",
    "border:1.5px solid #9aa2b1;border-radius:3.5px;margin-right:5px;font-size:10px;color:transparent;flex:none}",
    ".pcod2-flg.pcod2-on{border-color:var(--primary,#1a5fb4)}",
    ".pcod2-flg.pcod2-on b{background:var(--primary,#1a5fb4);border-color:var(--primary,#1a5fb4);color:#fff}",
    ".pcod2-flg.pcod2-esp{background:rgba(220,38,38,.06);border-color:#d33}",   /* sombreado «especificado» (manual pág. 35) */
    ".pcod2-flg.pcod2-esp b{border-color:#d33}",
    ".pcod2-in{min-height:28px;width:94px;border:1px solid var(--border,#c9cedb);border-radius:7px;text-align:right;",
    "font-variant-numeric:tabular-nums;padding:2px 6px;background:var(--bg,#fff);color:inherit;font-size:12px}",
    ".pcod2-in.pcod2-bad{border-color:#d33;background:rgba(221,51,51,.08)}",
    ".pcod2-tbl tr.pcod2-des td{opacity:.55}",
    ".pcod2-tbl tr.pcod2-des .pcod2-tach{text-decoration:line-through}",
    ".pcod2-tbl tr.pcod2-prop td{background:rgba(220,38,38,.05)}",
    ".pcod2-tbl .pcod2-acc{white-space:nowrap}",
    ".pcod2-tag.pcod2-edit{background:rgba(224,154,0,.18);color:#9a6700}",
    ".pcod2-tag.pcod2-propio{background:rgba(220,38,38,.12);color:#b3261e}",
    ".pcod2-tag.pcod2-des{background:rgba(120,126,140,.15);color:#57606a}",
    ".pcod2-act{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}",
    ".pcod2-mods{margin:6px 0 0;padding-left:18px}",
    ".pcod2-mods li{margin:2px 0}",
    ".pcod2-recrow{display:flex;gap:8px;align-items:baseline;border-bottom:1px dashed var(--border-soft,#eceff4);padding:5px 2px;cursor:pointer}",
    ".pcod2-recrow:hover{background:rgba(26,95,180,.05)}",
    ".pcod2-man{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:10px}",
    ".pcod2-man input,.pcod2-man select{min-height:32px;padding:4px 8px;border:1px solid var(--border,#c9cedb);border-radius:8px;background:var(--bg,#fff);color:inherit;font-size:12.5px}",
    ".pcod2-flgbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0 2px}"
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
    estatico: false,          // MISIÓN VIII: true = datos embebidos de la web (dist/data)
    versiones: [],            // catálogo de versiones (API)
    filtros: {},              // {tipo: bool}
    expandidos: {},           // {"tipo|codigo": bool} filas de detalle / juegos
    resultadosBusqueda: null,
    /* MISIÓN V (transitorio, solo UI — la edición persistente vive en
       it.edicionRecursos dentro del presupuesto, p3pro.budgets): */
    panelRec: null,           // "M"|"H"|"E" — panel «añadir recurso» abierto
    busqRec: null,            // {letra, q, tipo, resultados, error} del panel
    sinNormas: false          // true = la BD no tiene versiones con normas (regeneración parcial)
  };
  var TIPOS_ORDEN = ["material", "mano_obra", "equipo", "juego", "semielaborado"];
  var ETIQUETAS = {
    material: "Material", mano_obra: "Mano de obra", equipo: "Equipo",
    juego: "Juego", semielaborado: "Semielaborado"
  };
  /* MISIÓN V — familias de recursos por indicador M/H/E (SIECONS: M incluye
     materiales, juegos y semielaborados — igual que el motor PRECOST, que
     suma juegos+semis en el costo de materiales CMMN; verificación III-C). */
  var FAMILIAS = {
    M: { nombre: "Materiales", largo: "Recursos Materiales", tipos: ["material", "juego", "semielaborado"] },
    H: { nombre: "R. Humanos", largo: "Recursos Humanos", tipos: ["mano_obra"] },
    E: { nombre: "Equipos", largo: "Equipos", tipos: ["equipo"] }
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

  /* ==================================================================== */
  /* MISIÓN V — S-050/S-052: edición de recursos en el presupuesto          */
  /* ==================================================================== */

  /* flags M/H/E canónicos (orden M,H,E). Reutiliza el campo EXISTENTE
     it.flags — el mismo que edita el selector data-flg de la pestaña
     Partidas y el que consume el motor (ENGINE.partidaPrecio): sin modelo
     duplicado. Presupuestos antiguos sin flags → "MHE" (defecto PRECOST). */
  function flagsDe(it) {
    var f = String((it && it.flags) || "MHE").toUpperCase();
    var out = "";
    ["M", "H", "E"].forEach(function (l) { if (f.indexOf(l) >= 0) out += l; });
    return out;
  }
  function familiaDeTipo(t) {
    if (t === "mano_obra") return "H";
    if (t === "equipo") return "E";
    return "M";                       // material, juego, semielaborado
  }
  function claveRecurso(tipo, codigo) { return tipo + "|" + String(codigo); }

  /* capa de edición del ítem (persistente en el presupuesto). Presupuestos
     antiguos (pre-Misión V) no la traen: se crea al primer gesto de edición
     y desde entonces se guarda y recupera con el presupuesto. */
  function edicionDe(it) { return (it && it.edicionRecursos) || null; }

  function asegurarEdicion(it) {
    if (!it) return null;
    if (!it.edicionRecursos) {
      var d = (S.data && !S.data.error) ? S.data : null;
      var snap = it.normaPreco || null;
      it.edicionRecursos = {
        creado: new Date().toISOString(),
        actualizado: null,
        version_id: (snap && snap.version_id) || (d && d.partida ? d.partida.version_id : null) || S.versionId,
        version: (snap && snap.version) || (d && d.partida ? d.partida.version : null) || null,
        catalogo: (snap && snap.catalogo) || (d && d.partida ? d.partida.catalogo : null) || null,
        precio_version_id: S.precioVersionId || null,
        cambios: {},    /* "tipo|codigo" → { coef?, precio? } — S-052 sobre la norma */
        propios: {}     /* tipo → [recurso] — S-050 especificación */
      };
    }
    return it.edicionRecursos;
  }

  /* Descomposición EFECTIVA del ítem (S-052). Base = vista viva (S.data) o
     snapshot; aplica: (1) indicadores M/H/E — filas de la norma de una familia
     sin palomita quedan desactivadas y excluidas; (2) ediciones (cambios) sobre
     filas de la norma; (3) recursos propios de familias sin palomita.
     NUNCA redondea: importe = coef × precio en doble precisión; la presentación
     a 4 decimales es solo visual. Filas «sin precio» quedan excluidas con
     aviso explícito (no se inventa ningún valor). */
  function descompEfectiva(it) {
    var d = (S.data && !S.data.error && S.data.componentes) ? S.data
          : (it && it.normaPreco && it.normaPreco.componentes ? it.normaPreco : null);
    var ed = edicionDe(it);
    var fl = flagsDe(it);
    var cantidad = it ? (Number(it.cantidad) || 0) : 0;
    var out = { filas: [], subtotales: {}, total: 0, totalObra: 0, tieneNorma: !!(d && (d.componentes || []).length) };
    (d && d.componentes ? d.componentes : []).forEach(function (c) {
      var fam = familiaDeTipo(c.tipo);
      var activo = fl.indexOf(fam) >= 0;
      var k = claveRecurso(c.tipo, c.codigo);
      var cam = (ed && ed.cambios && ed.cambios[k]) || null;
      var editado = !!(cam && (cam.coef != null || cam.precio != null));
      var fila = {
        origen: "norma", estado: activo ? (editado ? "editada" : "norma") : "desactivada",
        tipo: c.tipo, codigo: c.codigo, descripcion: c.descripcion, um: c.unidad,
        coefOriginal: c.coeficiente, precioOriginal: c.precio_mn,
        coef: (cam && cam.coef != null) ? cam.coef : c.coeficiente,
        precio: (cam && cam.precio != null) ? cam.precio : c.precio_mn,
        hijos: c.hijos || [], advertencia: c.advertencia,
        precio_respaldo: c.precio_respaldo, resuelto: c.resuelto
      };
      out.filas.push(fila);
    });
    if (ed && ed.propios) {
      Object.keys(ed.propios).forEach(function (tipo) {
        var fam = familiaDeTipo(tipo);
        (ed.propios[tipo] || []).forEach(function (p, j) {
          out.filas.push({
            origen: "propio",
            /* palomita repuesta con propios residuales (no debería ocurrir por
               UI; estado explícito y exclusión con aviso — nunca en silencio) */
            estado: fl.indexOf(fam) >= 0 ? "ignorado" : (p.precio == null ? "sin-precio" : "propio"),
            tipo: tipo, codigo: p.codigo, descripcion: p.descripcion, um: p.unidad,
            coefOriginal: null, precioOriginal: null,
            coef: p.coef, precio: p.precio, hijos: [],
            origenDetalle: p.origen, agregado: p.agregado, idx: j
          });
        });
      });
    }
    out.filas.forEach(function (f) {
      if (f.estado !== "norma" && f.estado !== "editada" && f.estado !== "propio") return;
      if (f.coef == null || f.precio == null) { f.importe = null; return; }  // sin precio: exclusión explícita
      f.importe = f.coef * f.precio;
      f.consumo = f.coef * cantidad;
      f.importeTotal = f.consumo * f.precio;
      out.subtotales[f.tipo] = (out.subtotales[f.tipo] || 0) + f.importe;
      out.total += f.importe;
    });
    out.totalObra = out.total * cantidad;
    return out;
  }

  /* validación de entrada numérica (rechaza negativos, no numéricos, vacíos) */
  function validarNum(txt) {
    if (txt == null || String(txt).trim() === "") return { ok: false, motivo: "vacío" };
    var n = Number(String(txt).replace(",", "."));
    if (!isFinite(n)) return { ok: false, motivo: "no numérico" };
    if (n < 0) return { ok: false, motivo: "negativo" };
    return { ok: true, v: n };
  }
  function confirmarDestructivo(msg) {
    /* confirm() nativo (mismo mecanismo que PRECOST usa en sus acciones
       destructivas, p. ej. sobrescribir plantilla); nada custom que rompa. */
    return typeof confirm === "function" ? confirm(msg) : true;
  }
  function toastO(msg) {
    if (typeof toast === "function") toast(msg);
  }
  function guardarYRefrescar(b) {
    if (typeof touch === "function") touch(b);          /* mecanismo EXISTENTE → saveBudgets → p3pro.budgets */
    if (typeof renderEditor === "function") renderEditor();
  }

  /* base de la descomposición para un ítem: vista viva (S.data) si es válida,
     si no el snapshot vinculado (it.normaPreco), si no vacío. */
  function compsBase(it) {
    var d = (S.data && !S.data.error && S.data.componentes) ? S.data
          : (it && it.normaPreco && it.normaPreco.componentes ? it.normaPreco : null);
    return (d && d.componentes) ? d.componentes : [];
  }

  /* ---- acciones S-050: palomitas M/H/E ---- */
  function toggleFlag(b, it, letra) {
    if (!b || !it || it.tipo !== "partida") return;
    var f = flagsDe(it);
    var vaAActivar = f.indexOf(letra) < 0;
    var fam = FAMILIAS[letra];
    var ed = edicionDe(it);
    if (vaAActivar && ed && ed.propios) {
      var n = 0;
      fam.tipos.forEach(function (t) { n += (ed.propios[t] || []).length; });
      if (n > 0 && !confirmarDestructivo(
          "Al reponer la palomita " + letra + " (" + fam.largo + ") se descartan los " + n +
          " recurso(s) especificado(s) y se vuelve a la norma (manual SIECONS pág. 35). ¿Continuar?")) return;
      fam.tipos.forEach(function (t) { if (ed.propios) delete ed.propios[t]; });
    }
    var nf = "";
    ["M", "H", "E"].forEach(function (l) {
      if (l === letra ? vaAActivar : f.indexOf(l) >= 0) nf += l;
    });
    it.flags = nf;
    guardarYRefrescar(b);
    toastO(vaAActivar ? ("✓ " + letra + " reactivada — vuelve a la norma (" + nf + ")")
                      : (letra + " desactivada — puede especificar " + fam.nombre.toLowerCase() + " propios (" + nf + ")"));
  }

  /* ---- acciones S-052: edición de filas de la norma ---- */
  function aplicarCambioNorma(b, it, inp) {
    var spec = String(inp.getAttribute("data-pcod2ed")).split("|");
    var campo = spec.pop();
    var tipo = spec.shift();
    var codigo = spec.join("|");
    var k = claveRecurso(tipo, codigo);
    var ed = asegurarEdicion(it);
    var fila = descompEfectiva(it).filas.filter(function (f) {
      return f.origen === "norma" && f.tipo === tipo && f.codigo === codigo;
    })[0] || null;
    var original = fila ? (campo === "coef" ? fila.coefOriginal : fila.precioOriginal) : null;
    var val = validarNum(inp.value);
    if (!val.ok) {
      toastO("⚠ Valor inválido (" + val.motivo + ") en " + tipo + " " + codigo +
             " — se conserva el valor anterior. Requiere un número ≥ 0 (o ↺ para revertir).");
      guardarYRefrescar(b);            // re-render restaura el input al último valor válido
      return;
    }
    if (val.v === original) {          // vuelve al valor de la norma: quitar la edición
      if (ed.cambios[k]) {
        delete ed.cambios[k][campo];
        if (ed.cambios[k].coef == null && ed.cambios[k].precio == null) delete ed.cambios[k];
      }
    } else {
      ed.cambios[k] = ed.cambios[k] || {};
      ed.cambios[k][campo] = val.v;
    }
    ed.actualizado = new Date().toISOString();
    guardarYRefrescar(b);
  }
  function revertirCambioNorma(b, it, specStr) {
    var spec = String(specStr).split("|");
    var tipo = spec.shift();
    var codigo = spec.join("|");
    var ed = edicionDe(it);
    if (ed && ed.cambios) delete ed.cambios[claveRecurso(tipo, codigo)];
    if (ed) ed.actualizado = new Date().toISOString();
    guardarYRefrescar(b);
    toastO("↺ " + tipo + " " + codigo + " restaurado al valor de la norma");
  }

  /* ---- acciones S-050: recursos propios (especificación) ---- */
  function cargarNormasFamilia(b, it, letra) {
    var fam = FAMILIAS[letra];
    var ed = asegurarEdicion(it);
    var eff = descompEfectiva(it);
    var fl = flagsDe(it);
    var anyadidos = 0, ya = 0;
    eff.filas.forEach(function (f) {
      if (f.origen !== "norma" || fam.tipos.indexOf(f.tipo) < 0) return;
      /* guardia anti-doble-cuento: solo se copian filas de familias SIN
         palomita (con palomita la fila de la norma sigue activa y ya cuenta) */
      if (fl.indexOf(familiaDeTipo(f.tipo)) >= 0) return;
      var arr = ed.propios[f.tipo] = ed.propios[f.tipo] || [];
      if (arr.some(function (p) { return p.codigo === f.codigo; })) { ya++; return; }
      arr.push({
        tipo: f.tipo, codigo: f.codigo, descripcion: f.descripcion, um: f.um,
        /* se copia el valor EFECTIVO (con ediciones) como punto de partida
           editable — manual pág. 34; el original queda en la fila de la norma */
        coef: f.coef, precio: f.precio, origen: "norma", agregado: new Date().toISOString()
      });
      anyadidos++;
    });
    ed.actualizado = new Date().toISOString();
    guardarYRefrescar(b);
    toastO(anyadidos ? ("⤓ " + anyadidos + " recurso(s) de la norma cargado(s) en " + fam.nombre.toLowerCase() +
           " (editable; la norma no se toca)" + (ya ? " · " + ya + " ya estaban" : ""))
                     : "Sin recursos de la norma para esta familia en la vista actual");
  }

  function agregarPropio(b, it, letra, propio) {
    var fam = FAMILIAS[letra];
    var tipo = propio.tipo || fam.tipos[0];
    var ed = asegurarEdicion(it);
    var arr = ed.propios[tipo] = ed.propios[tipo] || [];
    if (arr.some(function (p) { return p.codigo === propio.codigo; })) {
      toastO("⚠ " + tipo + " " + propio.codigo + " ya está especificado (no se duplica)");
      return false;
    }
    arr.push({
      tipo: tipo, codigo: propio.codigo, descripcion: propio.descripcion, um: propio.um,
      coef: propio.coef, precio: propio.precio, origen: propio.origen,
      agregado: new Date().toISOString()
    });
    ed.actualizado = new Date().toISOString();
    guardarYRefrescar(b);
    return true;
  }

  /* edición en línea de un recurso propio (inputs data-pcod2pe="tipo#idx|campo") */
  function editarPropio(b, it, inp) {
    var spec = String(inp.getAttribute("data-pcod2pe")).split("|");
    var campo = spec.pop();
    var head = String(spec[0]).split("#");
    var tipo = head[0], idx = parseInt(head[1], 10);
    var ed = edicionDe(it);
    if (!ed || !ed.propios[tipo]) return;
    var p = ed.propios[tipo][idx];
    if (!p) return;
    var txt = String(inp.value == null ? "" : inp.value).trim();
    if (campo === "precio" && txt === "") {          /* «sin precio»: estado documentado, excluido del total */
      p.precio = null;
      ed.actualizado = new Date().toISOString();
      guardarYRefrescar(b);
      toastO("⚠ " + tipo + " " + p.codigo + " sin precio — excluido del total (no se inventa ningún valor)");
      return;
    }
    var val = validarNum(inp.value);
    if (!val.ok) {
      toastO("⚠ Valor inválido (" + val.motivo + ") en " + tipo + " " + p.codigo + " — se conserva el anterior (≥ 0; precio admite vacío = sin precio)");
      guardarYRefrescar(b);              // re-render restaura el valor válido anterior
      return;
    }
    p[campo] = val.v;
    ed.actualizado = new Date().toISOString();
    guardarYRefrescar(b);
  }

  /* entrada manual del panel «añadir recurso» */
  function agregarManual(b, it, letra) {
    var fam = FAMILIAS[letra];
    var g = function (id) {
      var el = document.getElementById(id);
      return el ? String(el.value == null ? "" : el.value).trim() : "";
    };
    var codigo = g("pcod2-man-codigo"), desc = g("pcod2-man-desc"), um = g("pcod2-man-um");
    var coefTxt = g("pcod2-man-coef"), precioTxt = g("pcod2-man-precio");
    var tipoSel = g("pcod2-rec-tipo") || fam.tipos[0];
    if (!codigo || !desc || !um) { toastO("⚠ Entrada manual incompleta: código, descripción y um son obligatorios"); return; }
    var vc = validarNum(coefTxt);
    if (!vc.ok) { toastO("⚠ Cantidad (coef) inválida: requiere un número ≥ 0"); return; }
    var precio = null;
    if (precioTxt !== "") {
      var vp = validarNum(precioTxt);
      if (!vp.ok) { toastO("⚠ Precio inválido: ≥ 0 o vacío (sin precio)"); return; }
      precio = vp.v;
    }
    if (agregarPropio(b, it, letra, { tipo: tipoSel, codigo: codigo, descripcion: desc, um: um, coef: vc.v, precio: precio, origen: "manual" }))
      toastO("＋ " + tipoSel + " " + codigo + " añadido (entrada manual — del presupuesto, nunca del catálogo)");
  }
  function quitarPropio(b, it, tipo, idx) {
    var ed = edicionDe(it);
    if (!ed || !ed.propios[tipo]) return;
    var arr = ed.propios[tipo];
    var removido = arr[idx];
    if (!removido) return;
    arr.splice(idx, 1);               // se conserva la clave (aunque quede vacía) para el Deshacer
    guardarYRefrescar(b);
    if (typeof toastAction === "function") {
      toastAction("«" + String(removido.codigo) + "» quitado de la especificación", "Deshacer", function () {
        arr.splice(Math.min(idx, arr.length), 0, removido);
        if (typeof touch === "function") touch(b);
        if (typeof renderEditor === "function") renderEditor();
      });
    } else toastO("Recurso propio quitado");
  }
  function quitarEspecificacionFamilia(b, it, letra) {
    var fam = FAMILIAS[letra];
    var ed = edicionDe(it);
    if (!ed) return;
    var n = 0;
    fam.tipos.forEach(function (t) { n += (ed.propios[t] || []).length; });
    if (!n) return;
    if (!confirmarDestructivo("¿Quitar los " + n + " recurso(s) especificado(s) de " + fam.largo +
          "? (la familia quedará sin recursos hasta que cargue la norma o añada otros)")) return;
    fam.tipos.forEach(function (t) { delete ed.propios[t]; });
    ed.actualizado = new Date().toISOString();
    guardarYRefrescar(b);
    toastO("Especificación de " + fam.nombre.toLowerCase() + " quitada");
  }
  function quitarTodasEdiciones(b, it) {
    var ed = edicionDe(it);
    if (!ed) return;
    var nc = Object.keys(ed.cambios || {}).length;
    var np = 0;
    Object.keys(ed.propios || {}).forEach(function (t) { np += ed.propios[t].length; });
    if (!nc && !np) return;
    if (!confirmarDestructivo("¿Quitar TODAS las ediciones (" + nc + " sobre la norma, " + np +
          " recursos propios)? El ítem vuelve a la descomposición de la norma tal como está en la vista.")) return;
    delete it.edicionRecursos;
    guardarYRefrescar(b);
    toastO("Ediciones quitadas — descomposición de la norma restaurada");
  }

  /* ---- búsqueda de recursos del nomenclador (/api/recursos, MISIÓN V) ---- */
  function buscarRecursosPanel(letra, forzar) {
    var q = (document.getElementById("pcod2-rec-q") || {}).value || "";
    var tipoSel = (document.getElementById("pcod2-rec-tipo") || {}).value || "";
    if (!forzar && !String(q).trim()) { toastO("Escriba un código o descripción para buscar"); return; }
    S.busqRec = { letra: letra, q: String(q).trim(), tipo: tipoSel, resultados: [], cargando: true };
    renderSiEditor2();
    var url = "/api/recursos?q=" + encodeURIComponent(String(q).trim()) +
      (tipoSel ? "&tipo=" + encodeURIComponent(tipoSel) : "") + "&limit=25";
    var vId = S.precioVersionId || S.versionId;
    if (vId) url += "&version_id=" + vId;
    api(url).then(function (d) {
      if (d.error) { S.busqRec = { letra: letra, q: q, tipo: tipoSel, resultados: [], error: d.error }; }
      else S.busqRec = { letra: letra, q: q, tipo: tipoSel, resultados: d.resultados || [], version: d.version };
      renderSiEditor2();
    }).catch(function (e) {
      /* MISIÓN VIII: modo web → nomenclador desde los datos embebidos
         (misma forma de respuesta que /api/recursos). */
      if (S.estatico && window.__pcodEstatico) {
        window.__pcodEstatico.recursos(String(q).trim(), tipoSel, vId || null, 25)
          .then(function (d) {
            if (d.error) { S.busqRec = { letra: letra, q: q, tipo: tipoSel, resultados: [], error: d.error }; }
            else S.busqRec = { letra: letra, q: q, tipo: tipoSel, resultados: d.resultados || [], version: d.version };
            renderSiEditor2();
          })
          .catch(function (e2) {
            S.busqRec = { letra: letra, q: q, tipo: tipoSel, resultados: [],
                          error: "sin datos embebidos del nomenclador (" + String(e2 && e2.message || e2) + ")" };
            renderSiEditor2();
          });
        return;
      }
      S.busqRec = { letra: letra, q: q, tipo: tipoSel, resultados: [], error: "sin conexión con la capa local (/api/recursos)" };
      renderSiEditor2();
    });
  }
  function renderSiEditor2() {
    if (typeof renderEditor === "function" &&
        typeof state !== "undefined" && state.view === "editor") renderEditor();
  }

  /* ==================================================================== */
  /* MISIÓN V — RENDER: barra de palomitas, tabla efectiva editable,       */
  /* panel de especificación y caja de modificaciones                     */
  /* ==================================================================== */

  function umPartidaDe(it, d) {
    var p = (d && !d.error && d.partida) ? d.partida : null;
    return (p && p.unidad) || (it && it.um) || "?";
  }
  function fechaCorta(iso) {
    return String(iso || "").replace("T", " ").slice(0, 16);
  }

  /* barra de indicadores M/H/E (S-050) — solo para partidas del presupuesto */
  function barraFlagsHTML(it) {
    if (!it || it.tipo !== "partida") return "";
    var fl = flagsDe(it);
    var ed = edicionDe(it);
    var h = '<div class="pcod2-flgbar" id="pcod2-flags"><span class="pcod2-mini">Indicadores M/H/E (manual págs. 32-33):</span>';
    ["M", "H", "E"].forEach(function (l) {
      var fam = FAMILIAS[l];
      var on = fl.indexOf(l) >= 0;
      var nEsp = 0;
      if (ed && ed.propios) fam.tipos.forEach(function (t) { nEsp += (ed.propios[t] || []).length; });
      var esp = nEsp > 0 && !on;
      h += '<span class="pcod2-flg' + (on ? " pcod2-on" : "") + (esp ? " pcod2-esp" : "") +
        '" data-pcod2flg="' + l + '" role="checkbox" aria-checked="' + on + '" tabindex="0" title="' +
        (on
          ? "Palomita activa: los recursos de la norma de esta familia se aplican tal cual. Clic para quitarla y poder especificar recursos propios de " + fam.nombre + "."
          : "Sin palomita: las filas de la norma de esta familia quedan desactivadas" +
            (nEsp ? " y se usan los " + nEsp + " especificado(s)" : " (puede especificar los suyos)") +
            ". Clic para reponerla (se descarta lo especificado y se vuelve a la norma).") +
        '"><b>✓</b>' + l + " · " + esc(fam.nombre) + (nEsp ? ' <span class="pcod2-mini">(' + nEsp + ' esp.)</span>' : "") + '</span>';
    });
    h += '<span class="pcod2-mini">Mismo campo <code>flags</code> que la pestaña Partidas y el motor (sin duplicación). <b style="color:#b3261e">Sombreado = especificado</b> (manual pág. 35).</span></div>';
    return h;
  }

  /* fila de la tabla efectiva */
  function filaEfectivaHTML(f, it, d, cantidad) {
    var umPartida = umPartidaDe(it, d);
    if (f.origen === "norma") {
      var desact = f.estado === "desactivada";
      var editada = f.estado === "editada";
      var clave = f.tipo + "|" + f.codigo;
      var expandible = (f.hijos || []).length > 0 && !desact;
      var marca = expandible ? (S.expandidos[clave] ? "▾ " : "▸ ") : "";
      var coefCell, precioCell;
      if (desact) {
        coefCell = '<td class="num"><span class="pcod2-tach" title="Original de la norma: ' + esc(String(f.coefOriginal)) + '">' + fmtCoef(f.coefOriginal) + "</span></td>";
        precioCell = '<td class="num"><span class="pcod2-tach" title="Original de la norma: ' + esc(String(f.precioOriginal)) + '">' + fmtM(f.precioOriginal) + "</span></td>";
      } else {
        coefCell = '<td class="num"><input type="number" class="pcod2-in" step="any" min="0" data-pcod2ed="' +
          esc(f.tipo) + "|" + esc(f.codigo) + '|coef" value="' + (f.coef == null ? "" : String(Number(f.coef))) +
          '" title="Original de la norma: ' + esc(String(f.coefOriginal)) + ' — edite (≥ 0) y Enter/clic fuera para aplicar"></td>';
        precioCell = '<td class="num"><input type="number" class="pcod2-in" step="0.0001" min="0" data-pcod2ed="' +
          esc(f.tipo) + "|" + esc(f.codigo) + '|precio" value="' + (f.precio == null ? "" : String(Number(f.precio))) +
          '" title="Original de la norma: ' + esc(String(f.precioOriginal)) + ' (Money 4 dec)"></td>';
      }
      var importe = (desact || f.importe == null) ? null : f.importe;
      var consumo = (desact || f.consumo == null) ? null : f.consumo;
      var importeTotal = (desact || f.importeTotal == null) ? null : f.importeTotal;
      var fuente = [];
      if (desact)
        fuente.push('<span class="pcod2-tag pcod2-des" title="Palomita ' + familiaDeTipo(f.tipo) +
          ' sin marcar: fila de la norma desactivada y excluida del total (sustituida por la especificación de esa familia)">desactivada (' + familiaDeTipo(f.tipo) + ')</span>');
      else if (editada)
        fuente.push('<span class="pcod2-tag pcod2-edit" title="norma: coef ' + esc(String(f.coefOriginal)) +
          ", precio " + esc(String(f.precioOriginal)) + ' — editada en este presupuesto">editada</span>');
      else
        fuente.push('<span class="pcod2-tag pcod2-dim">de la norma</span>');
      if (f.precio_respaldo) fuente.push('<span class="pcod2-tag pcod2-warn" title="Sin precio en la versión de precios: se usa el precio propio de la versión de la norma">respaldo</span>');
      if (f.advertencia) fuente.push('<span class="pcod2-tag pcod2-warn" title="' + esc(f.advertencia) + '">⚠</span>');
      var accion = desact ? "" : (editada
        ? '<button class="btn sm" data-pcod2rev="' + esc(f.tipo) + "|" + esc(f.codigo) + '" title="Restaurar el valor original de la norma">↺</button>'
        : "");
      return '<tr class="pcod2-comp' + (desact ? " pcod2-des" : "") + '" data-pcod2clave="' + esc(clave) + '"' +
        (expandible ? ' title="Ampliar/contraer componentes del juego o semielaborado y detalle"' : ' title="Ver detalle"') + '>' +
        "<td>" + marca + esc(ETIQUETAS[f.tipo] || f.tipo) + "</td>" +
        '<td><code class="pcod2-code">' + esc(f.codigo) + "</code></td>" +
        "<td>" + esc(f.descripcion || "(referencia sin nomenclador)") + ((f.hijos || []).length ? ' <span class="pcod2-mini">(' + f.hijos.length + " comp.)</span>" : "") + "</td>" +
        "<td>" + esc(f.um || "?") + "</td>" +
        coefCell + precioCell +
        '<td class="num">' + (importe == null ? "—" : fmtM(importe, true)) + "</td>" +
        '<td class="num">' + (consumo == null ? "—" : fmtM(consumo, true)) + "</td>" +
        '<td class="num">' + (importeTotal == null ? "—" : fmtM(importeTotal, true)) + "</td>" +
        "<td>" + fuente.join("") + "</td>" +
        '<td class="pcod2-acc">' + accion + "</td></tr>";
    }
    /* recurso propio (especificación) */
    var k = f.tipo + "#" + f.idx;
    var sinPrecio = f.estado === "sin-precio";
    var ignorado = f.estado === "ignorado";
    var umAviso = (f.um && umPartida !== "?" && f.um !== umPartida)
      ? '<span class="pcod2-mini" title="El coeficiente se expresa en la um de la partida por unidad de recurso">⚠ um ' + esc(f.um) + " ≠ um partida " + esc(umPartida) + "</span>"
      : "";
    var importe = (ignorado || sinPrecio || f.importe == null) ? null : f.importe;
    var consumo = (ignorado || f.consumo == null) ? null : f.consumo;
    var importeTotal = (ignorado || f.importeTotal == null) ? null : f.importeTotal;
    var fuente = [];
    fuente.push('<span class="pcod2-tag pcod2-propio" title="Recurso especificado en este presupuesto (origen: ' +
      esc(f.origenDetalle || "?") + ', añadido ' + fechaCorta(f.agregado) + ')">' + esc(f.origenDetalle || "propio") + "</span>");
    if (sinPrecio) fuente.push('<span class="pcod2-tag pcod2-warn" title="Sin precio: excluido del total — no se inventa ningún valor">sin precio</span>');
    if (ignorado) fuente.push('<span class="pcod2-tag pcod2-warn" title="La palomita de su familia está repuesta: este recurso propio se ignora (la norma vuelve a aplicar)">ignorado</span>');
    return '<tr class="pcod2-prop">' +
      "<td>" + esc(ETIQUETAS[f.tipo] || f.tipo) + " (propio)</td>" +
      '<td><code class="pcod2-code">' + esc(f.codigo) + "</code></td>" +
      "<td>" + esc(f.descripcion || "?") + (umAviso ? " " + umAviso : "") + "</td>" +
      "<td>" + esc(f.um || "?") + "</td>" +
      '<td class="num"><input type="number" class="pcod2-in" step="any" min="0" data-pcod2pe="' + k + '|coef" value="' +
        (f.coef == null ? "" : String(Number(f.coef))) + '" title="Cantidad (coef) del recurso propio — edición del presupuesto"></td>' +
      '<td class="num"><input type="number" class="pcod2-in" step="0.0001" min="0" placeholder="sin precio" data-pcod2pe="' + k + '|precio" value="' +
        (f.precio == null ? "" : String(Number(f.precio))) + '" title="Precio MN. Vacío = sin precio (excluido del total con aviso)"></td>' +
      '<td class="num">' + (importe == null ? "—" : fmtM(importe, true)) + "</td>" +
      '<td class="num">' + (consumo == null ? "—" : fmtM(consumo, true)) + "</td>" +
      '<td class="num">' + (importeTotal == null ? "—" : fmtM(importeTotal, true)) + "</td>" +
      "<td>" + fuente.join("") + "</td>" +
      '<td class="pcod2-acc"><button class="btn sm danger" data-pcod2rm="' + k + '" title="Quitar de la especificación (Deshacer disponible)">✕</button></td></tr>';
  }

  function filaDetalleEfectiva(f, it, d, cantidad, cols) {
    var t = "<b>Detalle:</b> " + esc(ETIQUETAS[f.tipo] || f.tipo) + " " + esc(f.codigo) +
      " · " + esc(f.descripcion || "(referencia sin nomenclador)") +
      " · um " + esc(f.um || "?") +
      " · coef norma " + esc(String(f.coefOriginal)) + (f.coef !== f.coefOriginal ? " → efectivo " + esc(String(f.coef)) : "") +
      " · precio norma " + fmtM(f.precioOriginal, true) + (f.precio !== f.precioOriginal ? " → efectivo " + fmtM(f.precio, true) : "") + " MN";
    if (f.coef != null && f.precio != null) t += " · importe = " + fmtCoef(f.coef) + " × " + fmtM(f.precio) + " = " + fmtM(f.coef * f.precio, true);
    if (cantidad != null && f.coef != null) t += " · consumo = " + fmtCoef(f.coef) + " × " + fmtCoef(cantidad) + " = " + fmtM(f.coef * cantidad, true);
    if ((f.hijos || []).length)
      t += " · " + f.hijos.length + " componentes (juego/semielaborado): informativos — el subtotal usa el precio del compuesto (F1/F7/F8)";
    return '<tr class="pcod2-det"><td colspan="' + cols + '">' + t + "</td></tr>";
  }

  /* tabla de la descomposición EFECTIVA (S-052) — solo modo presupuesto */
  function tablaEfectivaHTML(it, d, cantidad) {
    var ed = edicionDe(it);
    var eff = descompEfectiva(it);
    var p = (d && !d.error && d.partida) ? d.partida : null;
    var umPartida = umPartidaDe(it, d);
    var hayEdiciones = !!(ed && (Object.keys(ed.cambios || {}).length ||
      Object.keys(ed.propios || {}).some(function (t) { return (ed.propios[t] || []).length; })));
    var cols = 11;
    var h = '<div class="tblwrap"><table class="pcod2-tbl" id="pcod2-tbl-efectiva"><thead><tr>' +
      "<th>Tipo</th><th>Código</th><th>Descripción</th><th>Um</th>" +
      '<th class="num">Coef.</th><th class="num">Precio MN</th><th class="num">Importe/um</th>' +
      '<th class="num">Consumo</th><th class="num">Importe total</th>' +
      "<th>Fuente / estado</th><th>Acción</th></tr></thead><tbody>";
    TIPOS_ORDEN.forEach(function (t) {
      if (S.filtros[t] === false) return;    // los chips filtran SOLO filas de la norma; los propios siempre se muestran
      var filasTipo = eff.filas.filter(function (f) { return f.tipo === t; });
      if (!filasTipo.length) return;
      filasTipo.forEach(function (f) {
        h += filaEfectivaHTML(f, it, d, cantidad);
        var clave = f.tipo + "|" + f.codigo;
        if (f.origen === "norma" && S.expandidos[clave]) h += filaDetalleEfectiva(f, it, d, cantidad, cols);
      });
    });
    /* subtotales EFECTIVOS por tipo (solo filas activas; los propios cuentan en su tipo) */
    [["material", "Subtotal materiales (efectivo)"], ["mano_obra", "Subtotal mano de obra (efectivo)"],
     ["equipo", "Subtotal equipos (efectivo)"], ["juego", "Subtotal juegos de trabajo (efectivo)"],
     ["semielaborado", "Subtotal semielaborados (efectivo)"]].forEach(function (par) {
      if (eff.subtotales[par[0]] == null) return;
      var ref = (d && !d.error && d.subtotales) ? d.subtotales[par[0]] : null;
      h += '<tr class="pcod2-tot"><td colspan="5">' + par[1] + "</td>" +
        '<td class="num" colspan="3">' + fmtM(eff.subtotales[par[0]], true) +
        (ref != null && ref !== eff.subtotales[par[0]] ? ' <span class="pcod2-mini">(norma: ' + fmtM(ref, true) + ")</span>" : "") +
        '</td><td colspan="3"></td></tr>';
    });
    h += '<tr class="pcod2-tot"><td colspan="5">TOTAL descomposición efectiva (Σ coef×precio de filas activas, MN/' + esc(umPartida) + ')</td>' +
      '<td class="num" colspan="3" id="pcod2-tot-efectiva">' + fmtM(eff.total, true) +
      (hayEdiciones && d && !d.error && d.total != null && d.total !== eff.total
        ? ' <span class="pcod2-mini">(norma sin palomitas ni ediciones: ' + fmtM(d.total, true) + ")</span>" : "") +
      '</td><td colspan="3"></td></tr>';
    if (cantidad != null)
      h += '<tr class="pcod2-tot"><td colspan="5">TOTAL para la obra (× cantidad ' + fmtCoef(cantidad) + ')</td>' +
        '<td class="num" colspan="3" id="pcod2-tot-obra">' + fmtM(eff.totalObra, true) + '</td><td colspan="3"></td></tr>';
    h += "</tbody></table></div>";
    h += '<div class="pcod2-mini">Importe/um = coef × precio · Consumo = coef × cantidad presupuestada (' +
      fmtCoef(cantidad) + ") · Importe total = consumo × precio. Filas de la norma desactivadas (palomita quitada) y propias sin precio: excluidas del total — siempre explícito, nunca en silencio. Los componentes de juegos/semielaborados son informativos (F1/F7/F8). El precio unitario del <b>motor</b> PRECOST (catálogo 2025, flags y A.H/A.E) es una base distinta: se muestra aparte, nunca se sobrescribe.</div>";
    return h;
  }

  /* panel «añadir recurso propio» (dentro de la caja de edición) */
  function panelRecursoHTML(letra, it, d) {
    var fam = FAMILIAS[letra];
    var ed = edicionDe(it);
    var umPartida = umPartidaDe(it, d);
    var br = (S.busqRec && S.busqRec.letra === letra) ? S.busqRec : null;
    var h = '<div class="pcod2-box" id="pcod2-panelrec" style="margin:6px 0">';
    h += "<b>Añadir recurso propio — " + esc(fam.largo) + "</b> ";
    h += '<span class="pcod2-mini">nomenclador /api/recursos' +
      (br && br.version ? " · " + esc(br.version.catalogo) + " " + esc(br.version.version) : "") + "</span>";
    h += '<div class="pcod2-act">';
    h += '<input id="pcod2-rec-q" placeholder="Código o descripción (p. ej. cemento, albañil…)" value="' +
      esc(br ? br.q : "") + '" style="min-width:230px">';
    h += '<select id="pcod2-rec-tipo">' + (fam.tipos.length > 1 ? '<option value="">— Todos los tipos —</option>' : "") +
      fam.tipos.map(function (t) {
        return '<option value="' + t + '"' + (br && br.tipo === t ? " selected" : "") + ">" + esc(ETIQUETAS[t] || t) + "</option>";
      }).join("") + "</select>";
    h += '<button class="btn sm primary" id="pcod2-rec-buscar">Buscar</button>';
    h += "</div>";
    if (br) {
      if (br.cargando) h += '<div class="pcod2-mini">Buscando…</div>';
      else if (br.error) h += '<div class="pcod2-box pcod2-warnbox">' + esc(br.error) + "</div>";
      else if (!br.resultados.length) h += '<div class="note">Sin resultados para «' + esc(br.q) + "».</div>";
      else {
        h += '<div id="pcod2-rec-res">';
        br.resultados.forEach(function (res, j) {
          var ya = ed && ed.propios[res.tipo] &&
            ed.propios[res.tipo].some(function (pp) { return pp.codigo === res.codigo; });
          h += '<div class="pcod2-recrow" data-pcod2resadd="' + j + '">' +
            '<code class="pcod2-code">' + esc(res.codigo) + "</code> · " + esc(res.descripcion) +
            ' <i>(' + esc(res.unidad || "?") + ')</i>' +
            (res.precio_mn == null
              ? ' <span class="pcod2-tag pcod2-warn">sin precio</span>'
              : ' <b class="num">' + fmtM(res.precio_mn) + " MN</b>") +
            (ya ? ' <span class="pcod2-tag pcod2-warn">ya especificado</span>' : "") +
            ((res.mismo_codigo_otro_tipo || []).length
              ? ' <span class="pcod2-tag pcod2-warn" title="El mismo código existe como ' +
                esc((res.mismo_codigo_otro_tipo || []).join(", ")) + ' en esta versión">código ambiguo</span>' : "") +
            (res.unidad && umPartida !== "?" && res.unidad !== umPartida
              ? ' <span class="pcod2-mini">⚠ um ' + esc(res.unidad) + " ≠ um partida " + esc(umPartida) + " — coef en " + esc(umPartida) + " por recurso</span>"
              : "") +
            "</div>";
        });
        h += "</div>";
      }
    }
    h += '<div class="pcod2-man">' +
      '<input id="pcod2-man-codigo" placeholder="Código (único en la especificación)">' +
      '<input id="pcod2-man-desc" placeholder="Descripción">' +
      '<input id="pcod2-man-um" placeholder="Um (p. ej. ' + esc(umPartida) + ')">' +
      '<input id="pcod2-man-coef" type="number" min="0" step="any" placeholder="Cantidad (coef)">' +
      '<input id="pcod2-man-precio" type="number" min="0" step="0.0001" placeholder="Precio MN (vacío = sin precio)">' +
      '<button class="btn sm" id="pcod2-man-add">Añadir manual</button></div>';
    h += '<div class="pcod2-mini">La entrada manual pertenece al presupuesto (no crea nada en el catálogo). El mismo código no se duplica (aviso «ya especificado»).</div>';
    h += "</div>";
    return h;
  }

  /* caja de edición: acciones por familia + modificaciones + reversibilidad */
  function boxEdicionHTML(b, it, d, cantidad) {
    if (!it) return "";
    var ed = edicionDe(it);
    var eff = descompEfectiva(it);
    var fl = flagsDe(it);
    var h = '<div class="pcod2-box" id="pcod2-edicion">';
    h += "<b>Edición de recursos del presupuesto (S-050/S-052)</b> ";
    h += '<span class="pcod2-mini">Las ediciones viven SOLO en este presupuesto ' +
      "(guardadas con él, <code>p3pro.budgets</code>): la norma, el catálogo y la BD no se modifican.</span>";
    if (!eff.tieneNorma)
      h += '<div class="pcod2-mini">⚠ Sin normas de composición en la vista actual: la edición de filas de la norma y «Cargar normas» quedan pendientes; los indicadores M/H/E y los recursos propios siguen disponibles.</div>';
    ["M", "H", "E"].forEach(function (l) {
      if (fl.indexOf(l) >= 0) return;            // familia con palomita: la norma se aplica tal cual
      var fam = FAMILIAS[l];
      var nEsp = 0;
      if (ed && ed.propios) fam.tipos.forEach(function (t) { nEsp += (ed.propios[t] || []).length; });
      h += '<div class="pcod2-act"><b>' + esc(fam.largo) + "</b> " +
        '<span class="pcod2-mini">(sin palomita ' + l + " — especificación activa" +
        (nEsp ? ", sombreada: " + nEsp + " recurso(s)" : "") + ")</span>";
      h += '<button class="btn sm" data-pcod2cargar="' + l +
        '" title="Copiar los recursos de la norma de esta familia a la especificación como punto de partida editable (manual pág. 34)">⤓ Cargar normas</button>';
      h += '<button class="btn sm' + (S.panelRec === l ? " primary" : "") + '" data-pcod2panel="' + l + '">' +
        (S.panelRec === l ? "Cerrar panel" : "+ Añadir recurso") + "</button>";
      if (nEsp) h += '<button class="btn sm danger" data-pcod2quitar-esp="' + l + '">Quitar especificación (' + nEsp + ")</button>";
      h += "</div>";
      if (S.panelRec === l) h += panelRecursoHTML(l, it, d);
    });
    /* modificaciones — transparencia total (qué cambió, respecto a qué) */
    var mods = [];
    if (ed) {
      Object.keys(ed.cambios || {}).forEach(function (k) {
        var partes = k.split("|");
        var tipo = partes.shift();
        var codigo = partes.join("|");
        var c = ed.cambios[k];
        var fila = eff.filas.filter(function (f) { return f.origen === "norma" && f.tipo === tipo && f.codigo === codigo; })[0];
        if (!fila) { mods.push("<li><b>" + esc(tipo) + " " + esc(codigo) + "</b>: edición huérfana en esta vista (el código no está en la norma mostrada) — no se aplica al total.</li>"); return; }
        var txt = [];
        if (c.coef != null) txt.push("coef " + fmtCoef(fila.coefOriginal) + " → <b>" + fmtCoef(c.coef) + "</b>");
        if (c.precio != null) txt.push("precio " + fmtM(fila.precioOriginal) + " → <b>" + fmtM(c.precio) + "</b> MN");
        mods.push("<li><b>" + esc(tipo) + " " + esc(codigo) + "</b> (" + esc(String(fila.descripcion || "?").slice(0, 46)) + "): " + txt.join(" · ") + " · <span class=\"pcod2-mini\">↺ en la fila</span></li>");
      });
      Object.keys(ed.propios || {}).forEach(function (t) {
        (ed.propios[t] || []).forEach(function (pp) {
          mods.push("<li><b>" + esc(t) + " " + esc(pp.codigo) + "</b> (" + esc(String(pp.descripcion || "?").slice(0, 46)) +
            "): propio (" + esc(pp.origen) + ") · coef " + fmtCoef(pp.coef) + " · precio " +
            (pp.precio == null ? "sin precio" : fmtM(pp.precio) + " MN") + " · añadido " + fechaCorta(pp.agregado) + "</li>");
        });
      });
    }
    if (mods.length) {
      h += "<div><b>Modificaciones (" + mods.length + "):</b><ul class=\"pcod2-mods\">" + mods.join("") + "</ul></div>";
      h += '<div class="pcod2-act"><button class="btn sm danger" id="pcod2-quitar-todas">Quitar TODAS las ediciones</button>' +
        '<span class="pcod2-mini">Guardado con el presupuesto (p3pro.budgets)' +
        (ed && ed.actualizado ? " · actualizado " + fechaCorta(ed.actualizado) : "") + "</span></div>";
    }
    h += '<div class="pcod2-mini">Recálculo: importe = coef × precio · consumo = coef × cantidad presupuestada · importe total = consumo × precio · subtotal por tipo = Σ importes de filas activas · total efectivo = Σ subtotales · total de obra = total × cantidad. Sin redondeo interno (doble precisión); presentación 4 decimales.</div>';
    h += "</div>";
    return h;
  }




  /* ================================================================= RENDER */
  function render(b, r) {
    var host = document.getElementById("tab-recursos");
    if (!host) return;
    /* MISIÓN V: esta función también se invoca directamente (handlers del
       wire: filtros, selección, búsqueda) sin pasar por renderTabRecursos
       original, que es quien limpia el tab. Sin esta limpieza las secciones
       se acumulaban (defecto latente de III-C): se elimina la anterior y se
       inserta UNA sola (id estable para pruebas y DOM consistente). */
    var previa = host.querySelectorAll(":scope > .pcod2");
    for (var i = 0; i < previa.length; i++) previa[i].parentNode.removeChild(previa[i]);
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
    if (S.servidorOk || S.estatico) {   /* MISIÓN VIII: también en modo web */
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
      if (S.estatico) {
        /* MISIÓN VIII: web pública con datos PRECODI embebidos — NO es una
           degradación: catálogo, normas, nomenclador y comparación de
           versiones funcionan igual que con el servidor local. */
        h += '<div class="pcod2-box pcod2-warnbox"><b>Modo web — datos PRECODI embebidos (MISIÓN VIII).</b> ' +
          "Consultas del catálogo, normas y nomenclador servidas desde los datos publicados " +
          "(<code>dist/data</code>) sin servidor local. La especificación (S-050) y la edición " +
          "de cantidad/precio (S-052) funcionan igual: los cambios viven SOLO en este presupuesto.</div>";
      } else {
      var haySnapshot = S.itemIdx != null && b && b.items[S.itemIdx] && b.items[S.itemIdx].normaPreco;
      h += '<div class="pcod2-box pcod2-warnbox"><b>Capa local PRECODI no disponible.</b> ' +
        (haySnapshot
          ? "Se muestra la descomposición vinculada a este presupuesto (snapshot guardado; no se pueden consultar otras partidas del catálogo hasta que se inicie <code>scripts/servidor_precodi.py</code>)."
          : "Para consultar descomposiciones del catálogo PRECODI, inicie el servidor local: <code>python3 scripts/servidor_precodi.py</code>. Las descomposiciones ya vinculadas a partidas del presupuesto se muestran desde su snapshot guardado.") +
        '</div>';
      }
    }

    /* --- aviso MISIÓN V: BD sin normas (regeneración parcial) --- */
    if (S.servidorOk && S.sinNormas) {
      h += '<div class="pcod2-box pcod2-warnbox"><b>BD sin normas de composición.</b> ' +
        'Solo está importada la base PRECOST 2025 (regeneración parcial tras la pérdida de fuentes; ver INFORME_FASE_V). ' +
        'La edición de filas de la norma (S-052) y «Cargar normas» quedan PENDIENTES hasta re-importar las bases PRECODI; ' +
        'los indicadores M/H/E (S-050) y los recursos propios desde el nomenclador 2025 funcionan con normalidad.</div>';
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
    var enPresupuesto = S.itemIdx != null && b && b.items[S.itemIdx];
    var it = enPresupuesto ? b.items[S.itemIdx] : null;
    var cantidad = it ? (Number(it.cantidad) || 0) : null;
    var p = null;
    var h = "";

    if (d.error) {
      var vers = (d.versiones_disponibles || []).map(function (v) {
        return '<span class="pcod2-tag">' + esc(v.version) + '</span>';
      }).join("");
      h += '<div class="pcod2-box pcod2-warnbox">' + esc(d.error) +
        (vers ? '<br>Versiones donde existe: ' + vers : "") + '</div>';
      if (!enPresupuesto) return h;              /* consulta de catálogo: fin */
      /* MISIÓN V: modo presupuesto — continuar con base vacía (flags y propios editables) */
      h += '<div class="pcod2-head"><b><code class="pcod2-code">' + esc(it.codigo) + '</code> ' +
        esc(it.descripcion || "") + '</b> <span class="pcod2-tag pcod2-ok">EN EL PRESUPUESTO</span></div>' +
        '<div class="pcod2-mini">Vista de descomposición no disponible para esta selección (base vacía): los indicadores M/H/E y los recursos propios siguen editables.</div>';
    } else {
      p = d.partida;
      /* cabecera: código, descripción, unidad, fuente y versión */
      h += '<div class="pcod2-head"><b><code class="pcod2-code">' + esc(p.codigo) + '</code> ' +
        esc(p.descripcion) + '</b></div>';
      h += '<div>';
      h += '<span class="pcod2-tag">um: ' + esc(p.unidad || "?") +
        (p.factor_unidad && p.factor_unidad !== 1 ? " (×" + esc(p.factor_unidad) + ")" : "") + '</span>';
      h += '<span class="pcod2-tag' + (enPresupuesto ? ' pcod2-ok' : ' pcod2-dim') + '" >' +
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
        if (!enPresupuesto) return h;            /* consulta de catálogo: fin */
      }
    }

    /* cantidad presupuestada (modo presupuesto) + indicadores M/H/E (MISIÓN V) */
    if (enPresupuesto) {
      h += '<div class="pcod2-bar"><span>Cantidad presupuestada (' + esc(it.um || (p ? p.unidad : "") || "?") +
        '):</span> <input type="number" class="pcod2-cant" id="pcod2-cant" step="0.0001" min="0" value="' +
        (cantidad || 0) + '">' +
        '<span class="pcod2-mini">Se guarda con el presupuesto (mecanismo existente); ' +
        'recalcula consumos e importes. La norma no se modifica.</span></div>';
      h += barraFlagsHTML(it);
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

    /* tabla de componentes: en modo presupuesto (MISIÓN V) la tabla es la
       descomposición EFECTIVA editable; en catálogo, la vista III-C original */
    if (enPresupuesto) {
      h += tablaEfectivaHTML(it, d, cantidad);
      h += boxEdicionHTML(b, it, d, cantidad);
    } else {
      var cols = 8;
      h += '<div class="tblwrap"><table class="pcod2-tbl"><thead><tr>' +
        "<th>Tipo</th><th>Código</th><th>Descripción</th><th>Um</th>" +
        '<th class="num">Coef.</th><th class="num">Precio MN</th><th class="num">Importe/um</th>' +
        "<th>Fuente</th></tr></thead><tbody>";
      tiposPresentes.forEach(function (t) {
        if (S.filtros[t] === false) return;
        comps.filter(function (c) { return c.tipo === t; }).forEach(function (c) {
          h += filaComponente(c, false, cantidad, false);
          var clave = c.tipo + "|" + c.codigo;
          if (S.expandidos[clave]) h += filaDetalle(c, cantidad, cols, false);
          (c.hijos || []).forEach(function (hj) {
            h += filaComponente(hj, false, cantidad, true, c);
            if (S.expandidos[hj.tipo + "|" + hj.codigo + "|h"]) h += filaDetalle(hj, cantidad, cols, true, c);
          });
        });
      });
      /* subtotales por tipo (vista de catálogo — III-C original) */
      h += '<tr class="pcod2-tot"><td colspan="5">Subtotal materiales</td>' +
        '<td class="num" colspan="1">' + fmtM(d.subtotales.material, true) + '</td><td colspan="2"></td></tr>';
      if (d.subtotales.mano_obra != null)
        h += '<tr class="pcod2-tot"><td colspan="5">Subtotal mano de obra</td>' +
          '<td class="num" colspan="1">' + fmtM(d.subtotales.mano_obra, true) + '</td><td colspan="2"></td></tr>';
      if (d.subtotales.equipo != null)
        h += '<tr class="pcod2-tot"><td colspan="5">Subtotal equipos</td>' +
          '<td class="num" colspan="1">' + fmtM(d.subtotales.equipo, true) + '</td><td colspan="2"></td></tr>';
      if (d.subtotales.juego != null)
        h += '<tr class="pcod2-tot"><td colspan="5">Subtotal juegos de trabajo</td>' +
          '<td class="num" colspan="1">' + fmtM(d.subtotales.juego, true) + '</td><td colspan="2"></td></tr>';
      if (d.subtotales.semielaborado != null)
        h += '<tr class="pcod2-tot"><td colspan="5">Subtotal semielaborados</td>' +
          '<td class="num" colspan="1">' + fmtM(d.subtotales.semielaborado, true) + '</td><td colspan="2"></td></tr>';
      h += '<tr class="pcod2-tot"><td colspan="5">TOTAL descomposición (Σ coef×precio, MN/' +
        esc(p.unidad || "?") + ')</td>' +
        '<td class="num" colspan="1">' + fmtM(d.total, true) + '</td><td colspan="2"></td></tr>';
      h += '</tbody></table></div>';
      h += '<div class="pcod2-mini">Importe/um = coeficiente × precio unitario. Los componentes de juegos y semielaborados (filas indentadas) son ' +
        'informativos: los subtotales usan el precio del juego/semielaborado (modelo F1/F7/F8 verificado).</div>';
    }

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

    /* comparación con el PU del presupuesto (motor PRECOST) — nunca se sobrescribe.
       MISIÓN V: con p nulo (vista de descomposición no disponible) no se compara. */
    if (enPresupuesto && p && r && r.items && r.items[S.itemIdx] != null) {
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
      } else if (!S.data.error) {
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
        .catch(function () {
          /* MISIÓN VIII: modo web → búsqueda de partidas desde los datos
             embebidos (misma forma de respuesta que /api/partidas). */
          if (S.estatico && window.__pcodEstatico) {
            window.__pcodEstatico.partidas(t, S.versionId, 25)
              .then(function (d) { S.resultadosBusqueda = d.resultados || []; render(b, r); })
              .catch(function () { S.resultadosBusqueda = []; render(b, r); });
            return;
          }
          S.resultadosBusqueda = []; render(b, r);
        });
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

    /* ================================================== MISIÓN V (S-050/S-052) */
    if (S.itemIdx != null && b && b.items[S.itemIdx] && b.items[S.itemIdx].tipo === "partida") {
      var itV = b.items[S.itemIdx];
      sec.querySelectorAll("[data-pcod2flg]").forEach(function (chip) {
        chip.addEventListener("click", function () {
          toggleFlag(b, itV, chip.getAttribute("data-pcod2flg"));
        });
        chip.addEventListener("keydown", function (e) {   /* accesible por teclado */
          if (e.key === " " || e.key === "Enter") { e.preventDefault(); toggleFlag(b, itV, chip.getAttribute("data-pcod2flg")); }
        });
      });
      sec.querySelectorAll("[data-pcod2ed]").forEach(function (inp) {
        inp.addEventListener("change", function () { aplicarCambioNorma(b, itV, inp); });
      });
      sec.querySelectorAll("[data-pcod2rev]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          revertirCambioNorma(b, itV, btn.getAttribute("data-pcod2rev"));
        });
      });
      sec.querySelectorAll("[data-pcod2pe]").forEach(function (inp) {
        inp.addEventListener("change", function () { editarPropio(b, itV, inp); });
      });
      sec.querySelectorAll("[data-pcod2rm]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          var parts = String(btn.getAttribute("data-pcod2rm")).split("#");
          quitarPropio(b, itV, parts[0], parseInt(parts[1], 10));
        });
      });
      sec.querySelectorAll("[data-pcod2cargar]").forEach(function (btn) {
        btn.addEventListener("click", function () { cargarNormasFamilia(b, itV, btn.getAttribute("data-pcod2cargar")); });
      });
      sec.querySelectorAll("[data-pcod2panel]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var l = btn.getAttribute("data-pcod2panel");
          S.panelRec = (S.panelRec === l) ? null : l;
          if (!S.panelRec) S.busqRec = null;
          renderSiEditor2();
        });
      });
      sec.querySelectorAll("[data-pcod2quitar-esp]").forEach(function (btn) {
        btn.addEventListener("click", function () { quitarEspecificacionFamilia(b, itV, btn.getAttribute("data-pcod2quitar-esp")); });
      });
      var qTodas = $("#pcod2-quitar-todas");
      if (qTodas) qTodas.addEventListener("click", function () { quitarTodasEdiciones(b, itV); });
      var rBuscar = $("#pcod2-rec-buscar");
      if (rBuscar) rBuscar.addEventListener("click", function () { buscarRecursosPanel(S.panelRec, false); });
      var rQ = $("#pcod2-rec-q");
      if (rQ) rQ.addEventListener("keydown", function (e) {
        if (e.key === "Enter") buscarRecursosPanel(S.panelRec, false);
      });
      sec.querySelectorAll("[data-pcod2resadd]").forEach(function (row) {
        row.addEventListener("click", function () {
          if (!S.busqRec || !S.busqRec.resultados) return;
          var res = S.busqRec.resultados[parseInt(row.getAttribute("data-pcod2resadd"), 10)];
          if (!res) return;
          if (agregarPropio(b, itV, S.busqRec.letra, {
            tipo: res.tipo, codigo: res.codigo, descripcion: res.descripcion,
            um: res.unidad, coef: 1, precio: res.precio_mn, origen: "catalogo"
          })) toastO("＋ " + res.tipo + " " + res.codigo + " añadido (del nomenclador — nunca del catálogo se crea nada)");
        });
      });
      var mAdd = $("#pcod2-man-add");
      if (mAdd) mAdd.addEventListener("click", function () { agregarManual(b, itV, S.panelRec); });
    }
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
  function aplicarVersionDefecto() {
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
      /* MISIÓN V: BD sin versiones con normas (regeneración parcial tras la
         pérdida de fuentes): degradación honesta — las descomposiciones se
         piden sin version_id (el servidor responde 404 controlado) y los
         recursos propios se buscan en el nomenclador disponible (2025). */
      S.sinNormas = !elegida;
    }
  }
  function sondearServidor(b, r) {
    api("/api/versiones").then(function (d) {
      S.servidorOk = true;
      S.estatico = false;
      S.versiones = d.versiones || [];
      aplicarVersionDefecto();
      render(b, r);
    }).catch(function () {
      /* MISIÓN VIII: sin servidor local → capa de datos embebidos de la web
         (overlay estatico.js + dist/data): MISMAS versiones, normas y
         nomenclador que el servidor local. Si tampoco existe, degradación
         honesta a snapshot como antes. */
      if (window.__pcodEstatico) {
        window.__pcodEstatico.versiones().then(function (d) {
          S.servidorOk = false;
          S.estatico = true;
          S.versiones = d.versiones || [];
          aplicarVersionDefecto();
          render(b, r);
        }).catch(function () {
          S.servidorOk = false;
          render(b, r);
        });
      } else {
        S.servidorOk = false;
        render(b, r);
      }
    });
  }

  function cargar(b) {
    if (!S.codigo) return;
    /* MISIÓN VIII: modo web (sin servidor, con datos embebidos) → la
       descomposición se resuelve desde la capa estática con la MISMA forma
       de respuesta y el mismo post-proceso (vínculo al presupuesto incluido). */
    if (S.servidorOk === false && S.estatico && window.__pcodEstatico) {
      S.offline = false;
      window.__pcodEstatico.descomposicion(
        S.codigo, S.versionId,
        S.precioVersionId != null ? S.precioVersionId : S.versionId)
        .then(function (d) { procesarDescomposicion(d, b); })
        .catch(function (e) {
          S.data = (S.itemIdx != null && b && b.items[S.itemIdx]) ? b.items[S.itemIdx].normaPreco : null;
          S.offline = true;
          renderSiEditor();
        });
      return;
    }
    /* sin servidor ni datos embebidos: degradar a snapshot si existe */
    if (S.servidorOk === false) {
      S.data = (S.itemIdx != null && b && b.items[S.itemIdx]) ? b.items[S.itemIdx].normaPreco : null;
      S.offline = true;
      return;
    }
    var url = "/api/descomposicion/" + encodeURIComponent(S.codigo);
    /* MISIÓN V: sin versiones con normas (regeneración parcial) se omite
       version_id — el servidor responde 404 controlado con explicación. */
    var qs = [];
    if (S.versionId != null) qs.push("version_id=" + S.versionId);
    if (S.precioVersionId && S.precioVersionId !== S.versionId) qs.push("precio_version_id=" + S.precioVersionId);
    if (qs.length) url += "?" + qs.join("&");
    S.offline = false;
    api(url).then(function (d) { procesarDescomposicion(d, b); })
      .catch(function (e) {
        S.servidorOk = false;
        S.data = (S.itemIdx != null && b && b.items[S.itemIdx]) ? b.items[S.itemIdx].normaPreco : null;
        S.offline = true;
        renderSiEditor();
      });
  }

  /* MISIÓN VIII: post-proceso común de la descomposición (API local y capa
     estática comparten el MISMO camino: error explícito, vínculo automático
     al presupuesto la primera vez, render). */
  function procesarDescomposicion(d, b) {
    if (d.error) { S.data = d; renderSiEditor(); return; }
    S.data = d;
    /* vínculo automático la primera vez que se consulta una partida del
       presupuesto (persistencia por defecto; inmutable salvo acción explícita) */
    if (S.itemIdx != null && b && b.items[S.itemIdx] && !b.items[S.itemIdx].normaPreco) {
      vincular(b, null);
    } else {
      renderSiEditor();
    }
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
      catch (e) { /* la pestaña original ya está renderizada: nunca romper PRECOST.
                       El error queda registrado para diagnóstico (no rompe nada). */
        window.__pcod2err = (e && e.stack) || String(e);
        if (typeof console !== "undefined" && console.warn) console.warn("pcod2:", e);
      }
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
