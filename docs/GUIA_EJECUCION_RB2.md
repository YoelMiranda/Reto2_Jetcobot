# RB-2 · Guía de ejecución desde la Raspberry (arm-03, ROS_DOMAIN_ID 72)

La Raspberry hace de puente. Se separan dos tipos de comandos:

- **En el Jetson (entrando por ssh desde la Raspberry):** todo lo que abre el puerto serie del
  brazo: `verificar_fk.py`, `auditar_ik.py`, llevar el brazo a cero, el driver y el broker.
- **En la Raspberry (local):** comandos de ROS (`ros2 topic`, `ros2 action`) y los clientes.

Reglas del laboratorio: avisa en voz alta antes de mover el brazo, mira que no haya manos
cerca, y si algo falla no cambies permisos ni detengas servicios: levanta la mano.

| Terminal | Dónde | Para qué |
|---|---|---|
| R1 | Raspberry (local) | Compilar, pruebas de ROS, clientes |
| J0 | Raspberry → `ssh jetson@$JETSON` | Ítems 1 y 4, llevar a cero |
| JA | Raspberry → `ssh jetson@$JETSON` | Driver `sync_plan_nx` |
| JB | Raspberry → `ssh jetson@$JETSON` | Broker |

---

## 1. Llevar el zip a la Raspberry

Desde la laptop (PowerShell). La IP de la Raspberry sale con `ip -4 addr show scope global`
en la Raspberry.

```powershell
scp kit_reto_alumno_RB2.zip <usuario>@<IP_RASPBERRY>:~/
```

Si no llegas por red, sirve un USB o descargarlo desde OneDrive en la Raspberry.

## 2. En la Raspberry (R1): descomprimir y compilar

```bash
cd ~ && unzip -o kit_reto_alumno_RB2.zip
mkdir -p ~/rb2_ws/src && cp -r ~/kit_RB2/src/* ~/rb2_ws/src/
cd ~/rb2_ws && colcon build
source ~/rb2_ws/install/setup.bash
```

Tarda unos minutos porque genera código de las interfaces. Debe terminar con
`Summary: 2 packages finished`.

## 3. Pasar el kit al Jetson y compilar allá

Todavía en la Raspberry (`$JETSON` ya está definido en `~/.bashrc`):

```bash
scp ~/kit_reto_alumno_RB2.zip jetson@$JETSON:~/
ssh jetson@$JETSON
```

Ahora estás en `jetson@yahboom` (terminal J0):

```bash
cd ~ && unzip -o kit_reto_alumno_RB2.zip || python3 -m zipfile -e kit_reto_alumno_RB2.zip .
echo "$ROS_DISTRO · dominio $ROS_DOMAIN_ID · localhost_only $ROS_LOCALHOST_ONLY"
which colcon
python3 -c "import pymycobot; print('pymycobot OK')"
ls /dev/ttyUSB* /dev/ttyTHS* 2>/dev/null
mkdir -p ~/rb2_ws/src && cp -r ~/kit_RB2/src/* ~/rb2_ws/src/
cd ~/rb2_ws && colcon build && source install/setup.bash
```

- Debe decir `humble · dominio 72 · localhost_only 0`. Si el dominio es otro:
  `export ROS_DOMAIN_ID=72`.
- Si falta `colcon` o `pymycobot`, no instales nada: avisa al profesor.
- Anota el puerto que salga. Si no es `/dev/ttyUSB0`, agrega `--puerto <el que salga>` a los
  scripts de los pasos 4 y 5 (y cámbialo en el comando del paso 6).

## 4. Ítem 1: comprobar la FK en el brazo real (J0)

Confirma que nadie tiene el brazo (`sync_plan_nx` detenido) y avisa en voz alta.

```bash
cd ~/kit_RB2
python3 herramientas/verificar_fk.py --solo-leer      # solo lee, no mueve
python3 herramientas/verificar_fk.py                  # mueve a 4 poses
```

El error debe salir ≤ 10 mm. Si dice "el brazo no respondió", revisa el puerto o que no haya
otro programa usándolo.

## 5. Ítem 4: auditar la cinemática inversa del firmware (J0)

Mesa despejada y manos lejos del brazo:

```bash
python3 herramientas/auditar_ik.py --x 150 --y 0 --z 80
```

Con una orientación medida en el robot se agregan tres números reales (no las letras):
`--orientacion -92.1 1.7 -61.2`.

Si el script avisa **"El brazo NO se movió"**, el firmware ignoró `send_coords()` porque el
objetivo no es alcanzable con esa orientación. Esa corrida no es válida y no se guarda en el
CSV. Prueba un punto que el brazo sí alcance (ver abajo).

**Cómo conseguir un objetivo alcanzable.** Con el driver detenido, lleva el brazo a una pose
segura por encima del tablero, léelo y usa esas coordenadas como objetivo:

```bash
python3 -c "from pymycobot.mycobot import MyCobot; m=MyCobot('/dev/ttyUSB0',1000000); print(m.get_coords()); print(m.get_angles())"
```

`get_coords()` devuelve `[x, y, z, rx, ry, rz]`. Pide ese mismo punto con
`--x --y --z --orientacion rx ry rz`. Baja de a poco la `z`. Ojo: la `z` es la del flange, y
un gripper apuntando hacia abajo llega más abajo que eso.

- La `z` debe ser la altura del tablero más un pequeño margen.
- Con la orientación por defecto (la de la pose ready) el punto puede no ser alcanzable. Para
  conseguir una orientación útil, pon la herramienta apuntando al tablero desde
  `control_joints`, lee `get_coords()` y usa sus tres últimos valores (rx, ry, rz).
- Pide Enter antes de mover, imprime el error cartesiano y guarda `item4_resultado.csv`.
- Copia la salida y el CSV para completar `docs/RB2_item4_evidencia.md`.

## 6. Llevar el brazo a la pose cero (J0)

El broker parte de `q_actual = 0`, así que el brazo debe quedar en cero antes de levantar el
driver:

```bash
python3 -c "from pymycobot.mycobot import MyCobot; m=MyCobot('/dev/ttyUSB0',1000000); m.send_angles([0,0,0,0,0,0],20)"
```

Espera a que deje de moverse. Después sal de esta sesión con `exit` o déjala abierta.

## 7. Levantar driver y broker (una sola persona)

Abre dos terminales más en la Raspberry y entra al Jetson en cada una con
`ssh jetson@$JETSON`.

**JA: driver**
```bash
source ~/jetcobot_colcon_ws/install/setup.bash
ros2 run jetcobot_driver sync_plan_nx
```

**JB: broker** (se lanza desde `~/kit_RB2` para que `rechazos.csv` quede ahí)
```bash
source ~/rb2_ws/install/setup.bash
cd ~/kit_RB2
ros2 run arm_broker broker --ros-args -p politica:=fifo
```

Debe imprimir `arm_broker listo · política=fifo … único publicador de /joint_states`.

## 8. Pruebas desde la Raspberry (R1, terminal local)

En cada terminal nueva de la Raspberry, primero estas dos líneas (`conectar_rb2.sh` viene en el kit;
cópialo desde el repo con `cp herramientas/conectar_rb2.sh ~/`). El dominio queda en 72 por defecto:

```bash
source ~/rb2_ws/install/setup.bash
source ~/conectar_rb2.sh $JETSON     # (si el laboratorio usa Discovery Server: agrega  72 --discovery)
```

### 8.1 Publicador único y estado de la cola

```bash
ros2 topic info /joint_states -v            # un solo publicador: el broker
ros2 topic echo /arm/queue_state --once
```

### 8.2 Rechazos con motivo (admisión con FK)

```bash
A=arm_broker_interfaces/action/MoveArm
ros2 action send_goal /move_arm $A "{joint_positions: [3.5,0,0,0,0,0], client_id: prueba, priority: 1}"
ros2 action send_goal /move_arm $A "{joint_positions: [0,2.3,0,0,0,0], client_id: prueba, priority: 1}"
ros2 action send_goal /move_arm $A "{joint_positions: [1.5,-0.4,0.4,0,0.3,0], client_id: prueba, priority: 1}"
```

Los tres deben decir `Goal rejected`, por: límite articular, workspace y paso articular. El
registro con motivo queda en el Jetson. Para verlo, en J0 o JB:

```bash
cat ~/kit_RB2/rechazos.csv
```

### 8.3 Prueba corta con un cliente

```bash
cd ~/kit_RB2
python3 herramientas/generar_carga.py --n 5 --salida carga_corta.csv
ros2 run arm_broker cliente --ros-args -p client_id:=yoel -p priority:=3 -p traza:=carga_corta.csv
```

Después, cada integrante puede levantar su cliente desde su Raspberry, con su propio
`client_id` y `priority` (1 a 4; mayor número = más urgente). Para una prueba de humo con 4
clientes en una sola máquina:

```bash
bash herramientas/probar_cuatro_clientes.sh carga_corta.csv
```

Con varios clientes en disputa, `/arm/queue_state` debe mostrar un único
`executing_goal_id` en cada instante.

## 9. Medición del ítem 3

Antes de medir, firmen `docs/RB2_diseno_previo.md` (contiene la predicción de esperas).

```bash
python3 herramientas/generar_carga.py --n 40 --semilla 7 --salida carga.csv    # misma traza para todos
```

Una corrida por política, con la misma carga y los cuatro clientes lanzados a la vez. El
broker se reinicia con cada política (Ctrl+C en JB y de nuevo) y con el brazo en cero:

```bash
# JB (Jetson): broker
ros2 run arm_broker broker --ros-args -p politica:=fifo -p paso_max_rad:=2.0
# R1 (Raspberry) o Jetson: grabación
ros2 bag record -o fifo /arm/queue_state /joint_states
# ... los 4 clientes ... (Ctrl+C al bag cuando terminen)
```

Repetir con `politica:=prioridad` y `ros2 bag record -o prioridad ...`. Luego:

```bash
python3 analisis/exportar_csv.py fifo --salida fifo/
python3 analisis/exportar_csv.py prioridad --salida prioridad/
python3 analisis/metricas.py fifo/queue_state.csv prioridad/queue_state.csv
```

`paso_max_rad:=2.0` se usa en ambas corridas para que la traza aleatoria no genere rechazos por
paso articular según el momento de llegada, y así las dos políticas atiendan los mismos
pedidos.

## 10. Al terminar

- Detén el broker y el driver con Ctrl+C.
- Avisa al equipo: el puerto del brazo vuelve a quedar libre.
- Guarda `item4_resultado.csv`, `rechazos.csv`, los bags, los CSV y la figura
  `comparacion_politicas.png`.
- Pendientes de entrega: video de 3 minutos con los 4 clientes en disputa y
  `/arm/queue_state` en pantalla, y cierre reflexivo de una página.

## Si algo falla

| Síntoma | Qué revisar |
|---|---|
| `ros2 node list` vacío en la Raspberry | Mismo dominio (72) en Raspberry y Jetson, `ROS_LOCALHOST_ONLY=0`, `ros2 daemon stop && ros2 daemon start`. Si en el Jetson también está vacío, nadie levantó el driver |
| "el brazo no respondió" en los scripts | El driver `sync_plan_nx` está usando el puerto, o el puerto no es `/dev/ttyUSB0` (`--puerto`) |
| El cliente se queda en "esperando al broker" | El broker no está corriendo o el dominio es distinto |
| Todos los goals se rechazan por paso articular | El brazo no estaba en cero al arrancar el broker (paso 6) |
| `unzip` no existe en el Jetson | `python3 -m zipfile -e kit_reto_alumno_RB2.zip .` |
