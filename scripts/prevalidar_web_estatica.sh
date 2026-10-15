#!/usr/bin/env bash
# ============================================================================
# MISIÓN VI · Pre-validación local de la versión estática (dist/) bajo un
# SUBDIRECTORIO (http://127.0.0.1:8877/dist/) que simula la ruta de proyecto
# de GitHub Pages (/Precost/). Comprueba: carga, scripts, consola, degradación
# honesta sin servidor y núcleo PRECOST operativo.
#
# Requisitos: dist/ generado (scripts/construir_web.py) y un servidor estático
# en el puerto 8877 cuya raíz sea la raíz del repo:
#   (python3 -m http.server 8877 --bind 127.0.0.1 &)
# ============================================================================
set -u
BASE="http://127.0.0.1:8877/dist"
FALLOS=0
ok(){ echo "  ✓ $1"; }
mal(){ echo "  ✗ $1"; FALLOS=$((FALLOS+1)); }

echo "=== MISIÓN VI — Pre-validación estática bajo subdirectorio ==="

# 1) Cargar la página
agent-browser open "$BASE/" >/dev/null 2>&1 || { echo "  ✗ no se pudo abrir $BASE"; exit 1; }
agent-browser wait --load networkidle >/dev/null 2>&1
sleep 2
TIT=$(agent-browser get title 2>/dev/null)
[[ "$TIT" == *PRECOST* ]] && ok "carga bajo /dist/ (título: $TIT)" || mal "título inesperado: $TIT"

# 2) Overlays cargados (rutas relativas)
N1=$(agent-browser eval "document.querySelectorAll('script[src=\"overlay/recursos.js\"]').length" 2>/dev/null)
N2=$(agent-browser eval "document.querySelectorAll('script[src=\"overlay/calculadora.js\"]').length" 2>/dev/null)
[[ "$N1" == "1" && "$N2" == "1" ]] && ok "etiquetas overlay presentes (relativas)" || mal "overlays no inyectados ($N1/$N2)"

# 3) Overlays ejecutados (guardas idempotentes)
G1=$(agent-browser eval "window.__pcodRecursos === true" 2>/dev/null)
G2=$(agent-browser eval "window.__pcodCalc === true" 2>/dev/null)
[[ "$G1" == "true" && "$G2" == "true" ]] && ok "recursos.js y calculadora.js ejecutados" || mal "overlays no ejecutados ($G1/$G2)"

# 4) precodi.js NO presente (excluido del artefacto estático, documentado)
N3=$(agent-browser eval "document.querySelectorAll('script[src=\"overlay/precodi.js\"]').length" 2>/dev/null)
[[ "$N3" == "0" ]] && ok "precodi.js excluido como está documentado" || mal "precodi.js inesperado en estático"

# 5) Núcleo PRECOST operativo: vistas + funciones del editor
V=$(agent-browser eval "typeof go === 'function' && typeof renderTabRecursos === 'function' && typeof switchEditorTab === 'function'" 2>/dev/null)
[[ "$V" == "true" ]] && ok "núcleo PRECOST operativo (go/renderTabRecursos/switchEditorTab)" || mal "núcleo no operativo"

# 6) localStorage (persistencia de presupuestos) disponible
L=$(agent-browser eval "typeof localStorage === 'object'" 2>/dev/null)
[[ "$L" == "true" ]] && ok "localStorage disponible (persistencia de presupuestos)" || mal "localStorage no disponible"

# 7) Catálogo embebido cargado (núcleo autosuficiente)
C=$(agent-browser eval "typeof DB !== 'undefined' && typeof DB.P === 'object' && Object.keys(DB.P).length > 10000" 2>/dev/null)
[[ "$C" == "true" ]] && ok "catálogo normativo embebido cargado (DB.P > 10000 partidas)" || mal "catálogo embebido no disponible"

# 8) Presupuesto de prueba → pestaña Recursos → degradación honesta visible
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
W=$(agent-browser eval "document.body.innerHTML.indexOf('Capa local PRECODI no disponible') >= 0" 2>/dev/null)
[[ "$W" == "true" ]] && ok "aviso honesto «Capa local PRECODI no disponible» visible en pestaña Recursos" || mal "aviso de degradación no encontrado"

# 9) Persistencia del presupuesto en localStorage (guardado funcional)
P=$(agent-browser eval "JSON.parse(localStorage.getItem('p3pro.budgets')||'[]').some(function(b){return b.nombre==='Estatica-test'})" 2>/dev/null)
[[ "$P" == "true" ]] && ok "presupuesto de prueba persistido en localStorage" || mal "presupuesto no persistido"

# 10) Errores de consola
ERR=$(agent-browser console 2>/dev/null | grep -ci "error" || true)
[[ "$ERR" == "0" ]] && ok "0 errores de consola" || { echo "  ⚠ $ERR entradas con 'error' en consola:"; agent-browser console 2>/dev/null | grep -i "error" | head -5; }

echo ""
if [[ $FALLOS -eq 0 ]]; then
  echo "RESULTADO: pre-validación estática SUPERADA"
else
  echo "RESULTADO: $FALLOS fallos — revisar antes de publicar"
fi
exit $FALLOS
