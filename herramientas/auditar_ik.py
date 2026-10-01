#!/usr/bin/env python3
"""Ítem 4 — Audita con la FK propia la cinemática inversa del firmware.

Un único objetivo cartesiano (x, y, z) sobre el tablero de la mesa se manda con
send_coords() de pymycobot. El firmware resuelve la cinemática inversa (nosotros
no escribimos solver). Luego se lee el vector articular q realmente ejecutado, se
calcula FK(q) con nuestro fk.py y se mide el error contra lo solicitado.

Se corre EN EL JETSON, con el puerto serie libre (sin sync_plan_nx corriendo).
Colóquenlo en la carpeta herramientas/ del kit (usa ../src/arm_broker/arm_broker/fk.py).

    python3 auditar_ik.py --x 180 --y 0 --z 120
    python3 auditar_ik.py --x 180 --y 0 --z 120 --orientacion -90 0 -90
    python3 auditar_ik.py --desde-angulos 0 -60 60 0 30 0       # objetivo alcanzable por construcción
    python3 auditar_ik.py --x 180 --y 0 --z 120 --simular      # sin robot, para probar

Antes de mover pide confirmación (Enter). Ctrl+C cancela.
"""
import argparse, csv, math, os, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'src', 'arm_broker'))
from arm_broker import fk                                          # noqa: E402

POSE_INICIAL_RAD = [0.0, -0.5, 0.5, 0.0, 0.5, 0.0]   # 'ready' del kit


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class BrazoSimulado:
    """Simula el brazo con la propia FK (para probar el script sin robot)."""

    def __init__(self):
        self.q = [0.0] * 6
        self.ori = [-90.0, 0.0, -90.0]

    def send_angles(self, angulos_deg, vel):
        self.q = [math.radians(a) for a in angulos_deg]

    def send_coords(self, coords, vel, modo):
        from scipy.optimize import least_squares
        objetivo = coords[:3]
        f = lambda q: [a - b for a, b in zip(fk.fk(q), objetivo)]
        self.q = list(least_squares(f, self.q).x)      # IK numérica de mentira
        self.ori = list(coords[3:6])

    def get_angles(self):
        return [math.degrees(v) for v in self.q]

    def get_coords(self):
        return [*[v + 0.8 for v in fk.fk(self.q)], *self.ori]

    def is_moving(self):
        return 0


def conectar(args):
    if args.simular:
        return BrazoSimulado()
    try:
        from pymycobot.mycobot import MyCobot
    except ImportError:
        from pymycobot import MyCobot
    return MyCobot(args.puerto, args.baud)


def leer(brazo, intentos=5):
    for _ in range(intentos):
        ang, crd = brazo.get_angles(), brazo.get_coords()
        if ang and crd and len(ang) == 6 and len(crd) >= 6:
            return ang, crd
        time.sleep(0.3)
    return None, None


def esperar_fin(brazo, timeout):
    t0 = time.time()
    time.sleep(0.5)
    while time.time() - t0 < timeout:
        try:
            if brazo.is_moving() == 0:
                break
        except Exception:
            pass
        time.sleep(0.2)
    time.sleep(1.0)                                 # asentamiento


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--x', type=float, help='mm')
    ap.add_argument('--y', type=float, help='mm')
    ap.add_argument('--z', type=float, help='mm (altura del tablero + margen)')
    ap.add_argument('--desde-angulos', type=float, nargs=6, metavar='Q',
                    help='6 ángulos en grados: el brazo va a esa pose, se lee get_coords() y ESAS '
                         'coordenadas (con su orientación) son el objetivo. Garantiza que sea alcanzable')
    ap.add_argument('--orientacion', type=float, nargs=3, metavar=('RX', 'RY', 'RZ'),
                    help='grados; por defecto la que tiene el brazo en la pose inicial')
    ap.add_argument('--modo', type=int, default=0, choices=[0, 1],
                    help='send_coords: 0 angular (por defecto), 1 lineal')
    ap.add_argument('--velocidad', type=int, default=20)
    ap.add_argument('--timeout', type=float, default=15.0)
    ap.add_argument('--sin-pose-inicial', action='store_true',
                    help='no ir antes a la pose ready; usar la pose actual')
    ap.add_argument('--puerto', default='/dev/ttyUSB0')
    ap.add_argument('--baud', type=int, default=1000000)
    ap.add_argument('--salida', default='item4_resultado.csv')
    ap.add_argument('--simular', action='store_true')
    ap.add_argument('--si', action='store_true', help='no pedir confirmación')
    args = ap.parse_args()

    if not args.desde_angulos and None in (args.x, args.y, args.z):
        sys.exit('Indiquen --x --y --z, o --desde-angulos q1 q2 q3 q4 q5 q6 (grados).')

    brazo = conectar(args)

    ori_objetivo = None
    if args.desde_angulos:
        print('Llevando el brazo a la pose de referencia para leer un objetivo alcanzable...')
        brazo.send_angles(list(args.desde_angulos), args.velocidad)
        esperar_fin(brazo, args.timeout)
        _, crd_ref = leer(brazo)
        if crd_ref is None:
            sys.exit('El brazo no respondió al leer la pose de referencia.')
        args.x, args.y, args.z = crd_ref[:3]
        ori_objetivo = crd_ref[3:6]
        print(f'Objetivo tomado de esa pose: ({args.x:.1f}, {args.y:.1f}, {args.z:.1f}) mm, '
              f'orientación {[round(v, 1) for v in ori_objetivo]} deg')

    objetivo = [args.x, args.y, args.z]
    r = math.sqrt(sum(v * v for v in objetivo))
    if r > fk.ALCANCE_MAX_MM or r < fk.ALCANCE_MIN_MM or args.z < 0:
        sys.exit(f'Objetivo fuera del alcance del brazo ({r:.0f} mm de la base; '
                 f'permitido {fk.ALCANCE_MIN_MM:.0f}–{fk.ALCANCE_MAX_MM:.0f}, z ≥ 0). No se mueve.')

    if not args.sin_pose_inicial:
        print('Llevando el brazo a la pose inicial (ready)...')
        brazo.send_angles([math.degrees(v) for v in POSE_INICIAL_RAD], args.velocidad)
        esperar_fin(brazo, args.timeout)

    ang0, crd0 = leer(brazo)
    if ang0 is None:
        sys.exit('El brazo no respondió; revisen el puerto o que sync_plan_nx no esté corriendo.')
    ori = args.orientacion or ori_objetivo or crd0[3:6]
    print(f'Pose inicial q (deg) = {[round(v, 1) for v in ang0]}')
    print(f'Objetivo pedido      = ({args.x:.1f}, {args.y:.1f}, {args.z:.1f}) mm, '
          f'orientación = {[round(v, 1) for v in ori]} deg, modo {args.modo}')

    if not args.si:
        input('Tablero despejado y mano lejos del brazo. Enter para mover (Ctrl+C cancela)... ')

    brazo.send_coords([*objetivo, *ori], args.velocidad, args.modo)
    esperar_fin(brazo, args.timeout)

    ang, crd = leer(brazo)
    if ang is None:
        sys.exit('No se pudo leer el brazo tras el movimiento; repitan.')

    movio = max(abs(b - a) for a, b in zip(ang0, ang)) > 1.0      # grados
    if not movio:
        print('\n' + '!' * 66)
        print('El brazo NO se movió: el firmware ignoró send_coords().')
        print('Causa probable: objetivo inalcanzable con esa orientación (o fuera de su rango).')
        print('El "error" de abajo NO es una medición válida de la IK, y no se guarda en el CSV.')
        print('Prueben otro punto, otra --orientacion, o --modo 1. Ver GUIA_EJECUCION_RB2.md.')
        print('!' * 66)

    q = [math.radians(v) for v in ang]
    p_fk = fk.fk(q)
    err_pedido = dist(p_fk, objetivo)                 # métrica del ítem 4
    err_firmware = dist(crd[:3], objetivo)            # lo que reporta el propio brazo
    err_fk_vs_fw = dist(p_fk, crd[:3])                # calidad de nuestra FK (ítem 1)

    print('\n' + '-' * 66)
    print(f'q ejecutado (deg)        = {[round(v, 2) for v in ang]}')
    print(f'FK(q) propia             = ({p_fk[0]:.1f}, {p_fk[1]:.1f}, {p_fk[2]:.1f}) mm')
    print(f'get_coords() del brazo   = ({crd[0]:.1f}, {crd[1]:.1f}, {crd[2]:.1f}) mm')
    print(f'ERROR FK(q) vs pedido    = {err_pedido:.2f} mm   <- error cartesiano del ítem 4')
    print(f'error get_coords/pedido  = {err_firmware:.2f} mm')
    print(f'error FK(q) vs get_coords= {err_fk_vs_fw:.2f} mm   (debe ser <= 10 mm, ítem 1)')
    print('-' * 66)
    print('Solución elegida por el firmware (para la pregunta de la semana 5):')
    print(f'  q2 = {ang[1]:+.1f}°, q3 = {ang[2]:+.1f}°  -> codo '
          f'{"con q3 > 0" if ang[2] > 0 else "con q3 < 0"}; '
          f'q5 = {ang[4]:+.1f}° (muñeca {"positiva" if ang[4] > 0 else "negativa"})')
    print(f'  distancia articular desde la pose inicial: '
          f'{[round(b - a, 1) for a, b in zip(ang0, ang)]} deg')

    if not movio:
        sys.exit(2)

    nuevo = not os.path.exists(args.salida)
    with open(args.salida, 'a', newline='') as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(['t', 'x_pedido', 'y_pedido', 'z_pedido', 'q1', 'q2', 'q3', 'q4', 'q5',
                        'q6', 'fk_x', 'fk_y', 'fk_z', 'fw_x', 'fw_y', 'fw_z',
                        'err_fk_vs_pedido', 'err_fw_vs_pedido', 'err_fk_vs_fw'])
        w.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), *objetivo, *[round(v, 3) for v in ang],
                    *[round(v, 2) for v in p_fk], *[round(v, 2) for v in crd[:3]],
                    round(err_pedido, 2), round(err_firmware, 2), round(err_fk_vs_fw, 2)])
    print(f'Guardado en {args.salida}')


if __name__ == '__main__':
    main()
