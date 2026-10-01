#!/usr/bin/env python3
"""Predice, ANTES de medir, las esperas de FIFO y de prioridad con envejecimiento.

Modelo (discreto, sin ROS): N clientes en lazo cerrado, como el cliente del kit:
cada uno manda un goal, espera su resultado, descansa `pausa` segundos y manda el
siguiente. El brazo atiende de a uno y cada movimiento dura `servicio` segundos.

    python3 simular_prediccion.py
    python3 simular_prediccion.py --n 40 --servicio 3.05 --pausa 0.5 --tau 8 \
        --prioridades 1 2 3 4

Es la predicción que el reto pide dejar firmada en el documento de diseño previo.
Después se contrasta con lo medido (analisis/metricas.py).
"""
import argparse, random, statistics


def p95(xs):
    xs = sorted(xs)
    return xs[max(0, min(len(xs) - 1, int(round(0.95 * (len(xs) - 1)))))] if xs else 0.0


def jain(v):
    return (sum(v) ** 2) / (len(v) * sum(x * x for x in v)) if v and sum(v) else 0.0


def simular(politica, prioridades, n, servicio, pausa, tau, semilla, jitter):
    rnd = random.Random(semilla)
    clientes = len(prioridades)
    llegada = [rnd.uniform(0, 0.5) for _ in range(clientes)]      # próximo envío
    restantes = [n] * clientes
    t, esperas, atendidos = 0.0, [[] for _ in range(clientes)], [0] * clientes
    while any(r > 0 for r in restantes):
        listos = [i for i in range(clientes) if restantes[i] > 0 and llegada[i] <= t]
        if not listos:
            t = min(llegada[i] for i in range(clientes) if restantes[i] > 0)
            continue
        if politica == 'fifo':
            i = min(listos, key=lambda k: llegada[k])
        else:
            i = max(listos, key=lambda k: (prioridades[k] + (t - llegada[k]) / tau, -llegada[k]))
        esperas[i].append(t - llegada[i])
        t += servicio * (1 + rnd.uniform(-jitter, jitter))
        restantes[i] -= 1
        atendidos[i] += 1
        llegada[i] = t + pausa
    return esperas, atendidos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=40, help='goals por cliente')
    ap.add_argument('--servicio', type=float, default=3.05,
                    help='s por movimiento (duracion_movimiento_s del broker + ~50 ms)')
    ap.add_argument('--pausa', type=float, default=0.5, help='pausa_s del cliente')
    ap.add_argument('--tau', type=float, default=8.0)
    ap.add_argument('--prioridades', type=int, nargs='+', default=[1, 2, 3, 4])
    ap.add_argument('--semilla', type=int, default=7)
    ap.add_argument('--jitter', type=float, default=0.03)
    a = ap.parse_args()

    print(f'{len(a.prioridades)} clientes, prioridades {a.prioridades}, {a.n} goals c/u, '
          f'servicio {a.servicio}s, pausa {a.pausa}s, tau {a.tau}s\n')
    for pol in ('fifo', 'prioridad'):
        esp, at = simular(pol, a.prioridades, a.n, a.servicio, a.pausa, a.tau, a.semilla, a.jitter)
        todas = [w for e in esp for w in e]
        print(f'=== {pol}')
        print(f'  espera media {statistics.mean(todas):6.2f} s   p95 {p95(todas):6.2f} s   '
              f'máxima {max(todas):6.2f} s')
        peor = a.prioridades.index(min(a.prioridades))
        for pr in sorted(set(a.prioridades), reverse=True):
            ws = [w for i, e in enumerate(esp) if a.prioridades[i] == pr for w in e]
            print(f'    prioridad {pr}: media {statistics.mean(ws):6.2f}  p95 {p95(ws):6.2f}  '
                  f'máx {max(ws):6.2f}')
        print(f'  índice de inanición (máx. de la prioridad {min(a.prioridades)}): '
              f'{max(esp[peor]):.2f} s')
        print(f'  Jain sobre goals atendidos: {jain(at):.3f}\n')


if __name__ == '__main__':
    main()
