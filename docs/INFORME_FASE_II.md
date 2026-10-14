# FASE II — ENTORNO DE PRUEBAS, INSTALACIÓN DE SIECONS 11 Y DOCUMENTACIÓN OFICIAL

Fecha: 2026-10-14 · Entorno de análisis: contenedor Docker Debian 13

## 1. Capacidades REALES del entorno (verificado, sin simulaciones)

| Capacidad | Estado |
|---|---|
| Sistema | Contenedor Docker Debian 13 (trixie), kernel 5.10, usuario no root (uid 1001), 2 CPU, 4,1 GB RAM, ~8,7 GB libres |
| Virtualización | `/dev/kvm` NO existe; QEMU, VirtualBox, vmrun NO disponibles; sin `sudo` |
| Wine | NO disponible |
| **Conclusión** | **NO hay máquina virtual Windows ni posibilidad de crearla. SIECONS 11 NO se ha instalado ni ejecutado aquí** (requiere Windows + MS Access 2013+ 64 bits). No se simulará instalación alguna. |

Herramientas SÍ disponibles: `git`, `python3` (con PyPI accesible), `node`, `unrar`, `curl`, **`access-parser`** (lector de .mdb en Python puro, instalado y verificado). LibreOffice y Java presentes pero sin controlador de Access utilizable.

## 2. Requisitos verificados del instalador

Del propio ejecutable (metadatos PE + cadenas internas) y del sitio oficial:

- **SIECONS 11 «64Bit MSA_13 o Superior»** → para **MS Access 2013 o superior, de 64 bits** (los bits del Access, no los de Windows).
- Instalador Smart Install Maker v5.04; instala en `C:\SIECONS 11`; EULA propio («Acuerdo de Licencia», «Términos de la licencia antes de instalar SIECONS»).
- Requisito oficial indispensable: **Habilitar todas las macros** (Opciones de Access → Centro de Confianza → Configuración de Centro de Confianza → Configuración de Macros → Habilitar Todas las Macros).
- Variantes oficiales: MSA 2003 (32b) · MSA 2007+ (32b) · MSA 2010 (64b) · MSA 2013+ (64b).

## 3. Manuales empaquetados en el instalador — estado

- 46 rutas internas mapeadas, incl. `Como Instalar SIECONS.avi`, **`Como Quitar Vencimiento del SIECONS.doc`**, `Como Bajar Seguridad de MS-Access` (2003/2007+), `Manual Básico SIECONS.pdf`, `Configurar MS-Proyect`.
- Intento de extracción estática del payload (script `carvar_instalador.py`): 2.607 flujos zlib/LZMA candidatos analizados en el overlay de 43 MB → **solo 1 flujo válido y sin firma de archivo** → el payload usa compresión propietaria de Smart Install Maker.
- **Limitación documentada**: los manuales NO son extraíbles estáticamente con métodos estándar. Vías alternativas: instalación real en VM, o distribución oficial .7z (ver §4).

## 4. Proceso oficial de instalación y activación (fuente: siecons.nat.cu/productos, texto extraído íntegro)

> Puntos clave del texto oficial del fabricante (SoftGerency / Ing. Plinio Montano):

1. Identificar la versión de MS Access y **sus bits** (no los de Windows) para elegir el instalador correcto.
2. Habilitar todas las macros en el Centro de Confianza de Access.
3. **Clave oficial para descompactar los .7z de instalación: `pasion`** (así, sin acento).
4. La instalación y activación **solo puede hacerlas el administrador principal**, ejecutando MS Access **como administrador** (solo necesario durante la activación; después cualquier usuario puede trabajar).
5. **«La copia promocional con vida de 3 meses se activa con la palabra `pasion`»** — mecanismo oficial publicado por el fabricante (siempre que la fecha de compilación lo permita).
6. Si no funciona: contactar al fabricante indicando **versión, Número de Autenticar y Fecha de Compilación**.
7. Soporte 24/7 — Teléfonos: (+53) 7 6378259, (+53) 7 6378034, (+53) 5 2825833 · Correos: plinio@nauta.cu, siecons.plinio@nauta.cu.

**Nota**: la copia del usuario (ZIP de Drive, compilación 2025_07_22) no requiere contraseña de apertura. La distribución oficial actual son **.7z con builds `2026_05_01_0002`** (más recientes que la copia del usuario):

| Variante | Carpeta oficial Drive | Archivo detectado |
|---|---|---|
| MSA 2003, 32 bits | `drive.google.com/drive/folders/13AYz74oLGnoaLcANMa6LQu-xb64EfWaO` | `SIECONS_11_32Bit_MSA_03_2026_05_01_0002.7z` |
| MSA 2007+, 32 bits | `drive.google.com/drive/folders/1SJ5weLWJN0F0aVKfYnWzEuAj46mGKfYC` | `SIECONS_11_32Bit_MSA_07 o Superior_2026_05_01_0002.7z` |
| MSA 2010, 64 bits | `drive.google.com/drive/folders/1Ep1bdnXQsPEvNwwIAkiZKaSSF1bgZhHr` | `SIECONS_11_64Bit_MSA_10_2026_05_01_0002.7z` |
| **MSA 2013+, 64 bits (la del usuario)** | `drive.google.com/drive/folders/1kZOsDxQ5EnEh9wHosRJLDbQcR9fY-RoA` | `SIECONS_11_64Bit_MSA_13 o Superior_2026_05_01_0002.7z` |

## 5. Verificación de activos

Los tres activos (HTML, instalador, RAR) copiados a `precost/activos/` con SHA-256 verificados e idénticos a los originales analizados. Los originales de Google Drive no se han tocado (solo descargas). El RAR se extrajo a una copia de análisis (`work/recuperacion/analisis/PRECODI/`, 252 MB) sin modificar el contenedor.

## 6. Prueba de capacidad para la Fase III (bases de datos) — RESULTANTE

`access-parser` lee correctamente las .mdb del RAR PRECODI (lectura de datos REAL, no estimada):

| Base | Año | Tablas de usuario | Muestras |
|---|---|---|---|
| `7.21/codigo.mdb` (30 MB) | 2007 | 23 | Nomenclador de Materiales: 3.228 filas · Mano de Obra: 243 · Norma de Juegos: 341 |
| `codigo.mdb` raíz (42 MB) | 2017 | 24 | añade «Actividades de Estimación», «Norma Juego Material1» |
| `8.15/SBD2008_815.mdb` (106 MB) | 2011 | 284 | módulo AGIT (contratos, presupuestos, certificaciones, bancos, brigadas…) |

Esquema ejemplo (Nomenclador de Materiales v7.21): `CodMat, Material, UmRec, CodFamilia, PrecioU, PesoU, PMN, PMLC, IdEstab, Suministrador, IdM`.

**Conclusión: la Fase III (diccionario de datos y modelo de información) es totalmente viable en este entorno sin VM.**

## 7. Opciones para completar la instalación real (requiere TU máquina, no este contenedor)

**Opción A — VM en tu equipo (instalación real):**
1. VirtualBox 7.x + Windows 10/11 x64 (instantánea «antes de SIECONS»).
2. Instalar MS Office con **Access 2013 o superior de 64 bits**.
3. Habilitar todas las macros en el Centro de Confianza.
4. Ejecutar el instalador como administrador → activar la copia promocional con `pasion`.
5. Capturar: mensaje de activación, apertura de un presupuesto de prueba, y el contenido del manual «Como Quitar Vencimiento del SIECONS.doc» (ruta `C:\SIECONS 11\App\MANUAL\...`).

**Opción B — continuar aquí con análisis estático (recomendado, ya iniciado):** Fase III con `access-parser` sobre las bases PRECODI.

**Opción C — distribución oficial .7z (si autorizas la descarga):** los .7z oficiales `2026_05_01_0002` se abren con `pasion` y probablemente contienen `SBD_MICONS_2025.mdb` legible directamente sin ejecutar nada — daría acceso a la base de precios vigente 2025 para la evolución de PRECOST.

## 8. Seguridad aplicada

- Ningún ejecutable lanzado en ningún momento; solo análisis estático, lectura de archivos y descifrado de documentación pública.
- Sin elusión de licencias: la activación documentada es la **oficial del fabricante**, publicada en su propio sitio web.
- Originales intactos (Drive, upload/, contenedores RAR/ZIP).
- Registro completo: git (baseline + rama) y worklog compartido.
