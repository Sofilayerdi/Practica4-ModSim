import heapq
import random

from grafo import DESTINOS

ESCENARIOS = {"Normal": 4, "Semana Santa": 6, "Navidad": 10}


def generar_pedidos(pedidos_hora, horas, semilla):
    rng = random.Random(semilla)
    pedidos = []
    t = 0
    while True:
        t += rng.expovariate(pedidos_hora / 60)
        if t > horas * 60:
            break
        pedidos.append((t, rng.choice(DESTINOS)))
    return pedidos


def simular(pedidos, tiempos, vehiculos, horas, umbral=75):
    libres = [0.0] * vehiculos          # minuto en que cada vehículo vuelve a estar en N01
    heapq.heapify(libres)
    viajes = []
    for llegada, destino in pedidos:
        disponible = heapq.heappop(libres)
        salida = max(llegada, disponible)
        ida, regreso = tiempos[destino]
        entrega = salida + ida
        vuelta = entrega + regreso
        heapq.heappush(libres, vuelta)
        viajes.append({"llegada": llegada, "destino": destino, "salida": salida,
                       "entrega": entrega, "vuelta": vuelta,
                       "espera": salida - llegada, "total": entrega - llegada})
    return viajes, resultados(viajes, vehiculos, horas, umbral)


def resultados(viajes, vehiculos, horas, umbral):
    n = len(viajes)
    if n == 0:
        return {"pedidos": 0, "puntuales": 0, "% puntuales": 0, "espera prom": 0,
                "solicitud a entrega": 0, "utilización %": 0, "tiempo adicional": 0}
    fin = max(v["vuelta"] for v in viajes)
    jornada = max(horas * 60, fin)
    ocupado = sum(v["vuelta"] - v["salida"] for v in viajes)
    puntuales = sum(1 for v in viajes if v["total"] <= umbral)
    return {
        "pedidos": n,
        "puntuales": puntuales,
        "% puntuales": 100 * puntuales / n,
        "espera prom": sum(v["espera"] for v in viajes) / n,
        "solicitud a entrega": sum(v["total"] for v in viajes) / n,
        "utilización %": 100 * ocupado / (vehiculos * jornada),
        "tiempo adicional": max(0, fin - horas * 60),  # después del cierre, hasta que vuelve el último
    }


def experimentos(tiempos_actual, tiempos_nuevo, vehiculos, horas, semilla, repeticiones):
    filas = []
    for escenario, tasa in ESCENARIOS.items():
        for r in range(repeticiones):
            pedidos = generar_pedidos(tasa, horas, semilla + r)
            for politica, tiempos in (("Actual", tiempos_actual), ("Recomendada", tiempos_nuevo)):
                _, res = simular(pedidos, tiempos, vehiculos, horas)
                filas.append({"escenario": escenario, "repetición": r + 1,
                              "política": politica, **res})
    return filas
