import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import streamlit as st

from grafo import (BODEGA, DESTINOS, RUTAS_ACTUALES, a_estrella, a_networkx, aplicar_incidente,
                   dijkstra, hill_climbing, leer_matriz, posicion, rutas_actuales,
                   rutas_recomendadas, segunda_mejor_ruta, validar_ruta)
from simulacion import ESCENARIOS, experimentos, generar_pedidos, simular

st.set_page_config(page_title="Logística del Valle", layout="wide")
st.title("Logística del Valle")
st.caption("Rutas y flota para las entregas desde la bodega N01")

grafo_original = leer_matriz("matriz.csv")

# parámetros
st.sidebar.header("Parámetros")
escenario = st.sidebar.selectbox("Escenario", list(ESCENARIOS))
pedidos_hora = st.sidebar.number_input("Pedidos por hora", 1.0, 50.0, float(ESCENARIOS[escenario]),
                                       0.5, key=f"tasa_{escenario}")
vehiculos = st.sidebar.number_input("Vehículos", 1, 50, 8)
horas = st.sidebar.number_input("Horas de recepción de pedidos", 1.0, 24.0, 8.0, 0.5)
semilla = st.sidebar.number_input("Semilla", 0, 999999, 1)

st.sidebar.header("Incidente vial")
incidente = st.sidebar.checkbox("Modificar un tramo")
grafo = grafo_original
if incidente:
    origen = st.sidebar.selectbox("Desde", list(grafo_original))
    destino = st.sidebar.selectbox("Hacia", list(grafo_original[origen]))
    accion = st.sidebar.radio("Acción", ["Cambiar tiempo", "Cerrar tramo"])
    actual = grafo_original[origen][destino]
    if accion == "Cambiar tiempo":
        nuevo = st.sidebar.number_input(f"Nuevo tiempo (antes {actual:g} min)", 1.0, 500.0, actual * 2)
        grafo = aplicar_incidente(grafo_original, origen, destino, nuevo)
    else:
        grafo = aplicar_incidente(grafo_original, origen, destino, None)
    st.sidebar.caption("Las rutas recomendadas se recalculan con Dijkstra sobre la red modificada. "
                       "Las rutas actuales se mantienen y, si un tramo está cerrado, se toma el "
                       "desvío más corto en ese tramo.")

actuales = rutas_actuales(grafo)
recomendadas = rutas_recomendadas(grafo)


def texto(ruta):
    return " → ".join(ruta) if ruta else "sin ruta"


def dibujar(grafo, ruta_1=None, ruta_2=None):
    G = a_networkx(grafo)
    pos = {n: posicion(n) for n in G.nodes}
    un_sentido = [(a, b) for a, b in G.edges if not G.has_edge(b, a)]
    doble = [(a, b) for a, b in G.edges if G.has_edge(b, a)]
    fig, ax = plt.subplots(figsize=(14, 8.5))
    estilo = "arc3,rad=0.15"
    nx.draw_networkx_edges(G, pos, edgelist=doble, edge_color="#9ca3af", arrowsize=10,
                           connectionstyle=estilo, node_size=600, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=un_sentido, edge_color="#f59e0b", width=1.8,
                           arrowsize=14, connectionstyle=estilo, node_size=600, ax=ax)
    for ruta, color in ((ruta_1, "#dc2626"), (ruta_2, "#2563eb")):
        if ruta:
            nx.draw_networkx_edges(G, pos, edgelist=list(zip(ruta, ruta[1:])), edge_color=color,
                                   width=4, arrowsize=18, connectionstyle=estilo, node_size=600,
                                   alpha=0.7, ax=ax)
    etiquetas = {(a, b): f"{d['weight']:g}" for a, b, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=etiquetas, connectionstyle=estilo,
                                 font_size=7, ax=ax, bbox=dict(fc="white", ec="none", pad=0.1))
    especiales = [BODEGA] + DESTINOS
    colores = ["#111827" if n == BODEGA else "#16a34a" if n in DESTINOS else "white" for n in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_color=colores, edgecolors="black", node_size=600, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: n for n in especiales}, font_size=8,
                            font_color="white", ax=ax)
    nx.draw_networkx_labels(G, pos, labels={n: n for n in G.nodes if n not in especiales},
                            font_size=8, ax=ax)
    ax.axis("off")
    return fig


tab1, tab2, tab3, tab4 = st.tabs(["Grafo", "Rutas", "Simulación", "Experimentos"])

# grafo
with tab1:
    st.write("Cada flecha es una calle en el sentido en que se puede circular; el número es el tiempo "
             "en minutos. Las calles de doble sentido aparecen como dos flechas curvas (una por sentido) "
             "y las de un solo sentido en **naranja**. N01 es la bodega (negro) y los destinos están en verde.")
    c1, c2 = st.columns(2)
    dest = c1.selectbox("Resaltar ruta hacia", ["Ninguno"] + DESTINOS)
    sentido = c2.radio("Sentido", ["Ida", "Regreso"], horizontal=True)
    r1 = r2 = None
    if dest != "Ninguno":
        k = "ida" if sentido == "Ida" else "regreso"
        r1, r2 = actuales[dest][k], recomendadas[dest][k]
        st.write(f"Rojo: ruta actual ({actuales[dest]['t_' + k]:g} min) · "
                 f"Azul: ruta recomendada ({recomendadas[dest]['t_' + k]:g} min)")
    st.pyplot(dibujar(grafo, r1, r2))
    total_arcos = sum(len(v) for v in grafo.values())
    unicos = sum(1 for a in grafo for b in grafo[a] if a not in grafo[b])
    st.write(f"{len(grafo)} puntos, {total_arcos} conexiones dirigidas, {unicos} de un solo sentido.")

# rutas
with tab2:
    st.subheader("Validación de las rutas actuales")
    filas = []
    for d in DESTINOS:
        for sentido, ruta in (("Ida", RUTAS_ACTUALES[d]), ("Regreso", RUTAS_ACTUALES[d][::-1])):
            ok, minutos, faltan = validar_ruta(grafo, ruta)
            filas.append({"Destino": d, "Sentido": sentido, "Válida": "Sí" if ok else "No",
                          "Minutos": minutos, "Tramos inexistentes": ", ".join(faltan)})
    st.dataframe(pd.DataFrame(filas), hide_index=True)

    st.subheader("Comparación de rutas por destino")
    filas = []
    for d in DESTINOS:
        opciones = {"Actual": (actuales[d]["ida"], actuales[d]["regreso"])}
        opciones["Dijkstra"] = (dijkstra(grafo, BODEGA, d)[0], dijkstra(grafo, d, BODEGA)[0])
        opciones["A*"] = (a_estrella(grafo, BODEGA, d)[0], a_estrella(grafo, d, BODEGA)[0])
        opciones["Hill Climbing"] = (hill_climbing(grafo, BODEGA, d)[0], hill_climbing(grafo, d, BODEGA)[0])
        opciones["Segunda mejor"] = (segunda_mejor_ruta(grafo, BODEGA, d)[0],
                                     segunda_mejor_ruta(grafo, d, BODEGA)[0])
        for nombre, (ida, reg) in opciones.items():
            t_ida = validar_ruta(grafo, ida)[1] if ida else None
            t_reg = validar_ruta(grafo, reg)[1] if reg else None
            filas.append({"Destino": d, "Ruta": nombre, "Ida (min)": t_ida, "Regreso (min)": t_reg,
                          "Total (min)": t_ida + t_reg if t_ida and t_reg else None,
                          "Recorrido ida": texto(ida), "Recorrido regreso": texto(reg)})
    tabla = pd.DataFrame(filas)
    st.dataframe(tabla, hide_index=True)

    st.subheader("Comparación de algoritmos")
    st.write("Nodos expandidos = cuántos nodos tuvo que revisar el algoritmo antes de llegar.")
    filas = []
    for d in DESTINOS:
        for sentido, (o, f) in (("Ida", (BODEGA, d)), ("Regreso", (d, BODEGA))):
            for nombre, alg in (("Dijkstra", dijkstra), ("A*", a_estrella), ("Hill Climbing", hill_climbing)):
                ruta, minutos, expandidos = alg(grafo, o, f)
                filas.append({"Destino": d, "Sentido": sentido, "Algoritmo": nombre,
                              "Minutos": minutos, "Nodos expandidos": expandidos})
    st.dataframe(pd.DataFrame(filas), hide_index=True)

#  simulación
tiempos_act = {d: (actuales[d]["t_ida"], actuales[d]["t_regreso"]) for d in DESTINOS}
tiempos_rec = {d: (recomendadas[d]["t_ida"], recomendadas[d]["t_regreso"]) for d in DESTINOS}
hay_rutas = all(None not in t for t in list(tiempos_act.values()) + list(tiempos_rec.values()))

with tab3:
    if not hay_rutas:
        st.error("Con el incidente actual algún destino queda sin ruta.")
    else:
        pedidos = generar_pedidos(pedidos_hora, horas, semilla)
        viajes_act, res_act = simular(pedidos, tiempos_act, vehiculos, horas)
        viajes_rec, res_rec = simular(pedidos, tiempos_rec, vehiculos, horas)
        st.write(f"Se recibieron **{len(pedidos)} pedidos** en {horas:g} horas. "
                 "Las dos políticas atienden los mismos pedidos.")
        comparacion = pd.DataFrame({"Rutas actuales": res_act, "Rutas recomendadas": res_rec})
        st.dataframe(comparacion.round(1))

        st.write("Tiempo desde la solicitud hasta la entrega de cada pedido (la línea es el límite de 75 min)")
        grafica = pd.DataFrame({"Rutas actuales": [v["total"] for v in viajes_act],
                                "Rutas recomendadas": [v["total"] for v in viajes_rec],
                                "Límite": 75})
        st.line_chart(grafica, x_label="pedido", y_label="minutos")

        with st.expander("Ver detalle de los pedidos"):
            politica = st.radio("Política", ["Actuales", "Recomendadas"], horizontal=True)
            st.dataframe(pd.DataFrame(viajes_act if politica == "Actuales" else viajes_rec).round(1))

# experimentos
with tab4:
    if not hay_rutas:
        st.error("Con el incidente actual algún destino queda sin ruta.")
    else:
        st.write("Se corren los tres escenarios. En cada repetición se usan los mismos pedidos "
                 "para las dos políticas (repetición r usa la semilla + r).")
        repeticiones = st.slider("Repeticiones por escenario", 5, 50, 10)
        df = pd.DataFrame(experimentos(tiempos_act, tiempos_rec, vehiculos, horas, semilla, repeticiones))
        promedios = df.drop(columns="repetición").groupby(["escenario", "política"], sort=False).mean()
        st.dataframe(promedios.round(1))

        st.write("% de entregas puntuales")
        st.bar_chart(promedios["% puntuales"].unstack(), stack=False)
        st.write("Espera promedio (min)")
        st.bar_chart(promedios["espera prom"].unstack(), stack=False)

        st.subheader("¿Cuántos vehículos hacen falta?")
        maximo = st.slider("Probar hasta", 5, 30, 20)
        filas = []
        for v in range(1, maximo + 1):
            res = pd.DataFrame(experimentos(tiempos_act, tiempos_rec, v, horas, semilla, 5))
            for (esc, pol), g in res.groupby(["escenario", "política"]):
                filas.append({"vehículos": v, "serie": f"{esc} - {pol}", "% puntuales": g["% puntuales"].mean()})
        flota = pd.DataFrame(filas).pivot(index="vehículos", columns="serie", values="% puntuales")
        st.line_chart(flota, y_label="% puntuales")

        st.download_button("Descargar resultados (CSV)", df.to_csv(index=False).encode("utf-8"),
                           "resultados.csv")
