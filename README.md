# Esquiva Hoyos — Maipú

Juego 2D de misiones por **calles reales de Maipú** (con su sentido real): rescata michis, reparte tortas, completos y sopaipillas, esquiva hoyos de verdad y arráncate de pacos que siempre hacen el ridículo.

**Jugar:** https://papopapote.github.io/esquiva-hoyos/ (en iPhone: Safari → Compartir → "Agregar a pantalla de inicio").

## Qué es real
- **Calles, cruces, pistas y velocidades máximas:** OpenStreetMap (© colaboradores de OpenStreetMap, licencia ODbL).
- **55 lugares de interés** (metro, malls, hospitales, Templo Votivo, etc.): OpenStreetMap.
- **Hoyos reales** con dirección: denuncias publicadas por *La Batalla de Maipú* (2025-2026).
- **Obras y desvíos:** Transporte Informa (MTT), Red Movilidad, Municipalidad de Maipú / SERVIU, y cierres vistos en el mapa en vivo de Waze (07-11-2026).
- **Calles que se anegan con lluvia:** catastro de 43 puntos de Senapred (Programa Invierno 2026) + reportes vecinales.
- **Zonas de encerronas/portonazos:** análisis de la Fiscalía Nacional y Carabineros (enlace Vespucio – Ruta 78; horario 20:00–23:00).
- **Tráfico:** simulado, más denso en hora punta y en Av. Los Pajaritos frente a la Plaza (Waze: 12 km/h).

Además de los hoyos reales hay hoyos simulados para que el juego sea entretenido; los reales se marcan como **HOYO REAL** con su fuente.

## Niveles (v2, 2026-11-08)
1. Michi sin churu — Plaza Coronel Santiago Bueras → Mercado de Maipú (1,8 km)
2. La torta de la tía — Mall Arauco Maipú → Boulevard Terrazas (2,4 km)
3. Completos calientes — Metro Santiago Bueras → Estadio Santiago Bueras (2,1 km)
4. La novia atrasada — Boulevard Terrazas → Templo Votivo (2,2 km, hora punta)
5. Sopaipillas con lluvia — Polideportivo Martín Vargas → Parque Tres Poniente (1,6 km, lluvia + Senapred)
6. El michi de noche — Metro Las Parcelas → Puesto de Mando de San Martín (3,2 km, noche)

Cada nivel tiene una barra de carga (susto del michi, torta, calorcito, paciencia del novio, crocancia). Estrellas: 1 por llegar, +1 por llegar bajo la meta de tiempo y +1 si la barra está sobre 50 %.
Pacos: controles policiales en 2 puntos de la ruta; al pasar te persiguen (nombres ACAB, 1312, PACOS QL, Cabo Donut, etc.). Caen en los hoyos, paran por sopaipillas y se pierden; si te pillan, parte de +8 s.

Personajes del estallido 2019 (fuentes en `investigacion/autoridades.md`):
- Aliados: **Negro Matapacos** (lo recoges y muerde a los pacos ~28 s), **Tía Pikachu** (pone a bailar a los pacos), **Pareman** (los hace parar), **Primera Línea** (los pacos rebotan en los escudos).
- Vehículos de Carabineros: **guanaco** (chorro que cruza la calle; niveles 4 y 6) y **zorrillo** (nubes de gas; niveles 3, 5 y 6). También mojan y gasean a los pacos.
- Patrullas en blanco y verde (colores de Carabineros desde 1996). Balizas rojo/azul [SUPUESTO].

**Alcalde Todonovic** (parodia, personaje ficticio): aparece 4 veces por nivel haciendo él mismo las pegas de la muni: tapa hoyos con pala (desaparecen), pinta la calle (pintura fresca = patinazo), corta el pasto, barre, cambia ampolletas (de noche ilumina), dirige el tránsito (detiene a los pacos), atiende en un escritorio en la vereda (anula partes) y transmite en vivo (+churus). Frases de orgullo: "¡Maipú: el mejor país de Chile!".
Aviso en portada: parodia, nombres ficticios, cualquier similitud con personas reales es no intencional.

## Controles
- **Táctil:** el auto acelera solo. Arrastra el dedo para moverte de pista. En cada cruce aparecen ⬅ ⬆ ➡ con el nombre de la calle; si no eliges, sigue el GPS (que respeta los sentidos). Botón **FRENO** (o dos dedos).
- **Teclado:** ← → pista · ↑ acelerar · ↓ / Espacio frenar · A / W / D girar en el cruce · P pausa · M sonido.

## Regenerar los datos
```
python3 -I tools/build_data.py
```
Lee `investigacion/` y escribe `data.js` (red de 12.973 tramos de OSM, 3.012 de un sentido; ~750 KB).

## Bitácora
- **2026-11-07:** v1 (corredor por rutas fijas, 5 vehículos).
- **2026-11-08:** v2: mundo abierto sobre la red real con sentidos, cámara cercana (auto 3× más grande), 6 misiones como niveles, pacos tontos, tráfico, GPS A*. Probado en Chrome con bot: los 6 niveles se completan. La v1 se respaldó solo en git (commit 08b2982).

- **2026-11-08 (tarde):** pacos más insistentes (más rápidos, menos torpezas, refuerzos tras perderlos, 2 patrullas por control desde el nivel 3), colores de Carabineros, personajes del estallido, guanaco y zorrillo. Bot: los 6 niveles se completan; arreglado un error que mostraba "FALLASTE" vacío al reiniciar.

## Próximos pasos
- Decidido: solo nombres de parodia. Ideas para seguir: General y Ministro de parodia (jefe final, órdenes por radio), ferias libres, Metro L5 como atajo, micros RED.
- Que el usuario lo pruebe en iPhone y ajustar la dificultad (barras, densidad de hoyos y velocidad).
- Ideas: más niveles, elegir vehículo, ranking de tiempos.
- 30 de los 43 puntos de Senapred siguen sin ubicar en la red.
