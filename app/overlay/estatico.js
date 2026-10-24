/* ============================================================================
 * OVERLAY DATOS ESTÁTICOS — MISIÓN VIII (paridad «literal» en la web pública)
 * ----------------------------------------------------------------------------
 * Script 100% ADITIVO y WEB-ONLY: lo inyecta construir_web.py en dist/ (el
 * servidor local NO lo inyecta: allí la API /api/* ya sirve los datos). El
 * archivo PRECOST-v9.17.html en disco NO se modifica.
 *
 * Expone window.__pcodEstatico: una capa de datos que replica EXACTAMENTE
 * las respuestas del servidor local (scripts/servidor_precodi.py) leyendo los
 * JSON embebidos de dist/data/ (generados por scripts/generar_datos_web.py
 * desde bd/precodi.db, conteos verificados):
 *
 *   i.json            índice de versiones (ids de BD) + tipos_recurso
 *   p-<slug>.json     partidas por versión            (como /api/partidas)
 *   n-<slug>.json     normas por partida + hijos      (como /api/descomposicion)
 *   r-<slug>.json     nomenclador de recursos         (como /api/recursos)
 *
 * Reglas replicadas del servidor (documentadas en FASE_III_INTEGRACION.md y
 * INFORME_FASE_V): búsqueda LIKE ASCII-insensitive (igual que SQLite NOCASE),
 * resolución de precios por versión fuente con precio de respaldo propio,
 * advertencias con los mismos textos, duplicados, subtotales por tipo,
 * verificación CMMN/CHMN/CEMN con la tolerancia
 * |Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8) — aquí en doble precisión JS
 * (el servidor suma en Decimal y exporta float; la tolerancia absorbe la
 * diferencia de redondeo: paridad funcional documentada).
 * ==========================================================================*/
(function () {
  "use strict";
  if (window.__pcodEstatico) return;            // idempotente
  window.__pcodEstatico = true;

  var BASE = "data/";                           // rutas relativas (compatible /Precost/)
  var cache = {};                              // slug → Promise(datos)

  /* ---- utilidades ----------------------------------------------------- */
  function fetchJSON(ruta) {
    return fetch(ruta).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status + " al cargar " + ruta);
      return r.json();
    });
  }
  function cargar(nombre) {                     // con caché por archivo
    if (!cache[nombre]) cache[nombre] = fetchJSON(BASE + nombre);
    return cache[nombre];
  }
  var indiceP = null;
  function indice() {
    if (!indiceP) indiceP = cargar("i.json");
    return indiceP;
  }
  /* SQLite LIKE es ASCII case-insensitive por defecto (y COLLATE NOCASE
     también): replicamos el plegado SOLO ASCII, igual que el servidor. */
  function upperA(s) {
    return String(s == null ? "" : s).replace(/[a-z]/g, function (c) { return c.toUpperCase(); });
  }
  function como(q, texto) { return upperA(texto).indexOf(upperA(q)) >= 0; }

  function porSlug(slugP, vid) {                // archivo de partidas de la versión
    return cargar("p-" + slug(vid) + ".json").then(function (d) { return d.partidas; });
  }
  var slugs = null;                             // id → slug (del índice)
  function slug(vid) {
    if (!slugs) throw new Error("índice no cargado: llame a versiones() primero");
    var s = slugs[vid];
    if (!s) throw new Error("versión " + vid + " no existe en los datos embebidos");
    return s;
  }
  function filaPartida(filas, codigo) {         // búsqueda exacta por código
    for (var i = 0; i < filas.length; i++) if (filas[i][0] === codigo) return filas[i];
    return null;
  }
  function partidaObj(f, v) {                   // fila compacta → objeto del API
    return {
      codigo: f[0], descripcion: f[1], unidad: f[2], factor_unidad: f[3], capitulo: f[4],
      costo_mat_mn: f[5], costo_mo_mn: f[6], costo_eq_mn: f[7], costo_total_mn: f[8],
      costo_mat_mlc: f[9], version: v.version, catalogo: v.catalogo
    };
  }

  /* ---- /api/versiones -------------------------------------------------- */
  function versiones() {
    return indice().then(function (ix) {
      slugs = {};
      ix.versiones.forEach(function (v) { slugs[v.id] = v.slug; });
      return { versiones: ix.versiones, html_original_intacto: true };
    });
  }
  function verDe(vid) {                         // metadatos de la versión (índice)
    return indice().then(function (ix) {
      var v = ix.versiones.filter(function (x) { return x.id === vid; })[0];
      if (!v) throw new Error("versión " + vid + " inexistente");
      slugs = slugs || {};
      ix.versiones.forEach(function (x) { slugs[x.id] = x.slug; });
      return v;
    });
  }
  /* Versión de normas por defecto — MISMA regla documentada del servidor:
     2017-raíz > 2011-sbd2008 > 2007-v7.22 > 2007-v7.21. */
  function versionNormasDefecto(ix) {
    var orden = ["2017-raiz", "2011-sbd2008", "2007-v7.22", "2007-v7.21"];
    var conNormas = ix.versiones.filter(function (v) { return v.normas > 0; });
    for (var i = 0; i < orden.length; i++) {
      for (var j = 0; j < conNormas.length; j++) if (conNormas[j].version === orden[i]) return conNormas[j].id;
    }
    return conNormas.length ? conNormas[conNormas.length - 1].id : null;
  }

  /* ---- /api/partidas ---------------------------------------------------- */
  function partidas(q, versionId, limite) {
    limite = Math.min(limite || 60, 500);
    return indice().then(function (ix) {
      slugs = slugs || {}; ix.versiones.forEach(function (v) { slugs[v.id] = v.slug; });
      var vid = versionId != null ? versionId : ix.versiones[ix.versiones.length - 1].id;
      return verDe(vid).then(function (v) {
        return porSlug(v.slug, vid).then(function (filas) {
          var out = [];
          for (var i = 0; i < filas.length && out.length < limite; i++) {
            if (!q || como(q, filas[i][0]) || como(q, filas[i][1])) out.push(partidaObj(filas[i], v));
          }
          return { q: q || "", resultados: out, n: out.length };
        });
      });
    });
  }

  /* ---- otras versiones (misma partida en el resto de versiones) ---------- */
  function otrasVersiones(codigo, vidActual) {
    return indice().then(function (ix) {
      var tareas = ix.versiones.filter(function (v) { return v.id !== vidActual; })
        .map(function (v) {
          return porSlug(v.slug, v.id).then(function (filas) {
            var f = filaPartida(filas, codigo);
            return f ? { version_id: v.id, catalogo: v.catalogo, version: v.version,
                         costo_total_mn: f[8], unidad: f[2] } : null;
          }).catch(function () { return null; });
        });
      return Promise.all(tareas).then(function (rs) {
        return rs.filter(function (r) { return r; });
      });
    });
  }

  /* ---- /api/partida/<codigo> --------------------------------------------- */
  function partida(codigo, versionId) {
    return indice().then(function (ix) {
      var vid = versionId != null ? versionId : versionNormasDefecto(ix);
      return verDe(vid).then(function (v) {
        return porSlug(v.slug, vid).then(function (filas) {
          var f = filaPartida(filas, codigo);
          if (!f) return { error: "partida no encontrada", codigo: codigo };
          var p = partidaObj(f, v);
          p.fecha_importacion = v.fecha_importacion;
          p.fuente_archivo = v.fuente_archivo; p.fuente_sha256 = v.fuente_sha256;
          return cargarNormas(v, vid).then(function (normas) {
            var filasN = normas[codigo] || [];
            var out = [], sumas = {}, nTerms = 0, sumaAbs = 0.0;
            filasN.forEach(function (n) {
              var comp = {
                tipo: n[0], tipo_nombre: n[1], codigo_recurso: n[2], coeficiente: n[3],
                cod_norma: n[4], um_norma: n[5], recurso_desc: n[6], recurso_um: n[7],
                precio_mn: n[8], precio_mlc: n[9],
                subtotal: (n[3] || 0) * (n[8] || 0), componentes: []
              };
              (n[10] || []).forEach(function (h) {
                comp.componentes.push({
                  codigo_componente: h[2], tipo_componente: h[0], coeficiente: h[3],
                  descripcion: h[4], unidad: h[5], precio_mn: h[6],
                  subtotal: (h[3] || 0) * (h[6] || 0)
                });
              });
              var d = (n[3] || 0) * (n[8] || 0);
              sumas[comp.tipo] = (sumas[comp.tipo] || 0) + d;
              nTerms++; sumaAbs += Math.abs(d);
              out.push(comp);
            });
            var tol = Math.max(0.0001 * Math.max(1, nTerms), sumaAbs * 6e-8);
            function cmp(almacenado, recalculado) {
              if (almacenado == null) return null;
              var delta = recalculado - almacenado;
              return { almacenado: almacenado, recalculado: recalculado, delta: delta,
                       coincide: Math.abs(delta) <= tol, tolerancia: tol };
            }
            var verif = {
              cmmn: cmp(f[5], (sumas.material || 0) + (sumas.juego || 0) + (sumas.semielaborado || 0)),
              chmn: cmp(f[6], sumas.mano_obra || 0),
              cemn: cmp(f[7], sumas.equipo || 0),
              regla: "|Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8) — tolerancia por número de " +
                     "términos y magnitud, documentada en docs/FASE_III_INTEGRACION.md"
            };
            return otrasVersiones(codigo, vid).then(function (otras) {
              return { partida: p, normas: out, subtotales: sumas, verificacion: verif,
                       otras_versiones: otras, html_original_intacto: true };
            });
          });
        });
      });
    });
  }

  function cargarNormas(v, vid) {
    if (!v.normas) return Promise.resolve({});
    return cargar("n-" + v.slug + ".json").then(function (d) { return d.normas; });
  }

  /* ---- /api/recursos ------------------------------------------------------ */
  function recursos(q, tipo, versionId, limite) {
    limite = Math.min(limite || 30, 200);
    return indice().then(function (ix) {
      slugs = slugs || {}; ix.versiones.forEach(function (v) { slugs[v.id] = v.slug; });
      if (tipo && !ix.tipos_recurso.some(function (t) { return t.codigo === tipo; })) {
        return { error: "tipo desconocido", tipos_validos: ix.tipos_recurso };
      }
      /* versión por defecto del nomenclador — regla documentada del servidor:
         la de normas por defecto si tiene nomenclador; si no, la última con
         recursos (con la BD completa: 2017-raíz). */
      var vid = versionId != null ? versionId : (function () {
        var vn = versionNormasDefecto(ix);
        var conRec = ix.versiones.filter(function (v) { return v.recursos > 0; });
        if (vn != null && conRec.some(function (v) { return v.id === vn; })) return vn;
        return conRec.length ? conRec[conRec.length - 1].id : null;
      })();
      if (vid == null) return { error: "ninguna versión con recursos en la BD" };
      return verDe(vid).then(function (v) {
        return cargar("r-" + v.slug + ".json").then(function (d) {
          var filas = d.recursos, out = [];
          for (var i = 0; i < filas.length && out.length < limite; i++) {
            var r = filas[i];                    // [tipo, tipo_nombre, codigo, desc, um, pMN, pMLC]
            if (tipo && r[0] !== tipo) continue;
            if (q && !como(q, r[2]) && !como(q, r[3])) continue;
            var otros = [];
            for (var j = 0; j < filas.length && otros.length < 3; j++) {
              if (filas[j][2] === r[2] && filas[j][0] !== r[0]) otros.push(filas[j][0]);
            }
            out.push({ tipo: r[0], tipo_nombre: r[1], codigo: r[2], descripcion: r[3],
                       unidad: r[4], precio_mn: r[5], precio_mlc: r[6],
                       sin_precio: r[5] == null, mismo_codigo_otro_tipo: otros });
          }
          return { q: q || "", tipo: tipo || null, n: out.length, version_id: vid,
                   version: { catalogo: v.catalogo, version: v.version },
                   resultados: out, html_original_intacto: true };
        });
      });
    });
  }

  /* ---- /api/descomposicion/<codigo> — réplica completa de III-C ------------ */
  function descomposicion(codigo, versionId, precioVersionId) {
    return indice().then(function (ix) {
      var vid = versionId != null ? versionId : versionNormasDefecto(ix);
      if (vid == null) {
        return { error: "ninguna versión con normas disponible en la BD " +
                        "(solo PRECOST 2025, sin normas de composición: " +
                        "regeneración parcial, ver INFORME_FASE_V)", codigo: codigo };
      }
      var vidP = precioVersionId != null ? precioVersionId : vid;
      return verDe(vid).then(function (v) {
        return porSlug(v.slug, vid).then(function (filasP) {
          var f = filaPartida(filasP, codigo);
          if (!f) {                              // ¿existe en otras versiones?
            return otrasVersiones(codigo, -1).then(function (todas) {
              return { error: "partida no encontrada en la versión solicitada",
                       codigo: codigo,
                       versiones_disponibles: todas.map(function (o) {
                         return { version_id: o.version_id, version: o.version }; }) };
            });
          }
          var p = partidaObj(f, v);
          p.fecha_importacion = v.fecha_importacion;
          p.fuente_archivo = v.fuente_archivo; p.fuente_sha256 = v.fuente_sha256;
          return cargarNormas(v, vid).then(function (normas) {
            var filasN = normas[codigo] || [];
            return nomenclador(vidP).then(function (nomPrecios) {
              return verDe(vidP).then(function (vP) {
                /* nomenclador de la PROPIA versión (para descripciones/um) */
                return nomenclador(vid).then(function (nomPropio) {
                  var advertencias = [], componentes = [], duplicados = [], vistos = {};
                  filasN.forEach(function (n) {
                    var tipo = n[0], cod = n[2], coef = n[3];
                    var clave = tipo + "|" + cod;
                    vistos[clave] = (vistos[clave] || 0) + 1;
                    if (vistos[clave] === 2) duplicados.push({ tipo: tipo, codigo: cod });
                    var propio = nomPropio ? nomPropio[tipo + "|" + cod] : null;
                    var pr = nomPrecios ? nomPrecios[tipo + "|" + cod] : null;
                    var comp = {
                      tipo: tipo, tipo_nombre: n[1], codigo: cod, descripcion: propio ? propio[0] : null,
                      unidad: propio ? propio[1] : null, coeficiente: coef,
                      cod_norma: n[4], um_norma: n[5],
                      precio_mn: pr ? pr[2] : null,
                      resuelto: propio != null,
                      precio_resuelto: !!(pr && pr[2] != null),
                      hijos: []
                    };
                    if (!comp.resuelto) {
                      comp.advertencia = "referencia no resuelta en el nomenclador de " +
                        "la versión " + v.version + ": se conserva código y coeficiente de origen";
                      advertencias.push(tipo + " " + cod + ": sin nomenclador en versión " + v.version);
                    } else if (!comp.precio_resuelto) {
                      var amb = nomPrecios ? buscarOtroTipo(nomPrecios, cod, tipo) : null;
                      comp.advertencia = "sin precio en la versión de precios solicitada" +
                        (amb ? " (el código existe allí como tipo «" + amb + "») — se usa el precio " +
                               "propio de la versión de la norma"
                             : " — se usa el precio propio de la versión de la norma");
                      comp.precio_mn = propio ? propio[2] : null;   // respaldo: nomenclador propio
                      comp.precio_respaldo = true;
                      advertencias.push(tipo + " " + cod + ": sin precio en la versión de precios seleccionada");
                    } else if (pr && propio && pr[1] && propio[1] && pr[1] !== propio[1]) {
                      comp.advertencia = "unidad distinta entre versiones: norma «" +
                        propio[1] + "» vs precios «" + pr[1] + "»";
                    }
                    comp.importe = comp.precio_mn != null ? (coef || 0) * comp.precio_mn : null;
                    /* hijos (juegos/semielaborados): descomposición anidada */
                    if ((tipo === "juego" || tipo === "semielaborado") && propio) {
                      (n[10] || []).forEach(function (h) {
                        var hPropio = nomPropio ? nomPropio[h[0] + "|" + h[2]] : null;
                        var hPr = nomPrecios ? nomPrecios[h[0] + "|" + h[2]] : null;
                        var hijo = {
                          tipo: h[0], tipo_nombre: h[1], codigo: h[2],
                          descripcion: hPropio ? hPropio[0] : (h[4] != null ? h[4] : null),
                          unidad: hPropio ? hPropio[1] : (h[5] != null ? h[5] : null),
                          coeficiente: h[3], precio_mn: hPr ? hPr[2] : null,
                          resuelto: !!(hPropio || h[4] != null),
                          precio_resuelto: !!(hPr && hPr[2] != null)
                        };
                        if (hPr && hPropio && hPr[1] && hPropio[1] && hPr[1] !== hPropio[1]) {
                          hijo.advertencia = "unidad distinta entre versiones: norma «" +
                            hPropio[1] + "» vs precios «" + hPr[1] + "»";
                        }
                        hijo.importe = hijo.precio_mn != null ? (h[3] || 0) * hijo.precio_mn : null;
                        comp.hijos.push(hijo);
                      });
                    }
                    componentes.push(comp);
                  });
                  duplicados.forEach(function (d) {
                    advertencias.push("código duplicado en la norma: " + d.tipo + " " + d.codigo +
                                      " (se muestran todas las filas de origen)");
                  });
                  /* subtotales por tipo sobre componentes de primer nivel */
                  var subtotales = {}, nTerms = 0, sumaAbs = 0.0;
                  componentes.forEach(function (c) {
                    if (c.importe == null) return;
                    var d = (c.coeficiente || 0) * c.precio_mn;
                    subtotales[c.tipo] = (subtotales[c.tipo] || 0) + d;
                    nTerms++; sumaAbs += Math.abs(d);
                  });
                  var total = 0.0;
                  Object.keys(subtotales).forEach(function (k) { total += subtotales[k]; });
                  /* verificación SOLO con precios de la misma versión */
                  var verificacion = null;
                  if (vidP === vid && componentes.length) {
                    var tol = Math.max(0.0001 * Math.max(1, nTerms), sumaAbs * 6e-8);
                    function cmp(almacenado, recalculado) {
                      if (almacenado == null) return null;
                      var delta = recalculado - almacenado;
                      return { almacenado: almacenado, recalculado: recalculado, delta: delta,
                               coincide: Math.abs(delta) <= tol, tolerancia: tol };
                    }
                    verificacion = {
                      cmmn: cmp(f[5], (subtotales.material || 0) + (subtotales.juego || 0) +
                                     (subtotales.semielaborado || 0)),
                      chmn: cmp(f[6], subtotales.mano_obra || 0),
                      cemn: cmp(f[7], subtotales.equipo || 0),
                      regla: "|Δ| ≤ max(0.0001·N, Σ|coef·precio|·6e-8) — tolerancia por número " +
                             "de términos y magnitud (docs/FASE_III_INTEGRACION.md)"
                    };
                  }
                  /* informe de compatibilidad de la fuente de precios */
                  var fuentes_precio = null;
                  if (vidP !== vid) {
                    var resueltos = componentes.filter(function (c) { return c.precio_resuelto; }).length;
                    var unidadesDistintas = [];
                    componentes.forEach(function (c) {
                      if (c.resuelto && c.precio_resuelto && c.advertencia &&
                          c.advertencia.indexOf("unidad distinta") >= 0) {
                        unidadesDistintas.push({ tipo: c.tipo, codigo: c.codigo });
                      }
                    });
                    fuentes_precio = {
                      version_normas: { version: v.version, catalogo: v.catalogo },
                      version_precios: { version: vP.version, catalogo: vP.catalogo },
                      resueltos: resueltos, total: componentes.length,
                      porcentaje: componentes.length
                        ? Math.round(1000.0 * resueltos / componentes.length) / 10 : 0.0,
                      sin_resolver: componentes.filter(function (c) { return !c.precio_resuelto; })
                        .map(function (c) { return c.tipo + " " + c.codigo; }),
                      recursos_unidad_distinta: unidadesDistintas
                    };
                  }
                  return otrasVersiones(codigo, vid).then(function (otras) {
                    otras = otras.map(function (o) {
                      o.n_normas = 0;            /* el conteo por versión requiere n-*.json;
                                                   precodi.js no lo usa y recursos.js tampoco */
                      return o;
                    });
                    return { partida: p, tiene_norma: componentes.length > 0,
                             componentes: componentes, subtotales: subtotales, total: total,
                             verificacion: verificacion, fuentes_precio: fuentes_precio,
                             duplicados: duplicados, advertencias: advertencias,
                             otras_versiones: otras, html_original_intacto: true };
                  });
                });
              });
            });
          });
        });
      });
    });
  }

  /* nomenclador de una versión como mapa "tipo|codigo" → [desc, um, precio] */
  var nomCache = {};
  function nomenclador(vid) {
    if (nomCache[vid] !== undefined) return Promise.resolve(nomCache[vid]);
    return verDe(vid).then(function (v) {
      if (!v.recursos) { nomCache[vid] = null; return null; }
      return cargar("r-" + v.slug + ".json").then(function (d) {
        var m = {};
        d.recursos.forEach(function (r) { m[r[0] + "|" + r[2]] = [r[3], r[4], r[5]]; });
        nomCache[vid] = m;
        return m;
      });
    }).catch(function () { nomCache[vid] = null; return null; });
  }
  function buscarOtroTipo(nom, codigo, tipo) {
    var claves = Object.keys(nom);
    for (var i = 0; i < claves.length; i++) {
      var bar = claves[i].indexOf("|");
      if (claves[i].slice(bar + 1) === codigo && claves[i].slice(0, bar) !== tipo) {
        return claves[i].slice(0, bar);
      }
    }
    return null;
  }

  /* ---- /api/normas_disponibles (lotes) ------------------------------------ */
  function normasDisponibles(codigos, versionId) {
    return indice().then(function (ix) {
      var vid = versionId != null ? versionId : versionNormasDefecto(ix);
      return verDe(vid).then(function (v) {
        return Promise.all([porSlug(v.slug, vid), cargarNormas(v, vid)]).then(function (rs) {
          var filas = rs[0], normas = rs[1], mapa = {};
          var enCatalogo = {};
          filas.forEach(function (f) { enCatalogo[f[0]] = true; });
          codigos.forEach(function (c) {
            var n = (normas[c] || []).length;
            mapa[c] = { en_catalogo: !!enCatalogo[c], tiene_norma: n > 0, n_normas: n };
          });
          return { version_id: vid, codigos: mapa, html_original_intacto: true };
        });
      });
    });
  }

  /* ---- API pública del overlay -------------------------------------------- */
  window.__pcodEstatico = {
    es_estatico: true,
    versiones: versiones,
    partidas: partidas,
    partida: partida,
    recursos: recursos,
    descomposicion: descomposicion,
    normasDisponibles: normasDisponibles
  };
})();
