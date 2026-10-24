#!/usr/bin/env bash
# ============================================================================
# MISIÓN VII · Validación reproducible en navegador — RESPALDO/RESTAURACIÓN
# (S-005: exportación/importación completa de los datos del usuario)
# ============================================================================
# Criterio de aceptación (MATRIZ_PARIDAD M1, manual SIECONS pág. 14):
#   abrir PRECOST → botón «Respaldo» (abajo-izquierda) → panel con estado →
#   presupuestos + plantillas + configuración en el navegador →
#   generar respaldo (JSON) → BORRAR TODO el localStorage → recargar →
#   datos perdidos → restaurar desde el respaldo → recargar → TODO
#   recuperado BIT A BIT (presupuestos, plantillas y tema exactos) →
#   archivos inválidos rechazados SIN escrituras parciales →
#   Alt+B abre / Esc cierra → 0 errores de consola.
#
# Uso:  bash scripts/validar_vii_navegador.sh [URL_BASE]
#   Sin argumento: valida la versión local con servidor (http://127.0.0.1:8765)
#   Con URL: valida cualquier despliegue (p. ej. https://nardian90.github.io/Precost
#   o http://127.0.0.1:8877/dist para el artefacto estático).
# Requisitos: agent-browser; la BD local solo se necesita en modo servidor.
# ============================================================================
set -u
BASE="${1:-http://127.0.0.1:8765}"
FALLOS=0
ok(){ echo "  ✓ $1"; }
mal(){ echo "  ✗ $1"; FALLOS=$((FALLOS+1)); }
bval(){ python3 -c "import json,sys; print(json.loads(sys.argv[1] or 'null'))" "$1" 2>/dev/null; }
# agent-browser eval devuelve las cadenas como JSON escapado; jstr las decodifica
jstr(){ python3 -c '
import json,sys
s = sys.stdin.read().strip()
print(json.loads(s) if s.startswith(chr(34)) else s)' 2>/dev/null; }

echo "=== MISIÓN VII — Validación en navegador: respaldo S-005 ($BASE) ==="

agent-browser dialog accept > /dev/null 2>&1 || true   # limpiar diálogos residuales
agent-browser open "$BASE/" > /dev/null 2>&1 || { echo "  ✗ no se pudo abrir $BASE"; exit 1; }
agent-browser wait --load networkidle > /dev/null 2>&1
sleep 2

# capturar errores de consola de toda la sesión
agent-browser eval "window.__errs=[];window.addEventListener('error',function(e){__errs.push(String(e.message))});window.addEventListener('unhandledrejection',function(e){__errs.push('rej:'+String(e.reason))});window.confirm=function(){return true};true" > /dev/null 2>&1

# ---------- UI: FAB, panel, atajos ----------
R=$(agent-browser eval "!!document.getElementById('pcod4-fab')" 2>/dev/null)
check(){ if [ "$1" = "true" ]; then ok "$2"; else mal "$2"; fi; }
check "$R" "1) botón «Respaldo» presente (abajo-izquierda)"

R=$(agent-browser eval "document.getElementById('pcod4-fab').click(); document.getElementById('pcod4-mask').classList.contains('pcod4-open')" 2>/dev/null)
check "$R" "2) el botón abre el panel de respaldo"

R=$(agent-browser eval "document.getElementById('pcod4-estado').textContent.length > 20" 2>/dev/null)
check "$R" "3) el panel muestra el estado real (claves/presupuestos)"

R=$(agent-browser eval "document.getElementById('pcod4-exportar') && !!document.getElementById('pcod4-restaurar')" 2>/dev/null)
check "$R" "4) botones Exportar y Restaurar presentes"

R=$(agent-browser eval "document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); !document.getElementById('pcod4-mask').classList.contains('pcod4-open')" 2>/dev/null)
check "$R" "5) Esc cierra el panel"

R=$(agent-browser eval "document.dispatchEvent(new KeyboardEvent('keydown',{key:'b',altKey:true,bubbles:true})); document.getElementById('pcod4-mask').classList.contains('pcod4-open')" 2>/dev/null)
check "$R" "6) Alt+B abre el panel (atajo de teclado)"

# ---------- preparar datos reales: presupuesto + plantilla + tema ----------
agent-browser eval "
localStorage.clear();
var A=emptyBudget('VII-respaldo');
A.items.push({codigo:'012141',descripcion:(DB.P['012141']||['?'])[0],um:'m3',tipo:'partida',flags:'MHE',cantidad:2.5,precio:null,coef:1,capitulo:'1221',subcapitulo:'0121'});
state.budgets.unshift(A); state.currentId=A.id; LS.set('currentId',A.id);
saveBudgets();
LS.set('userTemplates','[{\"nombre\":\"Plantilla-VII\",\"capitulos\":[]}]}');
LS.set('theme','claro');
true" > /dev/null 2>&1
sleep 1

R=$(agent-browser eval "JSON.parse(localStorage.getItem('p3pro.budgets')).some(function(b){return b.nombre==='VII-respaldo'})" 2>/dev/null)
check "$R" "7) setup: presupuesto VII-respaldo + plantilla + tema en localStorage"

# ---------- exportación ----------
R=$(agent-browser eval "var r=window.__pcodRespaldoAPI.generar(); window.__resp=r; JSON.stringify({app:r.app, formato:r.formato, n:r.claves, tieneB:('p3pro.budgets' in r.datos), tieneT:('p3pro.userTemplates' in r.datos), tieneTe:('p3pro.theme' in r.datos)})" 2>/dev/null | jstr)
echo "$R" | grep -q '"app":"PRECOST"' && ok "8) generarRespaldo: app=PRECOST" || mal "8) app incorrecta: $R"
echo "$R" | grep -q '"formato":1' && ok "    formato=1" || mal "    formato incorrecto"
echo "$R" | grep -q '"n":[0-9]' && ok "    claves=$(echo "$R" | grep -o '"n":[0-9]*' | grep -o '[0-9]*')" || mal "    sin claves"
echo "$R" | grep -q '"tieneB":true' && echo "$R" | grep -q '"tieneT":true' && echo "$R" | grep -q '"tieneTe":true' && ok "    incluye budgets + userTemplates + theme" || mal "    faltan claves esperadas"

# respaldo completo a variable bash (para el round-trip)
GUARDAR=$(agent-browser eval "JSON.stringify(window.__resp.datos)" 2>/dev/null)

# valores exactos ANTES (para comparación bit a bit)
ANTES_B=$(agent-browser eval "localStorage.getItem('p3pro.budgets')" 2>/dev/null)
ANTES_T=$(agent-browser eval "localStorage.getItem('p3pro.userTemplates')" 2>/dev/null)
ANTES_TE=$(agent-browser eval "localStorage.getItem('p3pro.theme')" 2>/dev/null)

# ---------- catástrofe: borrar TODO y recargar ----------
agent-browser eval "localStorage.clear(); true" > /dev/null 2>&1
agent-browser open "$BASE/" > /dev/null 2>&1
agent-browser wait --load networkidle > /dev/null 2>&1
sleep 2
R=$(agent-browser eval "localStorage.length === 0 || localStorage.getItem('p3pro.budgets') === null" 2>/dev/null)
check "$R" "9) tras borrar localStorage y recargar: NO hay presupuestos (pérdida simulada)"

# ---------- restauración ----------
R=$(agent-browser eval "
var obj={app:'PRECOST',formato:1,fecha:'2026-10-24T00:00:00Z',claves:0,datos:JSON.parse($GUARDAR)};
var r=window.__pcodRespaldoAPI.aplicar(obj);
JSON.stringify(r)" 2>/dev/null | jstr)
echo "$R" | grep -q '"ok":true' && ok "10) aplicarRespaldo: ok=true" || mal "10) aplicarRespaldo falló: $R"

agent-browser open "$BASE/" > /dev/null 2>&1
agent-browser wait --load networkidle > /dev/null 2>&1
sleep 2
R=$(agent-browser eval "JSON.parse(localStorage.getItem('p3pro.budgets')).some(function(b){return b.nombre==='VII-respaldo'})" 2>/dev/null)
check "$R" "11) tras recargar: presupuesto VII-respaldo RECUPERADO"

DESPUES_B=$(agent-browser eval "localStorage.getItem('p3pro.budgets')" 2>/dev/null)
DESPUES_T=$(agent-browser eval "localStorage.getItem('p3pro.userTemplates')" 2>/dev/null)
DESPUES_TE=$(agent-browser eval "localStorage.getItem('p3pro.theme')" 2>/dev/null)
[ "$ANTES_B" = "$DESPUES_B" ] && ok "12) p3pro.budgets recuperado BIT A BIT (idéntico)" || mal "12) budgets difiere tras restaurar"
[ "$ANTES_T" = "$DESPUES_T" ] && ok "13) p3pro.userTemplates recuperado bit a bit" || mal "13) userTemplates difiere"
[ "$ANTES_TE" = "$DESPUES_TE" ] && ok "14) p3pro.theme recuperado bit a bit" || mal "14) theme difiere"

R=$(agent-browser eval "typeof state !== 'undefined' && state.budgets.some(function(b){return b.nombre==='VII-respaldo'})" 2>/dev/null)
check "$R" "15) la app cargó el presupuesto restaurado en su estado interno"

# ---------- rechazo de archivos inválidos (sin escrituras parciales) ----------
R=$(agent-browser eval "var n=window.__pcodRespaldoAPI.claves().length; var r=window.__pcodRespaldoAPI.aplicar({app:'PRECOST',formato:1,datos:{'evil.key':'x'}}); JSON.stringify({r:r, n2:window.__pcodRespaldoAPI.claves().length, escribio: localStorage.getItem('evil.key') !== null, n: n})" 2>/dev/null | jstr)
echo "$R" | grep -q '"ok":false' && ok "16) respaldo con clave sin prefijo p3pro. RECHAZADO" || mal "16) aceptó clave sin prefijo: $R"
echo "$R" | grep -q '"escribio":false' && ok "    nada se escribió (sin escrituras parciales)" || mal "    escribió la clave prohibida"
echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d['n']==d['n2'] else 1)" 2>/dev/null && ok "    conteo de claves p3pro.* intacto" || mal "    el conteo de claves cambió"

R=$(agent-browser eval "var r=window.__pcodRespaldoAPI.aplicar({foo:1}); JSON.stringify(r)" 2>/dev/null | jstr)
echo "$R" | grep -q '"ok":false' && ok "17) archivo ajeno ({foo:1}) rechazado" || mal "17) aceptó archivo ajeno: $R"

R=$(agent-browser eval "var r=window.__pcodRespaldoAPI.aplicar({app:'PRECOST',formato:1,datos:{'p3pro.budgets':123}}); JSON.stringify(r)" 2>/dev/null | jstr)
echo "$R" | grep -q '"ok":false' && ok "18) valor no-texto rechazado" || mal "18) aceptó valor no texto: $R"

R=$(agent-browser eval "var r=window.__pcodRespaldoAPI.aplicar({app:'PRECOST',formato:99,datos:{'p3pro.budgets':'[]'}}); JSON.stringify(r)" 2>/dev/null | jstr)
echo "$R" | grep -q '"ok":false' && ok "19) formato desconocido rechazado" || mal "19) aceptó formato desconocido: $R"

R=$(agent-browser eval "JSON.parse(localStorage.getItem('p3pro.budgets')).some(function(b){return b.nombre==='VII-respaldo'})" 2>/dev/null)
check "$R" "20) los datos legítimos SIGUEN intactos tras los rechazos"

# ---------- consola ----------
# (el historial de agent-browser persiste a través de las recargas del test)
ERRORES=$(agent-browser console 2>/dev/null | grep -ci "error" || true)
[ "$ERRORES" = "0" ] && ok "21) 0 errores de consola durante toda la sesión" || { mal "21) $ERRORES entradas con error"; agent-browser console 2>/dev/null | grep -i "error" | head -5; }

# ---------- limpieza: dejar el navegador como estaba ----------
agent-browser eval "localStorage.clear(); true" > /dev/null 2>&1

echo ""
if [[ $FALLOS -eq 0 ]]; then
  echo "=== RESUMEN: validación S-005 SUPERADA (21 comprobaciones) ==="
else
  echo "=== RESUMEN: $FALLOS fallos — revisar antes de publicar ==="
fi
exit $FALLOS
