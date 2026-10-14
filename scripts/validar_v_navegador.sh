#!/usr/bin/env bash
# ============================================================================
# MISIÓN V · Validación reproducible en navegador — EDICIÓN DE RECURSOS
# (S-050 indicadores M/H/E + especificación · S-052 cantidad/precio)
# ============================================================================
# Criterio de aceptación (MATRIZ_PARIDAD §M5, manual págs. 32–35):
#   abrir PRECOST → presupuesto con la partida 012141 → pestaña Recursos →
#   seleccionar la partida → ver barra M/H/E → quitar palomita M →
#   especificación activa (sombreada) → añadir recurso propio del nomenclador
#   (buscar cemento) + entrada manual con precio de 4 decimales → editar
#   cantidad y precio in-line → totales recalculados exactos → entradas
#   inválidas rechazadas → sin precio excluido con aviso → guardar
#   (autoguardado) → RECARGAR la página → reabrir el presupuesto → recuperar
#   la descomposición editada → presupuesto testigo con el MISMO código no
#   afectado → presupuesto antiguo (formato pre-V) funciona → reponer palomita
#   descarta lo especificado → S-080 Calculadora coexistente → BD y API
#   intactas → 0 errores de consola.
#
# Los pasos que requieren NORMAS de composición (edición de filas de la norma,
# «Cargar normas», desactivación por palomita de filas normativas) se marcan
# PENDIENTE si la BD no tiene versiones con normas (regeneración parcial tras
# la pérdida de fuentes — ver INFORME_FASE_V). Con la BD completa se ejecutan.
#
# Requisitos: bd/precodi.db (base precost2025 como mínimo); agent-browser; node.
# Uso:  bash scripts/validar_v_navegador.sh [puerto]
# ============================================================================
set -u
PUERTO="${1:-8795}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CAPT="$REPO/docs/datos"
ok=0; fallos=0; pendientes=0

srv() { python3 "$REPO/scripts/servidor_precodi.py" --puerto "$PUERTO" > /tmp/srv_v_val.log 2>&1 & SRV=$!; }
trap '[ -n "${SRV:-}" ] && kill $SRV 2>/dev/null' EXIT

check()  { if [ "$2" = "true" ];   then echo "  ✓ $1"; ok=$((ok+1));
           else echo "  ✗ FALLO: $1"; fallos=$((fallos+1)); fi; }
pend()   { echo "  ⏸ PENDIENTE (datos): $1"; pendientes=$((pendientes+1)); }
# extrae el valor de agent-browser eval: última línea, sin comillas
bval()  { printf '%s' "$1" | tail -1 | tr -d '"' | tr -d "'" | tr 'A-Z' 'a-z' | tr -d '[:space:]'; }
jval()  { printf '%s' "$1" | tail -1 | tr -d '"'; }
# agent-browser imprime el resultado como literal JSON (con \" escapadas):
# junesc quita las capas de escape para dejar el JSON limpio en V.
junesc() { printf '%s' "$1" | tail -1 | python3 -c "
import json,sys
s=sys.stdin.read().strip()
for _ in range(3):
    try:
        if s.startswith('\"'): s=json.loads(s)
        else: break
    except Exception: break
print(s)"; }

echo "=== MISIÓN V — Validación en navegador (puerto $PUERTO) ==="
pkill -f "servidor_precodi.py --puerto $PUERTO" 2>/dev/null; sleep 1
agent-browser dialog accept > /dev/null 2>&1 || true   # limpiar diálogos residuales

srv; sleep 2
BD1=$(sha256sum "$REPO/bd/precodi.db" | cut -d' ' -f1)
DEC1=$(curl -s "http://127.0.0.1:$PUERTO/api/descomposicion/012141" | sha256sum | cut -d' ' -f1)
REC1=$(curl -s "http://127.0.0.1:$PUERTO/api/recursos?q=cemento&limit=25" | sha256sum | cut -d' ' -f1)
# ¿hay normas de composición? (regeneración parcial → pasos pendientes)
NNORMAS=$(curl -s "http://127.0.0.1:$PUERTO/api/versiones" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin); print(sum(v.get('normas',0) for v in d.get('versiones',[])))
except Exception: print(0)")
agent-browser dialog accept > /dev/null 2>&1 || true

agent-browser open "http://127.0.0.1:$PUERTO/" > /dev/null 2>&1
agent-browser wait --load networkidle > /dev/null 2>&1

# estado determinista + presupuesto A (editado) y B (testigo, mismo código,
# formato ANTIGUO sin flags/edicionRecursos/normaPreco) + captura de errores
R=$(agent-browser eval "
window.__errs=[];
window.addEventListener('error',function(e){__errs.push(String(e.message))});
window.addEventListener('unhandledrejection',function(e){__errs.push('rej:'+String(e.reason))});
window.confirm=function(){return true};
localStorage.clear();
var A=emptyBudget('A-editada');
A.items.push({codigo:'012141',descripcion:(DB.P['012141']||['?'])[0],um:'m3',tipo:'partida',flags:'MHE',cantidad:2.5,precio:null,coef:1,capitulo:'1221',subcapitulo:'0121'});
var B=emptyBudget('B-testigo');
B.items.push({codigo:'012141',descripcion:(DB.P['012141']||['?'])[0],um:'m3',tipo:'partida',cantidad:3,precio:null,coef:1,capitulo:'1221',subcapitulo:'0121'});
state.budgets.unshift(A); state.budgets.unshift(B);
state.currentId=A.id; LS.set('currentId',A.id);
go('editor'); renderEditor();
var sel=document.getElementById('pcod2-sel'); sel.value='0'; sel.dispatchEvent(new Event('change'));
true
" 2>/dev/null)
sleep 2
check "setup: presupuesto A (2.5 m3) + B testigo mismo código (formato antiguo)" "$(bval "$R")"

# ---------- S-050: barra de palomitas ----------
R=$(agent-browser eval "JSON.stringify({bar:!!document.getElementById('pcod2-flags'),chips:document.querySelectorAll('[data-pcod2flg]').length,m:document.querySelectorAll('[data-pcod2flg]')[0].className,h:document.querySelectorAll('[data-pcod2flg]')[1].className,e:document.querySelectorAll('[data-pcod2flg]')[2].className})" 2>/dev/null)
V=$(junesc "$R")
check "1) barra M/H/E presente con 3 palomitas ON (defecto MHE)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['bar'] and d['chips']==3 and 'pcod2-on' in d['m'] and 'pcod2-on' in d['h'] and 'pcod2-on' in d['e'] else 'false')" 2>/dev/null || echo false)"

R=$(agent-browser eval "document.querySelector('[data-pcod2flg=\"M\"]').click(); JSON.stringify({ui:currentBudget().items[0].flags, ls:JSON.parse(localStorage.getItem('p3pro.budgets')).filter(function(b){return b.nombre==='A-editada'})[0].items[0].flags})" 2>/dev/null)
V=$(junesc "$R")
check "2) quitar palomita M → flags HE en el ítem Y persistido en p3pro.budgets" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['ui']=='HE' and d['ls']=='HE' else 'false')" 2>/dev/null || echo false)"

# ---------- S-052: especificación (recursos propios) ----------
R=$(agent-browser eval "document.querySelector('[data-pcod2panel=\"M\"]').click(); document.getElementById('pcod2-rec-q').value='cemento'; document.getElementById('pcod2-rec-buscar').click(); 'ok'" 2>/dev/null)
sleep 1.4
R=$(agent-browser eval "JSON.stringify({n:document.querySelectorAll('[data-pcod2resadd]').length, primero:document.querySelectorAll('[data-pcod2resadd]')[0]?document.querySelectorAll('[data-pcod2resadd]')[0].textContent.replace(/\s+/g,' ').slice(0,120):'—'})" 2>/dev/null)
V=$(junesc "$R")
check "3) búsqueda del nomenclador /api/recursos (cemento) con resultados" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['n']>0 and 'CEMENTO' in d['primero'].upper() else 'false')" 2>/dev/null || echo false)"
check "3b) aviso um ≠ um partida (litro ≠ m3) en el resultado" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if '≠' in d['primero'] or 'litro' in d['primero'] else 'false')" 2>/dev/null || echo false)"

R=$(agent-browser eval "
document.querySelector('[data-pcod2resadd]').click();
document.getElementById('pcod2-man-codigo').value='PROP-ARENA';
document.getElementById('pcod2-man-desc').value='ARENA DE RIO (propia)';
document.getElementById('pcod2-man-um').value='m3';
document.getElementById('pcod2-man-coef').value='0.375';
document.getElementById('pcod2-man-precio').value='4.5678';
document.getElementById('pcod2-man-add').click();
JSON.stringify({
  n:currentBudget().items[0].edicionRecursos.propios.material.length,
  sombra:document.querySelector('[data-pcod2flg=\"M\"]').className.indexOf('pcod2-esp')>=0,
  mods:document.querySelectorAll('.pcod2-mods li').length,
  totEf:document.getElementById('pcod2-tot-efectiva').textContent,
  totObra:document.getElementById('pcod2-tot-obra').textContent
})" 2>/dev/null)
V=$(junesc "$R")
ESP_UM=$(python3 -c "print(f'{(1*10.05+0.375*4.5678):.4f}')")
ESP_OBRA=$(python3 -c "print(f'{(1*10.05+0.375*4.5678)*2.5:.4f}')")
check "4) añadido del catálogo + manual (coef 0.375, precio 4.5678) → chip sombreado + modificaciones" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['n']==2 and d['sombra'] and d['mods']>=2 else 'false')" 2>/dev/null || echo false)"
check "5) PU descomposición efectiva = Σ coef×precio exacto ($ESP_UM)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['totEf']=='$ESP_UM' else 'false')" 2>/dev/null || echo false)"
check "6) total de obra = efectiva × cantidad 2.5 exacto ($ESP_OBRA)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['totObra']=='$ESP_OBRA' else 'false')" 2>/dev/null || echo false)"

# edición in-line + rechazo de inválidos + sin precio
R=$(agent-browser eval "
var i=document.querySelectorAll('[data-pcod2pe]');
var r={};
i[0].value='2.4'; i[0].dispatchEvent(new Event('change'));
r.trasCoef=document.getElementById('pcod2-tot-efectiva').textContent;
var i2=document.querySelectorAll('[data-pcod2pe]'); i2[3].value='5.1234'; i2[3].dispatchEvent(new Event('change'));
r.trasPrecio=document.getElementById('pcod2-tot-efectiva').textContent;
var i3=document.querySelectorAll('[data-pcod2pe]');
var prev=i3[0].value;
i3[0].value='-3'; i3[0].dispatchEvent(new Event('change'));
r.trasNeg=currentBudget().items[0].edicionRecursos.propios.material[0].coef;
r.inputRestaurado=document.querySelectorAll('[data-pcod2pe]')[0].value;
var i4=document.querySelectorAll('[data-pcod2pe]'); i4[0].value='abc'; i4[0].dispatchEvent(new Event('change'));
r.trasNaN=currentBudget().items[0].edicionRecursos.propios.material[0].coef;
var i5=document.querySelectorAll('[data-pcod2pe]'); i5[3].value=''; i5[3].dispatchEvent(new Event('change'));
r.p1=currentBudget().items[0].edicionRecursos.propios.material[1].precio;
r.trasSinPrecio=document.getElementById('pcod2-tot-efectiva').textContent;
r.avisoSinPrecio=document.body.textContent.indexOf('sin precio — excluido')>=0;
var i6=document.querySelectorAll('[data-pcod2pe]'); i6[3].value='4.5678'; i6[3].dispatchEvent(new Event('change'));
r.final=document.getElementById('pcod2-tot-efectiva').textContent;
JSON.stringify(r)
" 2>/dev/null)
V=$(junesc "$R")
E1=$(python3 -c "print(f'{(2.4*10.05+0.375*4.5678):.4f}')")
E2=$(python3 -c "print(f'{(2.4*10.05+0.375*5.1234):.4f}')")
check "7) edición in-line coef→2.4: total $E1 exacto" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['trasCoef']=='$E1' else 'false')" 2>/dev/null || echo false)"
check "8) edición in-line precio→5.1234: total $E2 exacto (4 decimales)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['trasPrecio']=='$E2' else 'false')" 2>/dev/null || echo false)"
check "9) negativo y no-numérico rechazados (coef se conserva =2.4 e input restaurado)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['trasNeg']==2.4 and d['trasNaN']==2.4 and d['inputRestaurado']=='2.4' else 'false')" 2>/dev/null || echo false)"
check "10) precio vacío = sin precio: excluido del total (2.4×10.05 = 24.12) con aviso" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['p1'] is None and d['avisoSinPrecio'] and d['trasSinPrecio']=='24.1200' else 'false')" 2>/dev/null || echo false)"

agent-browser screenshot "$CAPT/v_validacion_01_especificacion.png" > /dev/null 2>&1

# ---------- persistencia: recargar y recuperar ----------
R=$(agent-browser eval "JSON.stringify({f:currentBudget().items[0].flags,n:currentBudget().items[0].edicionRecursos.propios.material.length})" 2>/dev/null)
agent-browser eval "sessionStorage.setItem('verrs',JSON.stringify(window.__errs||[])); location.reload(); 'r'" > /dev/null 2>&1
sleep 2.5; agent-browser wait --load networkidle > /dev/null 2>&1
agent-browser dialog accept > /dev/null 2>&1 || true
# re-armar listeners y override de confirm (la recarga los borra)
agent-browser eval "
window.__errs=JSON.parse(sessionStorage.getItem('verrs')||'[]');
window.addEventListener('error',function(e){__errs.push(String(e.message))});
window.addEventListener('unhandledrejection',function(e){__errs.push('rej:'+String(e.reason))});
window.confirm=function(){return true};
'armado'" > /dev/null 2>&1
R=$(agent-browser eval "
var bs=JSON.parse(localStorage.getItem('p3pro.budgets'));
var A=bs.filter(function(b){return b.nombre==='A-editada'})[0];
JSON.stringify({
  flags:A.items[0].flags,
  cantidad:A.items[0].cantidad,
  ed:!!A.items[0].edicionRecursos,
  n:A.items[0].edicionRecursos.propios.material.length,
  p0:[A.items[0].edicionRecursos.propios.material[0].codigo,A.items[0].edicionRecursos.propios.material[0].coef,A.items[0].edicionRecursos.propios.material[0].precio]
})" 2>/dev/null)
V=$(junesc "$R")
check "11) tras RECARGAR: presupuesto en localStorage con flags HE + 2 propios intactos" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['flags']=='HE' and d['cantidad']==2.5 and d['ed'] and d['n']==2 else 'false')" 2>/dev/null || echo false)"

R=$(agent-browser eval "
go('editor'); renderEditor();
var A=state.budgets.filter(function(b){return b.nombre==='A-editada'})[0];
state.currentId=A.id; LS.set('currentId',A.id); renderEditor();
var sel=document.getElementById('pcod2-sel'); sel.value='0'; sel.dispatchEvent(new Event('change'));
'ok'" 2>/dev/null)
sleep 2
R=$(agent-browser eval "
JSON.stringify({
  filas:document.querySelectorAll('tr.pcod2-prop').length,
  totEf:document.getElementById('pcod2-tot-efectiva').textContent,
  totObra:document.getElementById('pcod2-tot-obra').textContent,
  sombra:document.querySelector('[data-pcod2flg=\"M\"]').className.indexOf('pcod2-esp')>=0,
  mods:document.querySelectorAll('.pcod2-mods li').length
})" 2>/dev/null)
V=$(junesc "$R")
E_FINAL=$(python3 -c "print(f'{(2.4*10.05+0.375*4.5678):.4f}')")
E_FINAL_OBRA=$(python3 -c "print(f'{(2.4*10.05+0.375*4.5678)*2.5:.4f}')")
check "12) REABRIR el presupuesto → descomposición editada RECUPERADA en la UI (2 filas propias, total $E_FINAL)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['filas']==2 and d['totEf']=='$E_FINAL' and d['sombra'] and d['mods']>=2 else 'false')" 2>/dev/null || echo false)"
check "12b) total de obra recuperado exacto ($E_FINAL_OBRA)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if abs(float(d['totObra'])-float('$E_FINAL_OBRA'))<0.0001 else 'false')" 2>/dev/null || echo false)"
agent-browser screenshot "$CAPT/v_validacion_02_recuperado.png" > /dev/null 2>&1

# ---------- aislamiento: B mismo código, formato antiguo ----------
R=$(agent-browser eval "
state.currentId=state.budgets.filter(function(b){return b.nombre==='B-testigo'})[0].id; LS.set('currentId',state.currentId); renderEditor();
var sel=document.getElementById('pcod2-sel'); sel.value='0'; sel.dispatchEvent(new Event('change'));
'ok'" 2>/dev/null)
sleep 2
R=$(agent-browser eval "
var B=currentBudget(); var bit=B.items[0];
var A=state.budgets.filter(function(b){return b.nombre==='A-editada'})[0];
var r=ENGINE.calc(B); var rc=r.items[0];
JSON.stringify({
  sinFlags:bit.flags===undefined,
  sinEdicion:bit.edicionRecursos===undefined,
  sinNorma:bit.normaPreco===undefined,
  uiM:document.querySelectorAll('[data-pcod2flg]')[0].className,
  totEfB:document.getElementById('pcod2-tot-efectiva').textContent,
  A_flags:A.items[0].flags,
  A_n:A.items[0].edicionRecursos.propios.material.length,
  motorFuente:rc.precioFuente, motorPrecio:+rc.precio.toFixed(4)
})" 2>/dev/null)
V=$(junesc "$R")
check "13) presupuesto B (MISMO código, formato antiguo): sin flags/edicion/snapshot — NO hereda nada de A" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['sinFlags'] and d['sinEdicion'] and d['sinNorma'] and d['A_flags']=='HE' and d['A_n']==2 else 'false')" 2>/dev/null || echo false)"
check "13b) B se muestra con defecto MHE y el motor lo calcula (PU fuente catálogo)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if 'pcod2-on' in d['uiM'] and d['motorFuente'] and d['motorPrecio']>0 else 'false')" 2>/dev/null || echo false)"

# ---------- ciclo M/H/E completo en A: reponer palomita ----------
R=$(agent-browser eval "
state.currentId=state.budgets.filter(function(b){return b.nombre==='A-editada'})[0].id; LS.set('currentId',state.currentId); renderEditor();
var sel=document.getElementById('pcod2-sel'); sel.value='0'; sel.dispatchEvent(new Event('change'));
'ok'" 2>/dev/null)
sleep 2
R=$(agent-browser eval "
var A=currentBudget();
var antes={f:A.items[0].flags,n:A.items[0].edicionRecursos.propios.material.length};
document.querySelector('[data-pcod2flg=\"M\"]').click();
var A2=currentBudget();
JSON.stringify({antes:antes.f+'/'+antes.n, despues:A2.items[0].flags+'/'+(A2.items[0].edicionRecursos&&A2.items[0].edicionRecursos.propios&&A2.items[0].edicionRecursos.propios.material?A2.items[0].edicionRecursos.propios.material.length:0)})" 2>/dev/null)
V=$(junesc "$R")
check "14) reponer palomita M → descarta lo especificado y vuelve a la norma (HE/2 → MHE/0)" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['antes']=='HE/2' and d['despues']=='MHE/0' else 'false')" 2>/dev/null || echo false)"

# ---------- S-080 coexistente + 0 errores ----------
R=$(agent-browser eval "
var antes=JSON.stringify(currentBudget());
var ev=new KeyboardEvent('keydown',{key:'c',altKey:true,bubbles:true,cancelable:true});
document.dispatchEvent(ev);
var abierto=!!document.getElementById('pcod3-mask');
var x=document.querySelector('#pcod3-win .pcod3-x');
if(x){x.click()} else {document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))}
JSON.stringify({abierto:abierto, intacto:JSON.stringify(currentBudget())===antes, errs:window.__errs})" 2>/dev/null)
V=$(junesc "$R")
sleep 1
check "15) S-080 Calculadora abre (Alt+C) con la edición activa y NO toca el presupuesto" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['abierto'] and d['intacto'] else 'false')" 2>/dev/null || echo false)"
R=$(agent-browser eval "JSON.stringify(window.__errs)" 2>/dev/null)
V=$(junesc "$R")
check "16) 0 errores de consola durante toda la sesión" \
  "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if not d else 'false')" 2>/dev/null || echo false)"

# ---------- pasos dependientes de NORMAS ----------
if [ "$NNORMAS" -gt 0 ] 2>/dev/null; then
  echo "  (BD con $NNORMAS normas: ejecutando pasos de norma)"
  R=$(agent-browser eval "
state.currentId=state.budgets.filter(function(b){return b.nombre==='A-editada'})[0].id; LS.set('currentId',state.currentId); renderEditor();
var sel=document.getElementById('pcod2-sel'); sel.value='0'; sel.dispatchEvent(new Event('change'));
'ok'" 2>/dev/null)
  sleep 2
  R=$(agent-browser eval "
document.querySelector('[data-pcod2cargar=\"M\"]').click();
JSON.stringify({n:currentBudget().items[0].edicionRecursos.propios.material.length})" 2>/dev/null)
  V=$(junesc "$R")
  check "17) Cargar normas: copia las filas de la norma a la especificación" \
    "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d['n']>0 else 'false')" 2>/dev/null || echo false)"
  R=$(agent-browser eval "
var ed=document.querySelector('[data-pcod2ed]');
if(!ed){'sin-filas'}else{
  var spec=ed.getAttribute('data-pcod2ed');
  var orig=+ed.value;
  ed.value='0.5'; ed.dispatchEvent(new Event('change'));
  var it=currentBudget().items[0];
  var k=it.edicionRecursos.cambios;
  var guardado=k&&k[spec.split('|')[0]+'|'+spec.split('|')[1]];
  var rev=document.querySelector('[data-pcod2rev]');
  if(rev){rev.click();}
  var despues=currentBudget().items[0].edicionRecursos.cambios;
  JSON.stringify({guardado:guardado?guardado.coef:null, trasRevert:despues&&!despues[spec.split('|')[0]+'|'+spec.split('|')[1]]})
}" 2>/dev/null)
  V=$(junesc "$R")
  check "18) edición de fila de la norma (cambios) + reversión ↺" \
    "$(python3 -c "import json,sys; d=json.loads('''$V'''); print('true' if d.get('guardado')==0.5 and d.get('trasRevert') else 'false')" 2>/dev/null || echo false)"
else
  pend "17) Cargar normas (copia filas de la norma a la especificación) — requiere bases PRECODI"
  pend "18) edición de filas de la norma + reversión ↺ — requiere bases PRECODI"
  pend "18b) desactivación por palomita de filas normativas (tableta visual) — requiere bases PRECODI"
fi

agent-browser screenshot "$CAPT/v_validacion_03_final.png" > /dev/null 2>&1

# ---------- protección: BD y API intactas ----------
kill $SRV 2>/dev/null; wait $SRV 2>/dev/null; SRV=""
sleep 0.5
BD2=$(sha256sum "$REPO/bd/precodi.db" | cut -d' ' -f1)
srv; sleep 2
DEC2=$(curl -s "http://127.0.0.1:$PUERTO/api/descomposicion/012141" | sha256sum | cut -d' ' -f1)
REC2=$(curl -s "http://127.0.0.1:$PUERTO/api/recursos?q=cemento&limit=25" | sha256sum | cut -d' ' -f1)
check "19) BD byte-idéntica tras toda la edición (la norma y el catálogo no se tocan)" \
  "$([ "$BD1" = "$BD2" ] && echo true || echo false)"
check "20) API descomposición idéntica antes/después (la norma no cambia)" \
  "$([ "$DEC1" = "$DEC2" ] && echo true || echo false)"
check "21) API recursos idéntica antes/después (el nomenclador no cambia)" \
  "$([ "$REC1" = "$REC2" ] && echo true || echo false)"

# ---------- resumen ----------
echo
echo "=== RESUMEN: $ok verificados · $fallos fallos · $pendientes pendientes (datos) ==="
[ "$fallos" -eq 0 ] || { echo "HAY FALLOS REALES — no reportar como éxito"; exit 1; }
if [ "$pendientes" -gt 0 ]; then
  echo "PENDIENTES explícitos: re-importar las bases PRECODI (ver INFORME_FASE_V §limitaciones)"
  echo "y re-ejecutar este script + tests_iiib/iiic/iv."
fi
exit 0
