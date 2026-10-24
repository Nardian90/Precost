#!/usr/bin/env bash
# ============================================================================
# MISIÓN VI/VIII · Pre-validación local de la versión estática (dist/) bajo un
# SUBDIRECTORIO (http://127.0.0.1:8877/dist/) que simula la ruta de proyecto
# de GitHub Pages (/Precost/). Comprueba: carga, overlays, consola, MODO WEB
# con datos PRECODI embebidos (MISIÓN VIII: paridad sin servidor) y núcleo
# PRECOST operativo.
#
# Requisitos: dist/ generado (scripts/construir_web.py) y un servidor estático
# en el puerto 8877 cuya raíz sea la raíz del repo:
#   (python3 -m http.server 8877 --bind 127.0.0.1 &)
# ============================================================================
set -u
# Uso: prevalidar_web_estatica.sh [URL_BASE]
#   Sin argumento: valida el artefacto local (requiere servidor en 8877).
#   Con URL: valida cualquier despliegue (p. ej. https://nardian90.github.io/Precost).
BASE="${1:-http://127.0.0.1:8877/dist}"
FALLOS=0
ok(){ echo "  ✓ $1"; }
mal(){ echo "  ✗ $1"; FALLOS=$((FALLOS+1)); }

echo "=== MISIÓN VIII — Pre-validación estática ($BASE) ==="

# 1) Cargar la página
agent-browser open "$BASE/" >/dev/null 2>&1 || { echo "  ✗ no se pudo abrir $BASE"; exit 1; }
agent-browser wait --load networkidle >/dev/null 2>&1
sleep 2
TIT=$(agent-browser get title 2>/dev/null)
[[ "$TIT" == *PRECOST* ]] && ok "carga correcta (título: $TIT)" || mal "título inesperado: $TIT"

# 2) Overlays cargados (rutas relativas) — MISIÓN VIII: 5 overlays
N=$(agent-browser eval "document.querySelectorAll('script[src^=\"overlay/\"]').length" 2>/dev/null)
[[ "$N" == "5" ]] && ok "5 overlays inyectados con rutas relativas" || mal "se esperaban 5 overlays, hay $N"
for OV in estatico recursos calculadora respaldo precodi; do
  C=$(agent-browser eval "document.querySelectorAll('script[src=\"overlay/$OV.js\"]').length" 2>/dev/null)
  [[ "$C" == "1" ]] || mal "falta la etiqueta de $OV.js"
done

# 3) Overlays ejecutados (guardas idempotentes) — incluida la capa de datos
G1=$(agent-browser eval "window.__pcodEstatico && window.__pcodEstatico.es_estatico === true" 2>/dev/null)
G2=$(agent-browser eval "window.__pcodRecursos === true && window.__pcodCalc === true" 2>/dev/null)
G3=$(agent-browser eval "window.__pcodRespaldo === true && window.__pcodOverlay === true" 2>/dev/null)
[[ "$G1" == "true" ]] && ok "capa de datos embebidos ejecutada (__pcodEstatico)" || mal "estatico.js no ejecutado ($G1)"
[[ "$G2" == "true" && "$G3" == "true" ]] && ok "recursos/calculadora/respaldo/precodi ejecutados" || mal "overlays no ejecutados ($G2/$G3)"

# 4) Datos embebidos: índice con las versiones y normas
IDX=$(agent-browser eval "window.__pcodEstatico ? __pcodEstatico.versiones().then(function(d){var v=d.versiones.filter(function(x){return x.normas>0}); return v.length + ':' + v.map(function(x){return x.version}).join(',')}) : 'sin-capa'" 2>/dev/null)
IDX=$(echo "$IDX" | tr -d '"')
case "$IDX" in
  4:*) ok "índice embebido: versiones con normas = ${IDX#*:}" ;;
  *) mal "índice embebido inesperado: $IDX" ;;
esac

# 5) Núcleo PRECOST operativo: vistas + funciones del editor
V=$(agent-browser eval "typeof go === 'function' && typeof renderTabRecursos === 'function' && typeof switchEditorTab === 'function'" 2>/dev/null)
[[ "$V" == "true" ]] && ok "núcleo PRECOST operativo (go/renderTabRecursos/switchEditorTab)" || mal "núcleo no operativo"

# 6) localStorage (persistencia de presupuestos) disponible
L=$(agent-browser eval "typeof localStorage === 'object'" 2>/dev/null)
[[ "$L" == "true" ]] && ok "localStorage disponible (persistencia de presupuestos)" || mal "localStorage no disponible"

# 7) Catálogo embebido cargado (núcleo autosuficiente)
C=$(agent-browser eval "typeof DB !== 'undefined' && typeof DB.P === 'object' && Object.keys(DB.P).length > 10000" 2>/dev/null)
[[ "$C" == "true" ]] && ok "catálogo normativo embebido cargado (DB.P > 10000 partidas)" || mal "catálogo embebido no disponible"

# 8) MODO WEB (MISIÓN VIII): presupuesto de prueba → pestaña Recursos →
#    descomposición de 012141 servida desde los DATOS EMBEBIDOS (no degradación)
agent-browser eval "
window.confirm=function(){return true};
localStorage.clear();
var A=emptyBudget('Estatica-test');
A.items.push({codigo:'012141',descripcion:(DB.P['012141']||['?'])[0],um:'m3',tipo:'partida',flags:'MHE',cantidad:2.5,precio:null,coef:1,capitulo:'1221',subcapitulo:'0121'});
state.budgets.unshift(A); state.currentId=A.id; LS.set('currentId',A.id);
if (typeof saveBudgets === 'function') { saveBudgets(); }
go('editor'); renderEditor(); switchEditorTab('recursos');
true" >/dev/null 2>&1
sleep 4
# seleccionar la partida 012141 del presupuesto (flujo real del usuario)
agent-browser eval "var s=document.getElementById('pcod2-sel'); if(s){s.value='0'; s.dispatchEvent(new Event('change'));} true" >/dev/null 2>&1
sleep 8
W=$(agent-browser eval "document.body.innerHTML.indexOf('datos PRECODI embebidos') >= 0" 2>/dev/null)
[[ "$W" == "true" ]] && ok "aviso «Modo web — datos PRECODI embebidos» visible en pestaña Recursos" || mal "aviso de modo web no encontrado"
FIL=$(agent-browser eval "document.querySelectorAll('input.pcod2-in').length" 2>/dev/null)
case "$FIL" in
  ""|*[!0-9]*) mal "la norma de 012141 no se renderizó desde los datos embebidos (inputs: $FIL)" ;;
  *) if [ "$FIL" -ge 3 ]; then ok "tabla efectiva de la norma renderizada (inputs de edición: $FIL)";
     else mal "tabla efectiva incompleta (inputs: $FIL)"; fi ;;
esac
VINC=$(agent-browser eval "JSON.parse(localStorage.getItem('p3pro.budgets')||'[]').some(function(b){return b.nombre==='Estatica-test' && b.items.length && b.items[0].normaPreco})" 2>/dev/null)
[[ "$VINC" == "true" ]] && ok "descomposición VINCULADA y persistida en el presupuesto (normaPreco)" || mal "la descomposición no se vinculó al presupuesto"

# 9) Persistencia del presupuesto en localStorage (guardado funcional)
P=$(agent-browser eval "JSON.parse(localStorage.getItem('p3pro.budgets')||'[]').some(function(b){return b.nombre==='Estatica-test'})" 2>/dev/null)
[[ "$P" == "true" ]] && ok "presupuesto de prueba persistido en localStorage" || mal "presupuesto no persistido"

# 10) Panel de catálogo PRECODI (precodi.js) con datos embebidos: buscar «roca»
agent-browser eval "document.querySelector('.pcod-fab') && document.querySelector('.pcod-fab').click(); true" >/dev/null 2>&1
sleep 3
ETQ=$(agent-browser eval "var s=document.querySelector('.pcod-h small'); s ? s.textContent.indexOf('datos embebidos')>=0 : 'sin-panel'" 2>/dev/null)
[[ "$ETQ" == "true" ]] && ok "panel PRECODI en modo web (etiqueta: datos embebidos)" || mal "panel PRECODI no indica modo web ($ETQ)"
agent-browser eval "var i=document.getElementById('pcod-q'); if(i){i.value='roca'; document.getElementById('pcod-buscar').click();} true" >/dev/null 2>&1
sleep 4
RES=$(agent-browser eval "document.querySelectorAll('.pcod-res tr[data-cod]').length" 2>/dev/null)
RES=$(echo "$RES" | tr -d '"')
case "$RES" in
  ""|*[!0-9]*) mal "búsqueda del catálogo sin resultados ($RES)" ;;
  *) if [ "$RES" -ge 3 ]; then ok "búsqueda «roca» en el catálogo embebido: $RES resultados";
     else mal "búsqueda del catálogo con pocos resultados ($RES)"; fi ;;
esac

# 11) Detalle de la partida 012141 (normas + verificación contra fuente)
agent-browser eval "var tr=document.querySelector('.pcod-res tr[data-cod=\"012141\"]') || document.querySelector('.pcod-res tr[data-cod]'); if(tr){tr.click();} true" >/dev/null 2>&1
sleep 5
DET=$(agent-browser eval "document.body.innerHTML.indexOf('Verificación contra la fuente') >= 0" 2>/dev/null)
[[ "$DET" == "true" ]] && ok "detalle de partida con normas y verificación CMMN/CHMN/CEMN (datos embebidos)" || mal "detalle de partida sin verificación"
SEL=$(agent-browser eval "document.querySelectorAll('#pcod-ver option').length" 2>/dev/null)
SEL=$(echo "$SEL" | tr -d '"')
[ "${SEL:-0}" -ge 5 ] 2>/dev/null && ok "selector de versiones con $SEL bases (paridad con SIECONS)" || mal "selector de versiones incompleto ($SEL)"

# 12) Errores de consola
ERR=$(agent-browser console 2>/dev/null | grep -ci "error" || true)
[[ "$ERR" == "0" ]] && ok "0 errores de consola" || { echo "  ⚠ $ERR entradas con 'error' en consola:"; agent-browser console 2>/dev/null | grep -i "error" | head -5; }

echo ""
if [[ $FALLOS -eq 0 ]]; then
  echo "RESULTADO: pre-validación estática SUPERADA (MISIÓN VIII: paridad web con datos embebidos)"
else
  echo "RESULTADO: $FALLOS fallos — revisar antes de publicar"
fi
exit $FALLOS
