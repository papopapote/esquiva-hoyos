#!/usr/bin/env python3
"""Genera data.js para Esquiva Hoyos a partir de la investigación (OpenStreetMap + fuentes oficiales).

Uso:  python3 -I tools/build_data.py   (desde ~/esquiva-hoyos)
"""
import json, math, heapq, re, os, sys, unicodedata

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
INV = os.path.join(BASE, 'investigacion')
inCL = lambda la, lo: -33.62 < la < -33.40 and -70.92 < lo < -70.66   # Maipú, Chile (la consulta trae también Maipú, Argentina)

def load(f): return json.load(open(os.path.join(INV, f), encoding='utf-8'))
def norm(s):
    s = unicodedata.normalize('NFD', s.lower()); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\b(avenida|av\.?|calle|pasaje|camino a|camino)\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()
def dist(a, b):
    dx = (b[1] - a[1]) * math.cos(math.radians(a[0])) * 111320; dy = (b[0] - a[0]) * 110540
    return math.hypot(dx, dy)

CLS = {'motorway':1, 'motorway_link':1, 'trunk':1, 'trunk_link':1, 'primary':2, 'primary_link':2, 'secondary':3, 'secondary_link':3,
       'tertiary':4, 'tertiary_link':4, 'residential':5, 'unclassified':5, 'living_street':5}
COST = {1:1.0, 2:1.0, 3:1.12, 4:1.3, 5:2.2}
DEF_LANES = {1:3, 2:3, 3:2, 4:2, 5:2}

ways = [w for w in load('all_roads.json')['elements'] if inCL(w['geometry'][0]['lat'], w['geometry'][0]['lon'])]
adj = {}                 # nodo -> [(vecino, costo, idx_way)]
node_ways = {}           # nodo -> set(nombres)
key = lambda p: (round(p['lat'], 7), round(p['lon'], 7))
for wi, w in enumerate(ways):
    t = w['tags']; c = CLS.get(t['highway'], 5); g = [key(p) for p in w['geometry']]
    oneway = False   # el juego avanza en una sola dirección: tratamos todas las calles como doble sentido para no aislar zonas
    for a, b in zip(g, g[1:]):
        L = dist(a, b) * COST[c]
        adj.setdefault(a, []).append((b, L, wi))
        if not oneway: adj.setdefault(b, []).append((a, L, wi))
        else: adj.setdefault(b, [])
    for p in g: node_ways.setdefault(p, set()).add(wi)
nodes = list(adj)
major_nodes = [n for n in nodes if any(CLS.get(ways[w]['tags']['highway'], 5) <= 4 for w in node_ways.get(n, ()))]
print(len(ways), 'tramos,', len(nodes), 'nodos', file=sys.stderr)

def nearest(pt, maxd=400):
    pool = major_nodes
    best = min(pool, key=lambda n: (n[0] - pt[0]) ** 2 + ((n[1] - pt[1]) * 0.83) ** 2)
    if dist(best, pt) > 350: best = min(nodes, key=lambda n: (n[0] - pt[0]) ** 2 + ((n[1] - pt[1]) * 0.83) ** 2)
    d = dist(best, pt)
    if d > maxd: raise SystemExit(f'punto {pt} lejos de la red ({d:.0f} m)')
    return best

def cross_point(a, b):
    """Coordenada del cruce entre dos calles (por nombre)."""
    na, nb = norm(a), norm(b)
    A = {p for wi, w in enumerate(ways) if na in norm(w['tags']['name']) for p in (key(q) for q in w['geometry'])}
    B = {p for wi, w in enumerate(ways) if nb in norm(w['tags']['name']) for p in (key(q) for q in w['geometry'])}
    if not A or not B: return None
    c = A & B
    if c: return min(c)
    a2, b2 = min(((x, y) for x in A for y in B), key=lambda q: dist(q[0], q[1]))
    return a2 if dist(a2, b2) < 120 else None

def dijkstra(s, t):
    D = {s: 0}; prev = {}; pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t: break
        if d > D[u]: continue
        for v, L, wi in adj[u]:
            nd = d + L
            if nd < D.get(v, 1e18): D[v] = nd; prev[v] = (u, wi); heapq.heappush(pq, (nd, v))
    if t not in prev: raise SystemExit(f'sin camino {s}->{t}')
    path = [t]; wis = []
    while path[-1] != s: u, wi = prev[path[-1]]; wis.append(wi); path.append(u)
    return path[::-1], wis[::-1]

POIS = load('pois_maipu.json')
poi = lambda n: next((p['lat'], p['lon']) for p in POIS if p['nombre'] == n)
EV = load('eventos_camino.json')

# Puntos de inundación oficiales de Senapred: se ubican por cruce de calles cuando se puede
FLOOD = []
for line in open(os.path.join(INV, 'senapred_lluvia_maipu.tsv'), encoding='utf-8').read().strip().split('\n')[1:]:
    n, lugar, barrio, riesgo, tipo = line.split('\t')
    parts = [p.strip() for p in re.split(r'–|,| con | entre | / ', lugar) if p.strip()]
    pt = None
    for i in range(len(parts) - 1):
        a = re.sub(r'\(.*?\)', '', parts[i]).strip(); b = re.sub(r'\(.*?\)', '', parts[i + 1]).strip()
        if len(norm(a)) > 3 and len(norm(b)) > 3: pt = cross_point(a, b)
        if pt: break
    FLOOD.append({'n': int(n), 'lugar': lugar, 'barrio': barrio, 'riesgo': riesgo, 'tipo': tipo, 'pt': pt})
print('Senapred ubicados:', sum(1 for f in FLOOD if f['pt']), 'de', len(FLOOD), file=sys.stderr)

# ---------- Rutas (niveles) ----------
X = cross_point
ROUTES = [
  dict(name='Centro y Templo Votivo', frm='Metro Santiago Bueras', to='Templo Votivo',
       wp=[poi('Metro Santiago Bueras'), poi('Metro Plaza de Maipú'), X('El Olimpo', 'Ramón Freire'), poi('Templo Votivo de Maipú')]),
  dict(name='Obras de 5 de Abril', frm='Municipalidad', to='Parque Central Las Torres',
       wp=[poi('Municipalidad de Maipú'), X('Esquina Blanca', 'Ferrocarril'), poi('Parque Central Las Torres')]),
  dict(name='Pehuén bajo la lluvia', frm='Templo Votivo', to='Parque Tres Poniente',
       wp=[poi('Templo Votivo de Maipú'), X('El Conquistador', 'Las Tinajas'), X('Ramón Barros Luco', 'Santo Grial'), poi('Parque Tres Poniente')]),
  dict(name='Los Bosquinos', frm='Hospital El Carmen', to='Cinemark Midmall',
       wp=[poi('Hospital El Carmen'), X('4 Poniente', 'Borgoño'), X('4 Poniente', 'Antártica Chilena'), poi('Cinemark Midmall')]),
  dict(name='Vespucio de noche', frm='Mall Arauco Maipú', to='Patio Outlet', night=True,
       wp=[poi('Mall Arauco Maipú'), X('Américo Vespucio', 'Segunda Transversal'), X('Américo Vespucio', 'Ferrocarril'), poi('Patio Outlet Maipú')]),
  dict(name='Cordillera en obras', frm='Metro Del Sol', to='Plaza de Maipú',
       wp=[poi('Metro Del Sol'), X('Cordillera de Los Andes', 'La Reforma'), X('Cordillera de Los Andes', 'Teatro Municipal'), poi('Metro Plaza de Maipú')]),
]

# eventos reales asignables a rutas (con coordenada)
REAL = []
box = {'Cuatro Poniente': True}
for h in EV['hoyos']:
    if h['lat'] is not None: REAL.append(dict(type='hoyoReal', lat=h['lat'], lon=h['lon'], name='Hoyo real: ' + h['lugar'], src=h['fuente'], box='Cuatro Poniente' in h['lugar']))
for o in EV['obras_y_cierres']:
    if o['lat'] is not None:
        tp = 'cierre' if 'cerrado' in o['detalle'].lower() or 'bajo nivel' in o['detalle'] else 'obra'
        REAL.append(dict(type=tp, lat=o['lat'], lon=o['lon'], name=o['lugar'], src=o['fuente'].split(',')[0]))
for f in FLOOD:
    if f['pt'] and f['tipo'] in ('Anegamiento', 'Colapso de colectores'):
        REAL.append(dict(type='anegamiento', lat=f['pt'][0], lon=f['pt'][1], name=f['lugar'] + f' (riesgo {f["riesgo"].lower()})', src='Senapred, Programa Invierno 2026'))
# reportados por vecinos en la lluvia del 6-10-2026
for a, b in [('4 Poniente', 'Borgoño'), ('El Descanso', 'La Estrella'), ('La Galaxia', 'Libertadores de Chile')]:
    pt = X(a, b)
    if pt: REAL.append(dict(type='anegamiento', lat=pt[0], lon=pt[1], name=f'{a} con {b} (reporte vecinal 06-10-2026)', src='La Batalla de Maipú'))
# zonas rojas de encerronas (Fiscalía): enlace Vespucio con Ruta 78 y sector norte
ZONES = [dict(pt=X('Américo Vespucio', 'Ferrocarril'), r=900, name='Enlace Américo Vespucio – Ruta 78', src='Fiscalía Nacional y Carabineros'),
         dict(pt=poi('Metro Las Parcelas'), r=700, name='Sector norte de Maipú', src='Fiscalía Nacional')]
TRAFFIC_SLOW = [poi('Metro Plaza de Maipú')]     # Waze: tráfico intenso frente a la Plaza (12 km/h)

def build(R, ri):
    pts = [nearest(p) for p in R['wp']]
    path, wis = [pts[0]], []
    for a, b in zip(pts, pts[1:]):
        p, w = dijkstra(a, b); path += p[1:]; wis += w
    # distancias acumuladas
    cum = [0]
    for a, b in zip(path, path[1:]): cum.append(cum[-1] + dist(a, b))
    L = cum[-1]
    # tramos por calle
    segs = []
    for i, wi in enumerate(wis):
        t = ways[wi]['tags']; c = CLS.get(t['highway'], 5)
        lanes_tag = int(t['lanes']) if str(t.get('lanes', '')).isdigit() else 0
        per_dir = lanes_tag if t.get('oneway') == 'yes' else lanes_tag // 2
        lanes = max(2, min(4, per_dir or DEF_LANES[c]))
        vmax = int(t['maxspeed']) if str(t.get('maxspeed', '')).isdigit() else (100 if c == 1 else 50)
        name = t['name']
        if segs and segs[-1]['name'] == name: segs[-1]['d1'] = cum[i + 1]; continue
        if segs and cum[i + 1] - cum[i] < 25 and segs[-1]['d1'] - segs[-1]['d0'] < 25: pass
        segs.append(dict(name=name, d0=cum[i], d1=cum[i + 1], lanes=lanes, vmax=min(vmax, 100), cls=c, i0=i))
    # fusionar tramos muy cortos (< 60 m) con el anterior
    merged = []
    for s in segs:
        if merged and (s['d1'] - s['d0'] < 60 or s['name'] == merged[-1]['name']): merged[-1]['d1'] = s['d1']; continue
        merged.append(s)
    segs = merged
    # giros
    def heading(i):
        a, b = path[max(0, i - 3)], path[min(len(path) - 1, i + 3)]
        return math.atan2(b[0] - a[0], (b[1] - a[1]) * 0.83)
    for k, s in enumerate(segs[1:], 1):
        i = s['i0']; h1 = heading(max(0, i - 4)); h2 = heading(min(len(path) - 1, i + 4))
        dh = math.atan2(math.sin(h2 - h1), math.cos(h2 - h1))
        s['turn'] = 'Gira a la izquierda' if dh > 0.5 else 'Gira a la derecha' if dh < -0.5 else ''
    for s in segs: s.pop('i0', None); s['d0'] = round(s['d0']); s['d1'] = round(s['d1'])
    # cruces
    cross = []; lastd = {}
    for i, n in enumerate(path):
        here = {ways[w]['tags']['name'] for w in node_ways.get(n, ())}
        cur = ways[wis[min(i, len(wis) - 1)]]['tags']['name']; prv = ways[wis[max(0, i - 1)]]['tags']['name']
        for nm in sorted(here - {cur, prv}):
            cl = min(CLS.get(ways[w]['tags']['highway'], 5) for w in node_ways[n] if ways[w]['tags']['name'] == nm)
            if cum[i] - lastd.get(nm, -1e9) < 150: continue
            if cross and cum[i] - cross[-1]['d'] < (60 if cl <= 3 else 140): continue
            cross.append(dict(d=round(cum[i]), name=nm, major=cl <= 3)); lastd[nm] = cum[i]
    # proyectar puntos sobre la ruta
    def project(lat, lon, maxd):
        best = None
        for i in range(0, len(path)):
            d = dist(path[i], (lat, lon))
            if best is None or d < best[0]: best = (d, i)
        if best[0] > maxd: return None
        i = best[1]
        a, b = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        side = (b[1] - a[1]) * (lat - a[0]) - (b[0] - a[0]) * (lon - a[1])
        return cum[i], ('izq' if side > 0 else 'der'), best[0]
    events = []
    for e in REAL:
        pr = project(e['lat'], e['lon'], 70 if e['type'] != 'anegamiento' else 90)
        if pr and 150 < pr[0] < L - 80:
            ev = dict(e); ev['d'] = round(pr[0]); ev['side'] = pr[1]; ev['real'] = True
            if ev['type'] == 'hoyoReal': ev['size'] = 1.3; ev['lane'] = 0 if pr[1] == 'izq' else 1
            if ev['type'] == 'obra': ev['lanesN'] = 1
            events.append(ev)
    # fusionar eventos del mismo tipo muy cercanos (p. ej. dos avisos del mismo cierre)
    events.sort(key=lambda e: e['d']); ded = []
    for e in events:
        if ded and ded[-1]['type'] == e['type'] and e['d'] - ded[-1]['d'] < 150: ded[-1]['name'] += ' / ' + e['name']; continue
        ded.append(e)
    events = ded
    for z in ZONES:
        if not z['pt']: continue
        inside = [cum[i] for i, n in enumerate(path) if dist(n, z['pt']) < z['r']]
        if inside and R.get('night'):
            events.append(dict(type='zona', d=round(max(200, min(inside))), d2=round(min(L - 100, max(inside))), name=z['name'], src=z['src'], lat=z['pt'][0], lon=z['pt'][1]))
    # lugares de interés junto a la ruta
    pois = []
    for p in POIS:
        pr = project(p['lat'], p['lon'], 260)
        if pr and 60 < pr[0] < L - 30 and not any(abs(q['d'] - pr[0]) < 90 for q in pois):
            pois.append(dict(d=round(pr[0]), name=p['nombre'], cat=p['categoria'], side=pr[1]))
    pois.sort(key=lambda q: q['d'])
    # tráfico lento real (Waze)
    for s in segs:
        s['slow'] = any(dist(path[i], tp) < 300 for tp in TRAFFIC_SLOW for i, c in enumerate(cum) if s['d0'] <= c <= s['d1'])
    # forma para el minimapa
    lat0 = sum(p[0] for p in path) / len(path)
    xs = [p[1] * math.cos(math.radians(lat0)) for p in path]; ys = [-p[0] for p in path]
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys); sc = max(mxx - mnx, mxy - mny) or 1
    ox = (1 - (mxx - mnx) / sc) / 2; oy = (1 - (mxy - mny) / sc) / 2
    shape, shapeCum, geo, lastc = [], [], [], -1e9
    for i, p in enumerate(path):
        if cum[i] - lastc >= 40 or i == len(path) - 1:
            shape.append([round(ox + (xs[i] - mnx) / sc, 4), round(oy + (ys[i] - mny) / sc, 4)]); shapeCum.append(round(cum[i] / L, 4))
            geo.append([round(p[0], 5), round(p[1], 5)]); lastc = cum[i]
    return dict(id=ri, name=R['name'], **{'from': R['frm']}, to=R['to'], night=bool(R.get('night')), len=round(L), segs=segs, cross=cross,
                pois=pois, events=sorted(events, key=lambda e: e['d']), shape=shape, shapeCum=shapeCum, geo=geo)

routes = []
for ri, R in enumerate(ROUTES):
    if any(w is None for w in R['wp']): raise SystemExit(f'ruta {R["name"]}: waypoint sin ubicar {R["wp"]}')
    r = build(R, ri); routes.append(r)
    kinds = {}
    for e in r['events']: kinds[e['type']] = kinds.get(e['type'], 0) + 1
    print(f"{r['name']:24s} {r['len']/1000:4.1f} km  {len(r['segs'])} calles  {len(r['cross'])} cruces  {len(r['pois'])} lugares  eventos {kinds}", file=sys.stderr)
    print('   calles:', ' → '.join(s['name'] for s in r['segs']), file=sys.stderr)

# calles principales para el mapa
base = []
for w in load('roads.json')['elements']:
    g = w['geometry']
    if not inCL(g[0]['lat'], g[0]['lon']): continue
    c = CLS.get(w['tags']['highway'], 5)
    if c > 3: continue
    pts, last = [], None
    for q in g:
        p = (round(q['lat'], 4), round(q['lon'], 4))
        if p != last: pts.append(list(p)); last = p
    if len(pts) > 1: base.append(dict(c=c, p=pts))
lats = [p[0] for r in base for p in r['p']]; lons = [p[1] for r in base for p in r['p']]
geo_all = [p for r in routes for p in r['geo']]
bbox = dict(n=max(p[0] for p in geo_all) + 0.012, s=min(p[0] for p in geo_all) - 0.012, w=min(p[1] for p in geo_all) - 0.015, e=max(p[1] for p in geo_all) + 0.015)
base = [r for r in base if any(bbox['s'] < p[0] < bbox['n'] and bbox['w'] < p[1] < bbox['e'] for p in r['p'])]
data = dict(generated='2026-11-07', bbox=bbox, base=base, routes=routes,
            pois=[dict(name=p['nombre'], cat=p['categoria'], lat=p['lat'], lon=p['lon']) for p in POIS],
            flood=[dict(n=f['n'], lugar=f['lugar'], riesgo=f['riesgo'], lat=f['pt'][0] if f['pt'] else None, lon=f['pt'][1] if f['pt'] else None) for f in FLOOD])
out = os.path.join(BASE, 'data.js')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write('// Generado por tools/build_data.py — calles © OpenStreetMap contributors (ODbL); eventos: Senapred, Fiscalía, MTT, Red Movilidad, La Batalla de Maipú, Waze\n')
    fh.write('window.MAIPU = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('data.js', os.path.getsize(out) // 1024, 'KB', file=sys.stderr)
