# Reto del Brazo 2 — paquetes base

**Universidad ESAN · Curso de Robótica**

Andamiaje entregado por el curso. Compila y corre tal cual: el broker arranca, publica
`/arm/queue_state` y acepta clientes. Lo que falta son las decisiones que el reto evalúa,
marcadas en el código como `IMPLEMENTAR`.

> **Autoría.** Esta estructura la entrega el curso y es idéntica para todos los equipos.
> Decláralo en el README de tu repositorio. Lo que es de ustedes es lo que escriban dentro
> de los bloques `IMPLEMENTAR`, y es lo único que se califica.

---

## Paso 0 · Antes de empezar: ¿tu máquina está lista?

Si ya trabajaste con el brazo en clase, probablemente sí. Compruébalo en 30 segundos:

```bash
echo "$ROS_DISTRO · dominio $ROS_DOMAIN_ID · localhost_only $ROS_LOCALHOST_ONLY"
command -v colcon >/dev/null && echo "colcon OK"
ls /opt/ros/humble/share/rosidl_default_generators >/dev/null 2>&1 && echo "rosidl OK"
ls -d /opt/ros/humble/share/rosbag2* >/dev/null 2>&1 && echo "rosbag2 OK"
python3 -c "import matplotlib" 2>/dev/null && echo "matplotlib OK"
ping -c 1 -W 2 $JETSON >/dev/null 2>&1 && echo "llego al Jetson"
```

Tienen que salir las seis líneas, y el dominio debe ser el mismo del Jetson.

**Si falta algo, está todo en `Guia_Configuracion_Raspberry.md`**, en esta misma carpeta.
Los dos que suelen faltar para el reto y no hacían falta en clase:

```bash
sudo apt install -y ros-humble-rosbag2 ros-humble-rosbag2-storage-default-plugins \
                    python3-matplotlib
```

`rosbag2` es para grabar la evidencia y `matplotlib` para la figura comparativa: sin
ellos no se puede entregar el ítem 3.

Y recuerda que **en cada terminal nueva** hace falta:

```bash
source ~/rb2_ws/install/setup.bash
```

---

## Compilar

```bash
mkdir -p ~/rb2_ws/src && cp -r src/* ~/rb2_ws/src/
cd ~/rb2_ws && colcon build
source install/setup.bash

ros2 interface show arm_broker_interfaces/action/MoveArm
ros2 interface show arm_broker_interfaces/msg/QueueState
```

---

## Qué hay que escribir

| Archivo | Bloque | Ítem | Qué decide |
|---|---|---|---|
| `fk.py` | `DH` y `fk(q)` | 1 | La tabla Denavit-Hartenberg y la cinemática directa |
| `broker.py` | `goal_callback` | 2 | Admisión: qué se rechaza y con qué motivo |
| `broker.py` | `handle_accepted_callback` | 2 | Encolar. Aquí no se ejecuta nada |
| `broker.py` | `_worker` | 2 | Desencolar y ejecutar de a uno |
| `broker.py` | `execute_callback` | 2 | Mover, con feedback y cancelación |
| `politicas.py` | `FIFO` y la segunda | 2 · 3 | El orden de atención |

Todo lo demás está completo: los manifiestos, el `CMakeLists.txt`, el `setup.py`, las
interfaces, el publicador de `/arm/queue_state`, el nodo cliente y los scripts de
análisis. Es plomería e instrumentación.

---

## Correr

```bash
# El broker, en el Jetson. Uno por equipo.
ros2 run arm_broker broker --ros-args -p politica:=fifo

# Cada integrante, desde su Raspberry:
ros2 run arm_broker cliente --ros-args \
  -p client_id:=tu_nombre -p priority:=3 -p traza:=carga.csv

# Para ver la cola:
ros2 topic echo /arm/queue_state
```

El driver `sync_plan_nx` tiene que estar corriendo en el Jetson.

---

## Medir

```bash
python3 herramientas/generar_carga.py --n 40 --semilla 7 --salida carga.csv

ros2 bag record -o fifo /arm/queue_state /joint_states
# ...corrida con los cuatro clientes...

python3 analisis/exportar_csv.py fifo --salida fifo/
python3 analisis/metricas.py fifo/queue_state.csv prioridad/queue_state.csv
```

**Graben siempre `/arm/queue_state`.** `/joint_states` dice qué poses pasaron, no quién
esperó cuánto. Sin ese tópico no hay métricas.

Las dos corridas —una por política— tienen que usar **la misma carga**. Si cada una usa
poses distintas, los resultados no se pueden comparar.

---

## Verificar la cinemática directa

```bash
python3 herramientas/verificar_fk.py
```

Se corre en el Jetson, con el puerto serie libre. Lleva el brazo a varias poses, lee su
posición real y la compara con `fk(q)`. Criterio del reto: error ≤ 10 mm.

---

## Dos cosas que conviene saber antes de empezar

**El identificador del pedido.** `QueueState` lleva `queued_goal_ids` y
`executing_goal_id`. Un `ros2 bag` de `/joint_states` no registra quién publicó cada
mensaje, así que por sí solo no demuestra si hubo publicadores concurrentes.
Correlacionar contra `/arm/queue_state` sí lo demuestra: si en cada instante hay un único
`executing_goal_id`, la exclusión mutua se cumplió. Guarden ese argumento para la
sustentación.

**La prioridad.** `MoveArm.action` la declara de 0 a 255, donde **mayor número = más
urgente**. El índice de inanición es entonces la espera máxima del número más bajo. Si
prefieren la convención contraria, cámbienla en la interfaz y en `metricas.py`, y déjenlo
escrito.
