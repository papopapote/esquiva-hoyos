# Esquiva Hoyos — Maipú

Juego 2D animado: maneja por **calles reales de Maipú** esquivando hoyos, obras, desvíos, calles anegadas y zonas de encerronas.

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

## Controles
- **Táctil:** mantén el dedo en la pantalla para avanzar y muévelo para cambiar de pista. Botón **FRENO** abajo a la derecha (o dos dedos).
- **Teclado:** ← → pista · ↑ acelerar (+15 km/h) · ↓ / Espacio frenar · P pausa · M sonido.

## Regenerar los datos
```
python3 -I tools/build_data.py
```
Lee `investigacion/` (descargas de OpenStreetMap y eventos con fuentes) y escribe `data.js`.
