/* MISIÓN IV — Fase C: driver de extracción del payload SIECONS 11.
 *
 * Compilado contra los fuentes de libmspack (kyz/libmspack) sin
 * modificación: los CABs del instalador Smart Install Maker v5.04 son
 * CABs estándar a los que solo falta la firma MSCF (restaurada).
 *
 * - abre 0000.tmp…0005.tmp y fusiona la cadena con cabd->merge
 * - crea los subdirectorios de destino
 * - extrae cada archivo numerado y lo renombra a su ruta real
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <mspack.h>

/* declarado en system.h interno de libmspack */
extern struct mspack_system *mspack_default_system;

static void crear_directorios(const char *ruta) {
    char tmp[2048];
    snprintf(tmp, sizeof(tmp), "%s", ruta);
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = 0;
            mkdir(tmp, 0755);
            *p = '/';
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "uso: %s <dir_cabs> <dir_salida> <lista_rutas>\n",
                argv[0]);
        return 1;
    }
    const char *dir_cabs = argv[1], *dir_out = argv[2], *lista = argv[3];

    /* leer la lista de rutas reales (una por línea, orden = índice) */
    FILE *lf = fopen(lista, "r");
    if (!lf) { perror(lista); return 1; }
    char **rutas = calloc(256, sizeof(char *));
    int n_rutas = 0;
    char linea[1024];
    while (fgets(linea, sizeof(linea), lf)) {
        size_t n = strlen(linea);
        while (n && (linea[n-1] == '\n' || linea[n-1] == '\r')) linea[--n] = 0;
        if (n == 0) continue;
        rutas[n_rutas++] = strdup(linea);
        if (n_rutas == 256) break;
    }
    fclose(lf);
    fprintf(stderr, "rutas de mapeo: %d\n", n_rutas);

    struct mscab_decompressor *cabd =
        mspack_create_cab_decompressor(mspack_default_system);
    if (!cabd) { fprintf(stderr, "error creando descompresor\n"); return 1; }

    /* abrir los 6 CABs de la cadena (strdup: cabd_open guarda el puntero) */
    struct mscabd_cabinet *cabs[6] = {NULL};
    char camino[2048];
    for (int i = 0; i < 6; i++) {
        snprintf(camino, sizeof(camino), "%s/000%d.tmp", dir_cabs, i);
        cabs[i] = cabd->open(cabd, strdup(camino));
        if (!cabs[i]) {
            fprintf(stderr, "error abriendo %s: %d\n", camino,
                    cabd->last_error(cabd));
            return 1;
        }
        fprintf(stderr, "abierto %s (setID=%d idx=%d)\n", camino,
                cabs[i]->set_id, cabs[i]->set_index);
    }

    /* fusionar la cadena: append(cab, nextcab) */
    for (int i = 0; i < 5; i++) {
        int err = cabd->append(cabd, cabs[i], cabs[i + 1]);
        if (err) {
            fprintf(stderr, "error %d fusionando %d con %d\n", err, i, i + 1);
            return 1;
        }
        fprintf(stderr, "fusionado 000%d.tmp + 000%d.tmp\n", i, i + 1);
    }

    /* contar archivos tras la fusión */
    int total = 0, extraidos = 0;
    for (struct mscabd_file *f = cabs[0]->files; f; f = f->next) total++;
    fprintf(stderr, "archivos en la cadena fusionada: %d\n", total);

    for (struct mscabd_file *f = cabs[0]->files; f; f = f->next) {
        int idx = atoi(f->filename);
        const char *destino;
        char numerico[256];
        if (idx >= 0 && idx < n_rutas && rutas[idx]) {
            destino = rutas[idx];
        } else {
            snprintf(numerico, sizeof(numerico), "_sin_mapeo_%s", f->filename);
            destino = numerico;
        }
        snprintf(camino, sizeof(camino), "%s/%s", dir_out, destino);
        crear_directorios(camino);
        int err = cabd->extract(cabd, f, camino);
        if (err) {
            fprintf(stderr, "ERROR %d extrayendo %s -> %s\n",
                    err, f->filename, destino);
        } else {
            extraidos++;
            printf("%s\t%s\t%lld\n", f->filename, destino,
                   (long long) f->length);
        }
    }

    fprintf(stderr, "extraídos: %d de %d\n", extraidos, total);
    /* al fusionarse, todos los CAB comparten memoria: cerrar solo el
     * primero libera todo el conjunto */
    cabd->close(cabd, cabs[0]);
    mspack_destroy_cab_decompressor(cabd);
    return extraidos == total ? 0 : 2;
}
