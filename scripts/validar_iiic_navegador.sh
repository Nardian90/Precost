#!/usr/bin/env bash
# ============================================================================
# MISIÓN III-C · FASE H — Validación reproducible del flujo completo en navegador
# ============================================================================
# Reproduce el CRITERIO FINAL DE ACEPTACIÓN de la misión:
#   abrir presupuesto → seleccionar partida real del catálogo importado →
#   consultar descomposición → comprobar consumos y subtotales → modificar
#   cantidad → guardar → recargar → comprobar persistencia → vistas intactas.
#
# Requisitos: bd/precodi.db importada (scripts/importar_precodi.py --todas),
#             agente navegador "agent-browser" instalado.
# Uso:  bash scripts/validar_iiic_navegador.sh [puerto]
# ============================================================================
set -u
PUERTO="${1:-8791}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
capturas="$REPO/docs/datos"
ok=0; fallos=0

srv() { python3 "$REPO/scripts/servidor_precodi.py" --puerto "$PUERTO" > /tmp/srv_iiic_val.log 2>&1 & SRV=$!; }
trap '[ -n "${SRV:-}" ] && kill $SRV 2>/dev/null' EXIT

check() { # check <desc> <esperado_true>
  if [ "$2" = "true" ]; then echo "  ✓ $1"; ok=$((ok+1));
  else echo "  ✗ FALLO: $1"; fallos=$((fallos+1)); fi
}

# agent-browser eval devuelve JSON.stringify(...) como string citado (doble
# codificación): desenredar antes de extraer la clave.
jget() { # jget <json_salida> <clave> → "true"/"false"
  printf '%s' "$1" | python3 -c "
import json, sys
try:
    v = json.load(sys.stdin)
    if isinstance(v, str): v = json.loads(v)
    print(str(v.get('$2')).lower())
except Exception:
    print('false')
"
}

echo "=== MISIÓN III-C — Validación en navegador (puerto $PUERTO) ==="
pkill -f "servidor_precodi.py --puerto $PUERTO" 2>/dev/null; sleep 1
srv; sleep 2

agent-browser open "http://127.0.0.1:$PUERTO/" > /dev/null
agent-browser wait --load networkidle > /dev/null

# preparación determinista: presupuesto nuevo + partida 012141 (patrón del buscador nativo)
agent-browser eval "
localStorage.removeItem('p3pro.budgets'); localStorage.removeItem('p3pro.currentId'); location.reload();
" > /dev/null; sleep 1.5
agent-browser eval "
nuevoPresupuesto();
var b = currentBudget(); b.nombre = 'Validación III-C';
b.items.push({codigo:'012141', descripcion: DB.P['012141'][0], um: DB.P['012141'][1], tipo:'partida', flags:'MHE', cantidad: 100, precio:null, coef:1, capitulo:'1221', subcapitulo:'0121'});
touch(b); go('editor'); switchEditorTab('recursos'); 'listo'
" > /dev/null; sleep 1

# 1) sección presente en la pestaña Recursos
r=$(agent-browser eval "!!document.querySelector('#pcod2-seccion')" 2>/dev/null)
check "1. Sección de descomposiciones presente en la pestaña Recursos" "$r"

# 2) seleccionar la partida → descomposición + vínculo automático
agent-browser eval "var s=document.querySelector('#pcod2-sel'); s.value='0'; s.dispatchEvent(new Event('change'))" > /dev/null; sleep 1.5
r=$(agent-browser eval "
var b=currentBudget(), t=document.querySelector('#pcod2-seccion').innerText;
JSON.stringify({d: t.includes('TOTAL descomposición'), v: !!b.items[0].normaPreco,
 c: t.includes('120.0000'), t: t.includes('888.8068'),
 k: t.includes('✓ Materiales') && t.includes('✓ Mano de obra') && t.includes('✓ Equipos')})
" 2>/dev/null)
for k in d v c t k; do
  v=$(jget "$r" "$k")
  case $k in
    d) check "2. Descomposición de 012141 visible (9 componentes)" "$v";;
    v) check "3. Norma vinculada automáticamente al presupuesto (persistencia)" "$v";;
    c) check "4. Consumo = coef × cantidad (1.2 × 100 = 120)" "$v";;
    t) check "5. Total de obra (8.8881 × 100 = 888.8068)" "$v";;
    k) check "6. Verificación contra la fuente 3/3 (CMMN/CHMN/CEMN)" "$v";;
  esac
done
agent-browser screenshot "$capturas/iiic_validacion_04_flujo_aceptacion.png" > /dev/null

# 3) modificar cantidad → recálculo
agent-browser eval "var i=document.querySelector('#pcod2-cant'); i.value='333.5'; i.dispatchEvent(new Event('change'))" > /dev/null; sleep 1.2
r=$(agent-browser eval "
var b=currentBudget(), t=document.querySelector('#pcod2-seccion').innerText;
JSON.stringify({c: b.items[0].cantidad===333.5, k: t.includes('400.2000'),
 n: b.items[0].normaPreco.componentes[0].coeficiente===1.2000000476837158})
" 2>/dev/null)
for k in c k n; do
  v=$(jget "$r" "$k")
  case $k in
    c) check "7. Cantidad presupuestada guardada (100 → 333.5)" "$v";;
    k) check "8. Consumos recalculados (1.2 × 333.5 = 400.2)" "$v";;
    n) check "9. La norma original no se modifica (Float32 exacto)" "$v";;
  esac
done

# 4) guardar → recargar → persistencia
r=$(agent-browser eval "
var g=JSON.parse(localStorage.getItem('p3pro.budgets'));
JSON.stringify({n: g.length===1, i: g[0].items.length===1, r: !!g[0].items[0].normaPreco})
" 2>/dev/null)
for k in n i r; do
  v=$(jget "$r" "$k")
  case $k in
    n) check "10. Presupuesto guardado en p3pro.budgets (mecanismo existente)" "$v";;
    i) check "11. Partida con su recurso asociado en el guardado" "$v";;
    r) check "12. Snapshot de la norma dentro del presupuesto guardado" "$v";;
  esac
done
agent-browser reload > /dev/null; agent-browser wait --load networkidle > /dev/null; sleep 1.5
agent-browser eval "go('editor'); switchEditorTab('recursos'); var s=document.querySelector('#pcod2-sel'); s.value='0'; s.dispatchEvent(new Event('change'))" > /dev/null; sleep 1.5
r=$(agent-browser eval "
var b=currentBudget(), t=document.querySelector('#pcod2-seccion').innerText;
JSON.stringify({n: b.nombre==='Validación III-C', c: b.items[0].cantidad===333.5,
 r: b.items[0].normaPreco.componentes.length===9, d: t.includes('TOTAL descomposición')})
" 2>/dev/null)
for k in n c r d; do
  v=$(jget "$r" "$k")
  case $k in
    n) check "13. Tras recargar: presupuesto recuperado" "$v";;
    c) check "14. Tras recargar: cantidad persiste (333.5)" "$v";;
    r) check "15. Tras recargar: descomposición persiste (9 componentes)" "$v";;
    d) check "16. Tras recargar: descomposición visible desde snapshot/vivo" "$v";;
  esac
done

# 5) demás vistas intactas
r=$(agent-browser eval "
var r={};
['datos','partidas','costos','resumen'].forEach(function(tb){ switchEditorTab(tb); r[tb]=document.querySelector('#tab-'+tb).innerHTML.length>50; });
go('inicio'); r.inicio=document.body.innerText.length>500; go('mios');
r.mios=document.body.innerText.includes('Validación III-C'); go('editor');
JSON.stringify(r)
" 2>/dev/null)
for k in datos partidas costos resumen inicio mios; do
  v=$(jget "$r" "$k")
  check "17. Vista/pestaña intacta: $k" "$v"
done

# 6) errores de consola
errs=$(agent-browser errors 2>/dev/null | grep -c "Error" || true)
if [ "$errs" = "0" ] || [ -z "$errs" ]; then check "18. Sin errores de consola durante todo el flujo" "true";
else check "18. Sin errores de consola ($errs encontrados)" "false"; fi

echo ""
echo "=== RESULTADO: $ok comprobaciones ✓ · $fallos fallos ==="
[ "$fallos" = "0" ] && echo "CRITERIO DE ACEPTACIÓN: SUPERADO" || echo "CRITERIO DE ACEPTACIÓN: NO SUPERADO"
agent-browser close > /dev/null 2>&1 || true
exit $fallos
