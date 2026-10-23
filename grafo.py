import csv
import heapq
from collections import deque

import networkx as nx

BODEGA = "N01"
DESTINOS = ["N08", "N19", "N34", "N40"]

# Rutas de ida de las hojas de despacho. El regreso es la misma ruta al revés.
RUTAS_ACTUALES = {
    "N08": ["N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08"],
    "N19": ["N01", "N02", "N03", "N11", "N19"],
    "N34": ["N01", "N09", "N17", "N25", "N33", "N34"],
    "N40": ["N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08", "N16", "N24", "N32", "N40"],
}


def leer_matriz(archivo):
    grafo = {}
    with open(archivo, encoding="utf-8-sig") as f:
        lector = csv.reader(f)
        columnas = next(lector)[1:]
        for fila in lector:
            origen = fila[0]
            grafo[origen] = {}
            for destino, valor in zip(columnas, fila[1:]):
                valor = valor.strip()
                if valor in ("", "—", "-") or destino == origen:
                    continue
                grafo[origen][destino] = float(valor)
    return grafo


def validar_ruta(grafo, ruta):
    total = 0
    faltan = []
    for a, b in zip(ruta, ruta[1:]):
        if b in grafo[a]:
            total += grafo[a][b]
        else:
            faltan.append(f"{a}->{b}")
    if faltan:
        return False, None, faltan
    return True, total, []


def armar_ruta(anterior, fin):
    ruta = [fin]
    while anterior[ruta[-1]] is not None:
        ruta.append(anterior[ruta[-1]])
    return ruta[::-1]


# Dijkstra
def dijkstra(grafo, inicio, fin):
    dist = {inicio: 0}
    anterior = {inicio: None}
    cola = [(0, inicio)]
    visitados = set()
    while cola:
        d, nodo = heapq.heappop(cola)
        if nodo in visitados:
            continue
        visitados.add(nodo)
        if nodo == fin:
            return armar_ruta(anterior, fin), d, len(visitados)
        for vecino, peso in grafo[nodo].items():
            if d + peso < dist.get(vecino, float("inf")):
                dist[vecino] = d + peso
                anterior[vecino] = nodo
                heapq.heappush(cola, (d + peso, vecino))
    return None, None, len(visitados)


# A*
def heuristica(grafo, fin):
    entrantes = {n: [] for n in grafo}
    for a in grafo:
        for b in grafo[a]:
            entrantes[b].append(a)
    minimo = min(p for a in grafo for p in grafo[a].values())

    saltos = {fin: 0}
    cola = deque([fin])
    while cola:
        n = cola.popleft()
        for a in entrantes[n]:
            if a not in saltos:
                saltos[a] = saltos[n] + 1
                cola.append(a)
    return {n: saltos[n] * minimo for n in saltos}


def a_estrella(grafo, inicio, fin):
    h = heuristica(grafo, fin)
    if inicio not in h:
        return None, None, 0
    g = {inicio: 0}
    anterior = {inicio: None}
    cola = [(h[inicio], inicio)]
    visitados = set()
    while cola:
        _, nodo = heapq.heappop(cola)
        if nodo in visitados:
            continue
        visitados.add(nodo)
        if nodo == fin:
            return armar_ruta(anterior, fin), g[fin], len(visitados)
        for vecino, peso in grafo[nodo].items():
            if vecino in h and g[nodo] + peso < g.get(vecino, float("inf")):
                g[vecino] = g[nodo] + peso
                anterior[vecino] = nodo
                heapq.heappush(cola, (g[vecino] + h[vecino], vecino))
    return None, None, len(visitados)


# Hill Climbing
def hill_climbing(grafo, inicio, fin):
    h = heuristica(grafo, fin)
    if inicio not in h:
        return None, None, 0
    ruta = [inicio]
    total = 0
    pasos = 0
    while ruta[-1] != fin:
        actual = ruta[-1]
        pasos += 1
        opciones = [(h[v], p, v) for v, p in grafo[actual].items()
                    if v in h and h[v] < h[actual] and v not in ruta]
        if not opciones:
            return None, None, pasos  # óptimo local, no llegó
        _, peso, siguiente = min(opciones)
        ruta.append(siguiente)
        total += peso
    return ruta, total, pasos


# otras rutas alternativas
def segunda_mejor_ruta(grafo, inicio, fin):
    G = a_networkx(grafo)
    try:
        rutas = nx.shortest_simple_paths(G, inicio, fin, weight="weight")
        next(rutas)
        ruta = next(rutas)
    except (nx.NetworkXNoPath, StopIteration):
        return None, None
    return ruta, validar_ruta(grafo, ruta)[1]


def a_networkx(grafo):
    G = nx.DiGraph()
    for a in grafo:
        for b, p in grafo[a].items():
            G.add_edge(a, b, weight=p)
    return G


#  incidentes
def aplicar_incidente(grafo, origen, destino, nuevo_tiempo=None):
    nuevo = {a: dict(vecinos) for a, vecinos in grafo.items()}
    if nuevo_tiempo is None:
        nuevo[origen].pop(destino, None)
    else:
        nuevo[origen][destino] = nuevo_tiempo
    return nuevo


def con_desvio(grafo, ruta):
    nueva = [ruta[0]]
    for a, b in zip(ruta, ruta[1:]):
        if b in grafo[a]:
            nueva.append(b)
        else:
            desvio, _, _ = dijkstra(grafo, a, b)
            if desvio is None:
                return None
            nueva += desvio[1:]
    return nueva


# políticas
def rutas_actuales(grafo):
    res = {}
    for d in DESTINOS:
        ida = con_desvio(grafo, RUTAS_ACTUALES[d])
        regreso = con_desvio(grafo, RUTAS_ACTUALES[d][::-1])
        res[d] = {"ida": ida, "regreso": regreso,
                  "t_ida": validar_ruta(grafo, ida)[1] if ida else None,
                  "t_regreso": validar_ruta(grafo, regreso)[1] if regreso else None}
    return res


def rutas_recomendadas(grafo):
    res = {}
    for d in DESTINOS:
        ida, t_ida, _ = dijkstra(grafo, BODEGA, d)
        regreso, t_reg, _ = dijkstra(grafo, d, BODEGA)
        res[d] = {"ida": ida, "regreso": regreso, "t_ida": t_ida, "t_regreso": t_reg}
    return res


#  dibujo
def posicion(nodo):
    k = int(nodo[1:]) - 1
    return (k % 8, -(k // 8))
