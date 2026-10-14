#!/usr/bin/env bash
# ============================================================================
# MISIÓN IV · FASE E — Validación reproducible en navegador de la CALCULADORA
# ============================================================================
# Criterio de aceptación de la función implementada (S-80 del manual SIECONS,
# MATRIZ_PARIDAD §M8):
#   abrir PRECOST → abrir la Calculadora (botón o Alt+C) → elegir la actividad
#   012141 → ver su descomposición (9 recursos) → editar un coeficiente y
#   comprobar el recálculo en vivo → aplicar coeficiente global 1.15 y
#   cantidad 10 → comprobar totales → guardar historial → comprobar que
#   p3pro.budgets NO se modifica → cerrar (Esc) → vistas intactas →
#   modo degradado sin servidor (fetch anulado) → 0 errores de consola.
#
# Requisitos: bd/precodi.db importada; agent-browser instalado; node.
# Uso:  bash scripts/validar_iv_navegador.sh [puerto]
# ============================================================================
set -u
PUERTO="${1:-8793}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
capturas="$REPO/docs/datos"
ok=0; fallos=0

srv() { python3 "$REPO/scripts/servidor_precodi.py" --puerto "$PUERTO" > /tmp/srv_iv_val.log 2>&1 & SRV=$!; }
trap '[ -n "${SRV:-}" ] && kill $SRV 2>/dev/null' EXIT

check() {
  if [ "$2" = "true" ]; then echo "  ✓ $1"; ok=$((ok+1));
  else echo "  ✗ FALLO: $1"; fallos=$((fallos+1)); fi
}

# extrae el valor de la salida de agent-browser eval: última línea, sin
# comillas, en minúsculas, sin espacios (tolera mensajes de arranque del CLI)
bval() {
  printf '%s' "$1" | tail -1 | tr -d '"' | tr -d "'" | tr 'A-Z' 'a-z' | tr -d '[:space:]'
}
# numérico: última línea, sin comillas, coma decimal → punto
nval() {
  printf '%s' "$1" | tail -1 | tr -d '"' | tr ',' '.'
}

echo "=== MISIÓN IV — Validación en navegador de la Calculadora (puerto $PUERTO) ==="
pkill -f "servidor_precodi.py --puerto $PUERTO" 2>/dev/null; sleep 1
srv; sleep 2

agent-browser open "http://127.0.0.1:$PUERTO/" > /dev/null 2>&1
agent-browser wait --load networkidle > /dev/null 2>&1

# estado inicial determinista + presupuesto de control (para probar que la
# calculadora NO lo toca)
agent-browser eval "
localStorage.removeItem('p3pro.budgets'); localStorage.removeItem('p3pro.currentId');
localStorage.removeItem('p3pro.calcHist'); location.reload();
" > /dev/null 2>&1; sleep 1.5
agent-browser eval "
nuevoPresupuesto();
var b = currentBudget(); b.nombre = 'Control IV';
b.items.push({codigo:'012141', descripcion: DB.P['012141'][0], um: DB.P['012141'][1], tipo:'partida', flags:'MHE', cantidad: 5, precio:null, coef:1, capitulo:'1221', subcapitulo:'0121'});
touch(b);
window.__ctrl = JSON.stringify(currentBudget());
'listo'
" > /dev/null 2>&1; sleep 0.5

# 1) botón flotante presente
R=$(agent-browser eval "!!document.getElementById('pcod3-fab')" 2>/dev/null)
check "1) botón flotante Calculadora presente" "$(bval "$R")"

# 2) abrir con Alt+C (atajo de teclado documentado)
R=$(agent-browser eval "
var ev = new KeyboardEvent('keydown', {key:'c', altKey:true, bubbles:true, cancelable:true});
document.dispatchEvent(ev); !!document.getElementById('pcod3-mask')
" 2>/dev/null)
check "2) Alt+C abre la calculadora" "$(bval "$R")"

# 3) consultar 012141
agent-browser eval "
document.getElementById('pcod3-cod').value = '012141';
document.getElementById('pcod3-go').click();
'iniciado'
" > /dev/null 2>&1; sleep 1.5
R=$(agent-browser eval "var t = document.querySelector('#pcod3-tbl'); t ? t.querySelectorAll('tbody > tr').length : -1" 2>/dev/null)
N=$(nval "$R")
check "3) descomposición de 012141 cargada (filas >= 9)" "$(python3 -c "print('true' if $N >= 9 else 'false')")"

R=$(agent-browser eval "document.querySelector('#pcod3-cuerpo') ? document.querySelector('#pcod3-cuerpo').textContent.indexOf('EN ROCA CUALQUIER SECCION') >= 0 : false" 2>/dev/null)
check "4) descripción de la partida visible" "$(bval "$R")"

# 5) subtotales oficiales visibles (CMMN/CHMN/CEMN)
R=$(agent-browser eval "var c = document.querySelector('#pcod3-cuerpo').textContent; c.indexOf('CMMN') >= 0 && c.indexOf('CHMN') >= 0 && c.indexOf('CEMN') >= 0" 2>/dev/null)
check "5) subtotales CMMN/CHMN/CEMN visibles" "$(bval "$R")"

# 6) edición de coeficiente en vivo: material 3834010001 coef 1.2 → 2.4
R=$(agent-browser eval "
var inp = document.querySelector('#pcod3-tbl input[data-pc3i=\"0\"][data-pc3f=\"coef\"]');
inp.value = '2.4'; inp.dispatchEvent(new Event('input', {bubbles:true}));
document.getElementById('pcod3-imp0').textContent
" 2>/dev/null)
IMP=$(nval "$R")
R2=$(agent-browser eval "document.getElementById('pcod3-rMat').textContent" 2>/dev/null)
MAT=$(nval "$R2")
check "6a) importe del recurso editado = 2.4 x 1.8 = 4.32" \
  "$(python3 -c "print('true' if abs(float('$IMP') - 4.32) < 0.001 else 'false')")"
check "6b) CMMN recalculado = 4.789 (2.629 + 2.16 extra)" \
  "$(python3 -c "print('true' if abs(float('$MAT') - 4.789) < 0.001 else 'false')")"

# 7) coeficiente global 1.15 y cantidad 10
agent-browser eval "
var g = document.getElementById('pcod3-glob'); g.value = '1.15';
g.dispatchEvent(new Event('input', {bubbles:true}));
var c = document.getElementById('pcod3-cant'); c.value = '10';
c.dispatchEvent(new Event('input', {bubbles:true})); 'ajustado'
" > /dev/null 2>&1; sleep 0.3
R=$(agent-browser eval "document.getElementById('pcod3-rTot').textContent" 2>/dev/null)
TOT=$(nval "$R")
R=$(agent-browser eval "document.getElementById('pcod3-rEv').textContent" 2>/dev/null)
EV=$(nval "$R")
# total base = 11.0480676…; x1.15 = 12.7052777…; x10 = 127.0527…
check "7a) total unitario ajustado x1.15 = 12.7053" \
  "$(python3 -c "print('true' if abs(float('$TOT') - 12.7052778) < 0.001 else 'false')")"
check "7b) total evaluación x10 = 127.0528" \
  "$(python3 -c "print('true' if abs(float('$EV') - 127.0527778) < 0.001 else 'false')")"

# 8) comparación contra PU oficial visible
R=$(agent-browser eval "document.querySelector('#pcod3-cuerpo').textContent.indexOf('PU motor PRECOST') >= 0" 2>/dev/null)
check "8) comparación contra PU oficial embebido visible" "$(bval "$R")"

# 9) guardado en historial (clave propia, sin tocar budgets)
agent-browser eval "document.getElementById('pcod3-hist-save').click(); 'guardado'" > /dev/null 2>&1; sleep 0.3
R=$(agent-browser eval "
var h = JSON.parse(localStorage.getItem('p3pro.calcHist') || '[]');
h.length === 1 && h[0].codigo === '012141'
" 2>/dev/null)
check "9a) historial guardado en p3pro.calcHist (1 entrada, 012141)" "$(bval "$R")"
R=$(agent-browser eval "JSON.stringify(currentBudget()) === window.__ctrl" 2>/dev/null)
check "9b) p3pro.budgets SIN cambios tras usar la calculadora" "$(bval "$R")"

# captura del flujo funcional
agent-browser screenshot "$capturas/iv_validacion_01_calculadora.png" > /dev/null 2>&1

# 10) cerrar con Esc
R=$(agent-browser eval "
var ev = new KeyboardEvent('keydown', {key:'Escape', bubbles:true});
document.dispatchEvent(ev); !document.getElementById('pcod3-mask')
" 2>/dev/null)
check "10) Esc cierra la calculadora" "$(bval "$R")"

# 11) vistas de PRECOST intactas
R=$(agent-browser eval "
var oks = [];
['inicio','catalogo','mios','reportes'].forEach(function(v){ try { go(v); oks.push(true); } catch(e){ oks.push(false); } });
go('editor');
oks.every(Boolean) && !!document.getElementById('pcod3-fab')
" 2>/dev/null)
check "11) navegación de vistas intacta + FAB persistente" "$(bval "$R")"
agent-browser screenshot "$capturas/iv_validacion_02_vistas.png" > /dev/null 2>&1

# 12) modo degradado: fetch anulado → PU embebido con aviso explícito
agent-browser eval "
window.__fetchReal = window.fetch;
window.fetch = function(){ return Promise.reject(new Error('offline simulado')); };
var ev = new KeyboardEvent('keydown', {key:'c', altKey:true, bubbles:true, cancelable:true});
document.dispatchEvent(ev); 'abierto'
" > /dev/null 2>&1; sleep 0.3
agent-browser eval "
document.getElementById('pcod3-cod').value = '011111';
document.getElementById('pcod3-go').click(); 'consultando'
" > /dev/null 2>&1; sleep 1.2
R=$(agent-browser eval "
var c = document.querySelector('#pcod3-cuerpo');
c && c.textContent.indexOf('Modo degradado') >= 0 &&
(c.textContent.indexOf('26,81') >= 0 || c.textContent.indexOf('26.81') >= 0)
" 2>/dev/null)
check "12) modo degradado honesto: PU embebido 011111 (26,81) con aviso" "$(bval "$R")"
agent-browser screenshot "$capturas/iv_validacion_03_degradado.png" > /dev/null 2>&1
agent-browser eval "window.fetch = window.__fetchReal; 'restaurado'" > /dev/null 2>&1

# 13) persistencia del historial tras recarga
agent-browser eval "location.reload()" > /dev/null 2>&1; sleep 1.5
R=$(agent-browser eval "
var ev = new KeyboardEvent('keydown', {key:'c', altKey:true, bubbles:true, cancelable:true});
document.dispatchEvent(ev);
var h = JSON.parse(localStorage.getItem('p3pro.calcHist') || '[]');
h.length === 1 && h[0].codigo === '012141'
" 2>/dev/null)
check "13) historial persiste tras recarga completa" "$(bval "$R")"

# 14) cero errores de consola
ERRORES=$(agent-browser console --errors 2>/dev/null | rg -c -i "error" || echo 0)
check "14) 0 errores de consola" "$(python3 -c "print('true' if $ERRORES == 0 else 'false')")"

# 15) integridad del HTML en disco
H=$(sha256sum "$REPO/app/PRECOST-v9.17.html" | cut -d' ' -f1)
check "15) HTML en disco byte-idéntico (SHA-256)" \
  "$(python3 -c "print('true' if '$H' == '50d3cf28e405201f36c50c3dd5385d7e28fbab3e7e5eee22c74ca0bcfd5cbaa2' else 'false')")"

echo
echo "=== RESULTADO: $ok ✓ / $fallos ✗ (de $((ok+fallos))) ==="
if [ "$fallos" -eq 0 ]; then
  echo "ACEPTACIÓN DE EXTREMO A EXTREMO: SUPERADA"
  exit 0
else
  echo "HAY FALLOS — NO DECLARAR LA MISIÓN COMPLETA"
  exit 1
fi
