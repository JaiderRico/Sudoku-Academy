# Tableros de la etapa “Resolver”

Scripts (Node) que eligieron los 12 sudokus completos por técnica que hay en `RETO_LIBRARY` de `app/index.html`.
Usan el mismo solucionador de la app (`lib.js` carga el JS del HTML).

Regla: con las técnicas anteriores el tablero se atasca y, añadiendo la técnica de la lección, se resuelve hasta el final.
Técnicas 21–23 se comparan contra las técnicas 1–18; Jellyfish contra Locked Candidates y subconjuntos.

```
node collect.js out1.json 240     # genera sudokus al azar y los clasifica (repetir out1..out4)
node collect3.js j1.json 150      # búsqueda especial para Jellyfish (j1, j2)
node build.js                     # verifica y escribe reto_lib.json
```
