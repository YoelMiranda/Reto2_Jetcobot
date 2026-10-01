# RB-2 · El Turno del Brazo — equipo arm-03

**GRUPO 5**


> **Autoría.** La estructura del repositorio (manifiestos, interfaces, `cliente.py`, nodo
> publicador de `/arm/queue_state`, scripts de análisis) la entrega el curso y es idéntica para
> todos los equipos. Lo nuestro es lo que está dentro de los bloques `IMPLEMENTAR`:
> `fk.py` (ítem 1), `broker.py` y `politicas.py` (ítems 2 y 3) y `herramientas/auditar_ik.py`,
> `herramientas/simular_prediccion.py` y `herramientas/probar_cuatro_clientes.sh` (ítems 3 y 4).

## Contenido

| Ruta | Qué es |
|---|---|
| `src/arm_broker/arm_broker/fk.py` | Ítem 1. Tabla DH y `fk(q)` |
| `src/arm_broker/arm_broker/broker.py` | Ítem 2. Admisión con FK, cola, worker único, ejecución |
| `src/arm_broker/arm_broker/politicas.py` | Ítems 2 y 3. FIFO y prioridad con envejecimiento |
| `herramientas/verificar_fk.py` | Compara `fk(q)` con lo que lee el brazo (ítem 1) |
| `herramientas/auditar_ik.py` | Ítem 4. Audita la IK del firmware con la FK propia |
| `herramientas/generar_carga.py` | Traza de poses para las corridas (ítem 3) |
| `herramientas/simular_prediccion.py` | Predicción de esperas antes de medir (ítem 3) |
| `herramientas/probar_cuatro_clientes.sh` | Prueba de humo con 4 clientes en una sola máquina |
| `herramientas/conectar_rb2.sh` | Deja una terminal de la Raspberry en el dominio del equipo (`source`) |
| `analisis/` | Exportar el bag a CSV y calcular métricas y figura |
| `matlab/` | Código MATLAB que valida la matriz T contra `control_joints` |
| `docs/` | Evidencia del ítem 1, diagrama de secuencia, guía de ejecución y guía de la Raspberry |
| `evidencia/` | Registro de rechazos con motivo (ítem 2) |

## Estado de los ítems

| Ítem | Estado | Evidencia |
|---|---|---|
| 1 · Cinemática directa | Verificada contra el brazo real: error máximo 7.1 mm en 5 poses (criterio ≤ 10 mm) | `docs/RB2_item1_evidencia.md`, `matlab/` |
| 2 · Broker con cola y admisión | Implementado; rechazos registrados con motivo | `evidencia/rechazos_item2.csv`, `docs/diagrama_secuencia.png` |
| 3 · Medición bajo contención | _(se completa tras las corridas)_ | |
| 4 · Auditoría de la IK | _(se completa tras la corrida válida)_ | |

Resultado del ítem 1: con los datos del fabricante el error máximo fue 12.9 mm; un único ajuste de
`d6` (45.6 → 53.7 mm, el punto que reporta el firmware está unos 8 mm más allá del flange) lo
baja a 7.1 mm. La calibración con 3 poses predice bien las otras 2.

## Compilar

```bash
mkdir -p ~/rb2_ws/src && cp -r src/* ~/rb2_ws/src/
cd ~/rb2_ws && colcon build
source install/setup.bash
```

## Correr

```bash
# Jetson: driver (una sola persona) y, en otra terminal, el broker
ros2 run jetcobot_driver sync_plan_nx
ros2 run arm_broker broker --ros-args -p politica:=fifo          # o politica:=prioridad

# Cada integrante, desde su Raspberry
ros2 run arm_broker cliente --ros-args -p client_id:=<nombre> -p priority:=<1-4> -p traza:=carga.csv

ros2 topic echo /arm/queue_state
```

Antes del primer movimiento, el brazo debe estar en la pose cero: el broker parte de
`q_actual = 0` para calcular el paso articular y no puede leer el brazo real.

## Ítem 2 · pruebas de admisión

Con el broker corriendo, cada línea debe ser rechazada y quedar en `rechazos.csv`
(carpeta desde la que se lanzó el broker) con su motivo:

```bash
A=arm_broker_interfaces/action/MoveArm
ros2 action send_goal /move_arm $A "{joint_positions: [3.5,0,0,0,0,0], client_id: prueba, priority: 1}"   # límite
ros2 action send_goal /move_arm $A "{joint_positions: [0,2.3,0,0,0,0], client_id: prueba, priority: 1}"   # workspace
ros2 action send_goal /move_arm $A "{joint_positions: [1.5,-0.4,0.4,0,0.3,0], client_id: prueba, priority: 1}"  # paso
```

Exclusión mutua: en `/arm/queue_state` debe verse un único `executing_goal_id` en cada
instante, y solo el broker publica en `/joint_states` (`ros2 topic info /joint_states -v`
debe mostrar un publicador).

## Ítem 3 · medición

```bash
python3 herramientas/generar_carga.py --n 40 --semilla 7 --salida carga.csv    # misma traza para todos

# una corrida por política, con la MISMA carga y los 4 clientes lanzados a la vez
ros2 run arm_broker broker --ros-args -p politica:=fifo -p paso_max_rad:=2.0
ros2 bag record -o fifo /arm/queue_state /joint_states
# ... 4 clientes ...  (Ctrl+C al bag cuando terminen)

ros2 run arm_broker broker --ros-args -p politica:=prioridad -p paso_max_rad:=2.0
ros2 bag record -o prioridad /arm/queue_state /joint_states

python3 analisis/exportar_csv.py fifo --salida fifo/
python3 analisis/exportar_csv.py prioridad --salida prioridad/
python3 analisis/metricas.py fifo/queue_state.csv prioridad/queue_state.csv
```

`paso_max_rad:=2.0` se usa en ambas corridas para que la traza aleatoria no genere rechazos
por paso articular según el momento en que llega cada goal, y así las dos políticas atiendan
exactamente los mismos pedidos. Los rechazos se demuestran con las pruebas del ítem 2.

## Ítem 4 · auditoría de la IK

En el Jetson, con `sync_plan_nx` detenido (el puerto serie debe estar libre):

```bash
python3 herramientas/auditar_ik.py --x 150 --y 0 --z 80 [--orientacion RX RY RZ]
```

## Política elegida y por qué

Prioridad con envejecimiento (τ = 8 s). Un cliente urgente no debería esperar detrás de uno
que no lo es, pero una prioridad estática deja a las bajas esperando sin cota. El
envejecimiento conserva la preferencia por los urgentes y acota la espera del menos urgente.
La predicción y sus supuestos están en el documento de diseño previo entregado por separado.

## Limitaciones conocidas

- El paso articular se valida contra la última pose publicada al momento de la llegada del goal, no
  contra la que tendrá el brazo cuando le toque a ese goal.
- `cola_max` es una cota blanda: dos goals que llegan a la vez pueden dejarla en `cola_max + 1`.
- Un rechazo solo devuelve `accepted=False` al cliente; el motivo queda en el log y en `rechazos.csv`.
