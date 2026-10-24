/* MISIÓN VIII — Runner de pruebas: ejecuta el overlay estatico.js REAL en
 * Node con un shim de fetch que lee los JSON de app/web-datos desde disco.
 * Lee del stdin una lista de tareas [{op, ...}] y escribe al stdout la lista
 * de respuestas JSON (mismo orden). Así tests_viii.py compara el overlay
 * REAL contra el servidor REAL: paridad «literal» verificada, no asumida.
 */
"use strict";
const fs = require("fs");
const path = require("path");

global.window = global;                       // el overlay usa window.*

const DIR_DATOS = path.join(__dirname, "..", "app", "web-datos");
global.fetch = function (ruta) {
  const archivo = String(ruta).replace(/^data\//, "").split("?")[0];
  const rutaAbs = path.join(DIR_DATOS, archivo);
  return new Promise(function (resolve, reject) {
    fs.readFile(rutaAbs, "utf8", function (e, contenido) {
      if (e) return reject(new Error("no se puede leer " + ruta + ": " + e.message));
      resolve({ ok: true, json: function () { return Promise.resolve(JSON.parse(contenido)); } });
    });
  });
};

require(path.join(__dirname, "..", "app", "overlay", "estatico.js"));

const E = global.__pcodEstatico;
if (!E) { console.error("el overlay no expuso window.__pcodEstatico"); process.exit(2); }

let tareas = "";
process.stdin.on("data", function (d) { tareas += d; });
process.stdin.on("end", function () {
  let lista;
  try { lista = JSON.parse(tareas); } catch (e) { console.error("stdin no es JSON: " + e); process.exit(2); }
  Promise.all(lista.map(function (t) {
    try {
      if (t.op === "versiones") return E.versiones();
      if (t.op === "partidas") return E.partidas(t.q || null, t.versionId != null ? t.versionId : null, t.limite || null);
      if (t.op === "partida") return E.partida(t.codigo, t.versionId != null ? t.versionId : null);
      if (t.op === "recursos") return E.recursos(t.q || "", t.tipo || "", t.versionId != null ? t.versionId : null, t.limite || null);
      if (t.op === "descomposicion") return E.descomposicion(t.codigo, t.versionId != null ? t.versionId : null,
                                                             t.precioVersionId != null ? t.precioVersionId : null);
      if (t.op === "normasDisponibles") return E.normasDisponibles(t.codigos || [], t.versionId != null ? t.versionId : null);
      return Promise.reject(new Error("op desconocida: " + t.op));
    } catch (e) {
      return Promise.reject(e);
    }
  })).then(function (respuestas) {
    /* escritura síncrona por bloques: el write asíncrono + exit truncaba
       salidas grandes en 64 KiB (pérdida silenciosa de datos). */
    const salida = JSON.stringify(respuestas);
    for (let i = 0; i < salida.length; ) {
      const bloque = salida.slice(i, i + 16384);
      fs.writeSync(1, bloque);
      i += 16384;
    }
    process.exit(0);
  }).catch(function (e) {
    console.error(String((e && e.stack) || e));
    process.exit(1);
  });
});
