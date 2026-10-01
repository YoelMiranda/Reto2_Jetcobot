# RB-2 · Ítem 1 — Cinemática directa verificada (JetCobot)

## 1. Tabla Denavit-Hartenberg (convención estándar)

T(i-1→i) = Rz(θi) · Tz(di) · Tx(ai) · Rx(αi), con θi = qi + offset.

| i | θi (offset) | di (mm) | ai (mm) | αi |
|---|---|---|---|---|
| 1 | q1 + 0 | 131.22 | 0 | π/2 |
| 2 | q2 − π/2 | 0 | −110.4 | 0 |
| 3 | q3 + 0 | 0 | −96 | 0 |
| 4 | q4 − π/2 | 63.4 | 0 | π/2 |
| 5 | q5 + π/2 | 75.05 | 0 | −π/2 |
| 6 | q6 + 0 | **53.7** | 0 | 0 |

Las cotas del plano del fabricante (135, 110, 96, 75 mm) corresponden a d1, a2, a3 y d5.
La posición del efector es la última columna de T(0→6) = A1·A2·A3·A4·A5·A6.
d6 partió en 45.6 mm (hoja de datos) y quedó en 53.7 mm tras la calibración de la sección 5.

## 2. Implementación

- MATLAB: `verificar_fk_jetcobot.m` (matriz homogénea y comparación con `control_joints.ipynb`).
- Python: `fk.py` del paquete `arm_broker` (`fk(q)` devuelve x, y, z en mm).
  `_t()` del kit usa DH modificada, así que `fk.py` guarda la misma tabla en esa forma
  (alpha_{i-1}, a_{i-1}, d_i, offset_i). Ambas versiones dan resultados idénticos.

## 3. Predicción (declarada antes de medir, con d6 = 45.6 mm de la hoja de datos)

| Pose | q (grados) | FK predicha (x, y, z) mm |
|---|---|---|
| Cero | [0, 0, 0, 0, 0, 0] | (45.6, −63.4, 412.7) |
| A | [0, −30, 30, 0, 30, 0] | (94.7, −40.6, 397.9) |
| B | [30, −20, 20, 0, 15, 0] | (96.6, −3.8, 406.0) |
| C | [0, −60, 60, 0, 0, 0] | (141.2, −63.4, 357.5) |
| D | [45, −30, 30, 30, 30, 0] | (65.4, 8.0, 407.6) |

q6 no cambia la posición del efector, por lo que su valor no afecta la predicción.

## 4. Medición y error inicial (predicción previa)

| Pose | Medido (x, y, z) mm | Δ (x, y, z) mm | Error (mm) | ≤ 10 mm |
|---|---|---|---|---|
| Cero | (52.6, −64.7, 409.2) | (+7.0, −1.3, −3.5) | 7.9 | Sí |
| A | (104.6, −40.3, 393.3) | (+9.9, +0.3, −4.6) | 10.9 | No |
| B | (105.7, −1.1, 401.5) | (+9.1, +2.7, −4.5) | 10.5 | No |
| C | (152.5, −62.0, 351.3) | (+11.3, +1.4, −6.2) | 12.9 | No |
| D | (71.3, 13.3, 406.4) | (+5.9, +5.3, −1.2) | 8.0 | Sí |

Error medio 10.1 mm, máximo 12.9 mm. El sesgo es sistemático: las diferencias son siempre
positivas en x y negativas en z, lo que apunta a un punto de referencia del firmware más allá
del flange, no a un error en los eslabones.

## 5. Calibración de d6 y verificación

Hipótesis: el punto que reporta el brazo está unos milímetros más allá del flange, sobre el
eje z6. Se ajustó solo d6 por mínimos cuadrados.

- Ajuste con las 3 primeras poses (Cero, A, B): d6 = 53.6 mm.
- Con ese valor, las poses no usadas en el ajuste dan error de 7.1 mm (C) y 6.7 mm (D).
- Ajuste con las 5 poses: d6 = 53.7 mm (valor adoptado, +8.1 mm sobre la hoja de datos).

| Pose | FK con d6 = 53.7 (x, y, z) mm | Error (mm) | ≤ 10 mm |
|---|---|---|---|
| Cero | (53.7, −63.4, 412.7) | 3.9 | Sí |
| A | (101.7, -36.5, 397.9) | 6.6 | Sí |
| B | (102.4, 1.9, 406.0) | 6.4 | Sí |
| C | (149.3, -63.4, 357.5) | 7.1 | Sí |
| D | (66.8, 15.1, 411.1) | 6.7 | Sí |

Error medio 6.1 mm, máximo 7.1 mm, dentro del criterio de 10 mm.

## 6. Conclusión

La predicción con los datos del fabricante dio error máximo de 12.9 mm, con un sesgo
constante en la dirección del eje z6. Corregir d6 de 45.6 a 53.7 mm lo reduce a un máximo de
7.1 mm en las cinco poses, y la calibración hecha con tres poses predice bien las dos
restantes. La tabla DH queda validada y se usa como portero de admisión (ítem 2) y como
instrumento de auditoría de la cinemática inversa del firmware (ítem 4).
