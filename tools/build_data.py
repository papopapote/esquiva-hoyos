#!/usr/bin/env python3
"""Genera data.js para Esquiva Hoyos v2 (mundo abierto sobre calles reales de Maipú).

Uso:  python3 -I tools/build_data.py   (desde ~/esquiva-hoyos)

Salida: red de calles de OpenStreetMap con SENTIDO REAL (oneway), pistas y velocidades,
eventos reales (hoyos, obras, anegamientos Senapred) proyectados sobre las calles,
y los niveles (misiones A -> B) con controles policiales sobre la ruta más corta.
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

CLS = {'motorway':1, 'motorway_link':1, 'trunk':1, 'trunk_link':1, 'primary':2, 'primary_link':2, 'secondary':3, 'secondary_link':3,
       'tertiary':4, 'tertiary_link':4, 'residential':5, 'unclassified':5, 'living_street':6}
DEF_LANES = {1:3, 2:2, 3:2, 4:1, 5:1, 6:1}      # pistas por sentido si OSM no lo dice
PEN = {1:1, 2:1, 3:1.05, 4:1.1, 5:1.3, 6:1.6}   # costo GPS: preferir avenidas (igual que en el juego)
DEF_V = {1:100, 2:60, 3:50, 4:50, 5:40, 6:30}

POIS = load('pois_maipu.json')
poi = lambda n: next((p['lat'], p['lon']) for p in POIS if p['nombre'] == n)

# ---------- Niveles (misiones) ----------
LEVELS = [
  dict(id='michi',  name='Michi sin churu',       frm='Plaza Coronel Santiago Bueras', to='Mercado de Maipú',  cargo='gato'),
  dict(id='torta',  name='La torta de la tía',    frm='Mall Arauco Maipú',        to='Boulevard Terrazas Maipú', cargo='torta'),
  dict(id='compl',  name='Completos calientes',   frm='Metro Santiago Bueras',    to='Estadio Santiago Bueras', cargo='completos'),
  dict(id='novia',  name='La novia atrasada',     frm='Boulevard Terrazas Maipú', to='Templo Votivo de Maipú', cargo='novia', rush=True),
  dict(id='sopa',   name='Sopaipillas con lluvia',frm='Polideportivo Martín Vargas', to='Parque Tres Poniente', cargo='sopaipillas', rain=True),
  dict(id='feria',  name='Huevos de la feria',    frm='El Descanso Boulevard',    to='Mall Arauco Maipú', cargo='huevos', feria=True),
  dict(id='abrazo', name='El Abrazo de Maipú',    frm='Plaza Coronel Santiago Bueras', to='Monumento al Abrazo de Maipú', cargo='procer'),
  dict(id='noche',  name='El michi de noche',     frm='Metro Las Parcelas',       to='Puesto de Mando de San Martín', cargo='gato', night=True),
]
pts = [poi(L['frm']) for L in LEVELS] + [poi(L['to']) for L in LEVELS]
MARGIN = 0.008
BB = dict(s=min(p[0] for p in pts) - MARGIN, n=max(p[0] for p in pts) + MARGIN,
          w=min(p[1] for p in pts) - MARGIN * 1.2, e=max(p[1] for p in pts) + MARGIN * 1.2)
LAT0, LON0 = (BB['s'] + BB['n']) / 2, (BB['w'] + BB['e']) / 2
KX = math.cos(math.radians(LAT0)) * 111320; KY = 110540
def xy(lat, lon): return ((lon - LON0) * KX, -(lat - LAT0) * KY)     # metros; y hacia el sur (como la pantalla)
inBB = lambda la, lo: BB['s'] < la < BB['n'] and BB['w'] < lo < BB['e']

# ---------- Grafo ----------
ways = [w for w in load('all_roads.json')['elements'] if w['type'] == 'way' and w['tags'].get('highway') in CLS
        and inCL(w['geometry'][0]['lat'], w['geometry'][0]['lon']) and any(inBB(p['lat'], p['lon']) for p in w['geometry'])]
key = lambda p: (round(p['lat'], 7), round(p['lon'], 7))
use = {}
for w in ways:
    g = [key(p) for p in w['geometry']]
    for i, p in enumerate(g): use[p] = use.get(p, 0) + (2 if 0 < i < len(g) - 1 else 1)
names = []; name_idx = {}
def nid(s):
    if s not in name_idx: name_idx[s] = len(names); names.append(s)
    return name_idx[s]
node_id = {}; NODES = []
def node(p):
    if p not in node_id: node_id[p] = len(NODES); NODES.append(xy(*p))
    return node_id[p]
EDGES = []    # dict(a, b, pts, name, cls, lf, lb, v, ow)
for w in ways:
    t = w['tags']; c = CLS[t['highway']]; g = [key(p) for p in w['geometry']]
    ow = t.get('oneway') in ('yes', '1', 'true') or t.get('junction') == 'roundabout' or c == 1 and t.get('oneway') != 'no'
    rev = t.get('oneway') == '-1'
    if rev: g = g[::-1]; ow = True
    tl = int(t['lanes']) if str(t.get('lanes', '')).isdigit() else 0
    if ow: lf, lb = max(1, min(4, tl or DEF_LANES[c] + (1 if c <= 3 else 0))), 0
    else:
        lf = lb = max(1, min(3, (tl // 2) if tl >= 2 else DEF_LANES[c]))
    v = int(t['maxspeed']) if str(t.get('maxspeed', '')).isdigit() else DEF_V[c]
    name = t.get('name') or ('Pasaje sin nombre' if c >= 5 else 'Calle sin nombre')
    cur = [g[0]]
    for p in g[1:]:
        cur.append(p)
        if use.get(p, 0) >= 3 or p == g[-1] or (p in node_id and p != g[-1]):
            if len(cur) >= 2 and cur[0] != cur[-1]:
                EDGES.append(dict(a=node(cur[0]), b=node(cur[-1]), pts=[xy(*q) for q in cur], name=nid(name), cls=c, lf=lf, lb=lb, v=v, ow=ow))
            cur = [p]
# largo de cada arco
for e in EDGES:
    e['len'] = sum(math.dist(p, q) for p, q in zip(e['pts'], e['pts'][1:]))
EDGES = [e for e in EDGES if e['len'] > 0.5]
# componente conexa mayor (ignorando sentidos)
adjU = {}
for i, e in enumerate(EDGES): adjU.setdefault(e['a'], []).append(e['b']); adjU.setdefault(e['b'], []).append(e['a'])
seen = set(); best = set()
for s in adjU:
    if s in seen: continue
    comp = {s}; st = [s]
    while st:
        u = st.pop()
        for v in adjU[u]:
            if v not in comp: comp.add(v); st.append(v)
    seen |= comp
    if len(comp) > len(best): best = comp
EDGES = [e for e in EDGES if e['a'] in best]
# renumerar nodos
used = sorted({e['a'] for e in EDGES} | {e['b'] for e in EDGES}); ren = {o: i for i, o in enumerate(used)}
NODES = [NODES[o] for o in used]
for e in EDGES: e['a'] = ren[e['a']]; e['b'] = ren[e['b']]
print(len(ways), 'calles OSM →', len(EDGES), 'tramos,', len(NODES), 'nodos,', sum(e['ow'] for e in EDGES), 'de un sentido', file=sys.stderr)

# adyacencia dirigida (respeta sentido)
adj = [[] for _ in NODES]
for i, e in enumerate(EDGES):
    cost = e['len'] * PEN[e['cls']]
    adj[e['a']].append((e['b'], cost, i))
    if not e['ow']: adj[e['b']].append((e['a'], cost, i))
def dijkstra(s, t):
    D = {s: 0}; prev = {}; pq = [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t: break
        if d > D[u]: continue
        for v, L, ei in adj[u]:
            nd = d + L
            if nd < D.get(v, 1e18): D[v] = nd; prev[v] = (u, ei); heapq.heappush(pq, (nd, v))
    if t not in prev: return None
    path = [t]; eis = []
    while path[-1] != s: u, ei = prev[path[-1]]; eis.append(ei); path.append(u)
    return path[::-1], eis[::-1]

def snap(x, y, maxd=60, cls_max=6):
    """Punto más cercano sobre un arco: (edge, s, lateral con signo, distancia)."""
    best = None
    for i, e in enumerate(EDGES):
        if e['cls'] > cls_max: continue
        acc = 0
        for p, q in zip(e['pts'], e['pts'][1:]):
            dx, dy = q[0] - p[0], q[1] - p[1]; L2 = dx * dx + dy * dy or 1e-9
            u = max(0, min(1, ((x - p[0]) * dx + (y - p[1]) * dy) / L2))
            px, py = p[0] + u * dx, p[1] + u * dy; d = math.hypot(x - px, y - py)
            if best is None or d < best[3]:
                side = (dx * (y - p[1]) - dy * (x - p[0])) / math.sqrt(L2)   # >0: a la derecha del sentido del arco (y hacia abajo)
                best = (i, acc + u * math.sqrt(L2), side, d)
            acc += math.sqrt(L2)
    return best if best and best[3] <= maxd else None

def near_node(x, y, cls_max=5):
    cand = [(math.hypot(NODES[n][0] - x, NODES[n][1] - y), n) for n in range(len(NODES)) if len(adj[n]) > 0
            and any(EDGES[ei]['cls'] <= cls_max for _, _, ei in adj[n])]
    return min(cand)[1]

# ---------- Eventos reales ----------
EV = load('eventos_camino.json')
REAL = []
def add_real(tp, lat, lon, name, src, maxd=45):
    if not inBB(lat, lon): return
    sn = snap(*xy(lat, lon), maxd=maxd)
    if sn: REAL.append(dict(t=tp, e=sn[0], s=round(sn[1], 1), side=1 if sn[2] > 0 else -1, n=name, src=src))
for h in EV['hoyos']:
    if h['lat'] is not None: add_real('hoyo', h['lat'], h['lon'], h['lugar'], h['fuente'])
for o in EV['obras_y_cierres']:
    if o['lat'] is not None: add_real('obra', o['lat'], o['lon'], o['lugar'], o['fuente'].split(',')[0])
# Senapred: ubicar por cruce de calles (nombres)
def cross_point(a, b):
    na, nb = norm(a), norm(b)
    A = {(e['a'], e['b']) for e in EDGES if na and na in norm(names[e['name']])}
    B = {(e['a'], e['b']) for e in EDGES if nb and nb in norm(names[e['name']])}
    An = {n for ab in A for n in ab}; Bn = {n for ab in B for n in ab}
    c = An & Bn
    return NODES[min(c)] if c else None
nflood = 0
for line in open(os.path.join(INV, 'senapred_lluvia_maipu.tsv'), encoding='utf-8').read().strip().split('\n')[1:]:
    n, lugar, barrio, riesgo, tipo = line.split('\t')
    if tipo not in ('Anegamiento', 'Colapso de colectores'): continue
    parts = [p.strip() for p in re.split(r'–|,| con | entre | / ', lugar) if p.strip()]
    pt = None
    for i in range(len(parts) - 1):
        a = re.sub(r'\(.*?\)', '', parts[i]).strip(); b = re.sub(r'\(.*?\)', '', parts[i + 1]).strip()
        if len(norm(a)) > 3 and len(norm(b)) > 3: pt = cross_point(a, b)
        if pt: break
    if pt:
        sn = snap(pt[0] + 6, pt[1] + 6, maxd=30)
        if sn: REAL.append(dict(t='agua', e=sn[0], s=round(sn[1], 1), side=0, n=lugar + f' (riesgo {riesgo.lower()})', src='Senapred, Programa Invierno 2026')); nflood += 1
print('eventos reales en el mapa:', len(REAL), '(anegamientos Senapred:', nflood, ')', file=sys.stderr)

# ---------- Niveles ----------
levels = []
for L in LEVELS:
    A = xy(*poi(L['frm'])); B = xy(*poi(L['to']))
    na, nb = near_node(*A), near_node(*B)
    r = dijkstra(na, nb)
    if not r: raise SystemExit('sin ruta ' + L['name'])
    path, eis = r
    cum = [0]
    for ei in eis: cum.append(cum[-1] + EDGES[ei]['len'])
    total = cum[-1]
    # controles policiales: nodos de la ruta a ~35 % y ~70 % (en calles grandes si se puede)
    ctrl = []
    for f in (0.35, 0.7):
        i = min(range(1, len(path) - 1), key=lambda k: abs(cum[k] - total * f) + (0 if EDGES[eis[k]]['cls'] <= 4 else 150))
        ctrl.append(path[i])
    # arco de partida: el primero de la ruta
    L2 = dict(id=L['id'], name=L['name'], frm=L['frm'], to=L['to'], cargo=L['cargo'], night=bool(L.get('night')), rain=bool(L.get('rain')),
              rush=bool(L.get('rush')), feria=bool(L.get('feria')), start=dict(e=eis[0], dir=1 if EDGES[eis[0]]['a'] == path[0] else -1),
              A=[round(A[0]), round(A[1])], B=[round(B[0]), round(B[1])], goal=nb, ctrl=ctrl, best=round(total))
    levels.append(L2)
    print(f"{L['name']:24s} {total/1000:4.1f} km  calles: " + ' → '.join(dict.fromkeys(names[EDGES[ei]['name']] for ei in eis)), file=sys.stderr)

# ---------- Exportar compacto ----------
N = [v for p in NODES for v in (round(p[0], 1), round(p[1], 1))]
E = []; P = []
for e in EDGES:
    # puntos intermedios (sin extremos) simplificados: se descartan puntos casi colineales a < 1 m
    mid = [q for q in e['pts'][1:-1]]
    E.append([e['a'], e['b'], e['name'], e['cls'], e['lf'], e['lb'], e['v'], 1 if e['ow'] else 0])
    P.append([v for q in mid for v in (round(q[0], 1), round(q[1], 1))])
pois = [dict(n=p['nombre'], c=p['categoria'], x=round(xy(p['lat'], p['lon'])[0]), y=round(xy(p['lat'], p['lon'])[1])) for p in POIS if inBB(p['lat'], p['lon'])]
data = dict(generated='2026-11-08', origin=[LAT0, LON0], names=names, N=N, E=E, P=P, real=REAL, pois=pois, levels=levels)
out = os.path.join(BASE, 'data.js')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write('// Generado por tools/build_data.py — calles © OpenStreetMap contributors (ODbL); eventos: Senapred, MTT, Red Movilidad, La Batalla de Maipú, Waze\n')
    fh.write('window.MAIPU=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('data.js', os.path.getsize(out) // 1024, 'KB', file=sys.stderr)
