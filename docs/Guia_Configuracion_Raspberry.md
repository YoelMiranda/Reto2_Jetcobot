# Guía de configuración — Tu Raspberry y el JetCobot

**Universidad ESAN · Curso de Robótica · Ing. Gonzalo Justiniani**

Al terminar esta guía tu Raspberry podrá hablar con el JetCobot de tu equipo y correr
todo el material del curso.

Ningún programa que escribas tú toca el brazo directamente. Todos publican en un tópico,
y el único que mueve el robot es el driver, que corre dentro del Jetson. Por eso tu
Raspberry solo necesita dos cosas: **estar en la misma red que el Jetson** y **estar en su
mismo dominio de ROS 2**.

Necesitas de tu profesor: la **IP del Jetson** de tu equipo y el **ROS_DOMAIN_ID**.

---

## Paso 1 · Conectar la Raspberry a la red del laboratorio

Conéctala por cable o por la WiFi del laboratorio, y comprueba qué dirección le tocó:

```bash
ip -4 addr show scope global
```

Debe aparecer una dirección del rango del laboratorio, por ejemplo `172.51.9.30`.

Si sale algo que empieza por `169.254`, no recibió dirección: revisa el cable o la WiFi
antes de seguir.

Anota tu IP. La vas a necesitar si algo falla.

---

## Paso 2 · Comprobar que llegas al Jetson

```bash
JETSON=172.51.9.5          # reemplaza por la IP de tu equipo

ping -c 3 $JETSON
```

Si no responde, el problema es de red y no de ROS 2. Avisa al profesor antes de seguir:
nada de lo que viene va a funcionar.

Guarda la IP para no escribirla cada vez:

```bash
echo "export JETSON=$JETSON" >> ~/.bashrc
```

---

## Paso 3 · Instalar lo que hace falta

```bash
sudo apt update
sudo apt install -y \
  ros-humble-rosidl-default-generators \
  ros-humble-rosbag2 \
  ros-humble-rosbag2-storage-default-plugins \
  ros-humble-sensor-msgs \
  ros-humble-demo-nodes-cpp \
  ros-humble-turtlesim \
  python3-colcon-common-extensions \
  python3-matplotlib
```

Para qué sirve cada uno:

| Paquete | Para qué |
|---|---|
| `rosidl-default-generators` | Compilar los paquetes que definen acciones y servicios propios |
| `rosbag2` | Grabar lo que pasa por los tópicos |
| `colcon-common-extensions` | Compilar paquetes de ROS 2 |
| `sensor_msgs` | El tipo de mensaje con el que se le habla al brazo |
| `demo-nodes-cpp` | Un par de nodos de prueba para comprobar la conexión |
| `matplotlib` | Generar gráficas a partir de las mediciones |

Comprueba que quedaron:

```bash
ros2 --version
colcon version-check 2>/dev/null | head -3
ls /opt/ros/humble/share/rosidl_default_generators >/dev/null && echo "rosidl OK"
```

---

## Paso 4 · Configurar el entorno

Tres líneas en tu `~/.bashrc`. Reemplaza el `52` por el dominio que te dio tu profesor:

```bash
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=52'           >> ~/.bashrc
echo 'export ROS_LOCALHOST_ONLY=0'       >> ~/.bashrc
exec bash
```

Verifica:

```bash
echo "$ROS_DISTRO · dominio $ROS_DOMAIN_ID · localhost_only $ROS_LOCALHOST_ONLY"
```

Debe decir `humble · dominio 52 · localhost_only 0`.

**Qué significa cada línea**

`source /opt/ros/humble/setup.bash` carga ROS 2. Sin esto el comando `ros2` no existe.

`ROS_DOMAIN_ID` es el canal por el que se hablan los nodos. Dos máquinas en dominios
distintos no se ven **aunque estén en la misma red y se hagan ping**. Tiene que ser
exactamente el mismo número que el del Jetson.

`ROS_LOCALHOST_ONLY=0` permite que tus nodos salgan de tu máquina. Con el valor en `1`,
ROS 2 funciona pero solo habla consigo mismo, y vas a ver únicamente tus propios nodos.

---

## Paso 5 · Reiniciar el demonio de ROS 2

ROS 2 guarda en memoria la lista de lo que vio la última vez. Si cambias el dominio o las
variables sin reiniciarlo, te sigue mostrando la información vieja.

```bash
ros2 daemon stop
ros2 daemon start
```

Hazlo cada vez que cambies algo del paso 4.

---

## Paso 6 · Comprobar que ves el robot

Primero, **una persona de tu equipo** levanta el driver dentro del Jetson y deja esa
terminal abierta:

```bash
ssh jetson@$JETSON
source ~/jetcobot_colcon_ws/install/setup.bash
ros2 run jetcobot_driver sync_plan_nx
```

Solo una persona. El brazo tiene un único puerto y no se comparte: si dos lo intentan, el
segundo recibe un error.

Y ahora, desde tu Raspberry:

```bash
ros2 node list
ros2 topic list
ros2 topic info /joint_states -v
```

Lo que debe salir:

```
/control_sync_plan

/joint_states
/parameter_events
/rosout

Type: sensor_msgs/msg/JointState
Publisher count: 0
Subscription count: 1
```

Si aparece `/control_sync_plan`, tu Raspberry ya está conectada al robot.

---

## Paso 7 · Si no aparece nada

Recorre esta tabla en orden. Cada línea descarta una causa.

| # | Comprueba | Comando | Si falla |
|---|---|---|---|
| 1 | Tienes IP del laboratorio | `ip -4 addr show scope global` | Revisa cable o WiFi |
| 2 | Llegas al Jetson | `ping $JETSON` | Es la red. Avisa al profesor |
| 3 | Alguien levantó el driver | `ros2 node list` **dentro del Jetson** | Si allá también sale vacío, nadie lo levantó. No es tu Raspberry |
| 4 | Mismo dominio en las dos | `echo $ROS_DOMAIN_ID` en cada una | Iguálalos y vuelve al paso 5 |
| 5 | `ROS_LOCALHOST_ONLY` en 0 | `echo $ROS_LOCALHOST_ONLY` | Con 1 no sales de tu máquina |
| 6 | Demonio reiniciado | `ros2 daemon stop && ros2 daemon start` | La lista vieja engaña |
| 7 | Cortafuegos abierto | `sudo ufw status` | Ver abajo |

El punto 3 es el que más confunde: una lista vacía **casi nunca** es un problema de red.
Lo más común es que el driver no esté corriendo.

### Si el cortafuegos está activo

ROS 2 usa puertos UDP que dependen del dominio: `7400 + 250 × dominio`. Con el dominio
52, del 20400 en adelante.

```bash
sudo ufw allow from 172.51.0.0/16 to any proto udp port 20400:20500
```

### Si todo lo anterior está bien y sigue sin verse

Pregúntale al profesor si el laboratorio usa **Discovery Server**. En ese caso hacen falta
dos variables más y un archivo que se copia desde el Jetson:

```bash
sudo apt install -y ros-humble-rmw-fastrtps-cpp
scp jetson@$JETSON:~/super_client_configuration_file.xml ~/

export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISCOVERY_SERVER=$JETSON:11811
export FASTRTPS_DEFAULT_PROFILES_FILE=$HOME/super_client_configuration_file.xml

ros2 daemon stop; ros2 daemon start
ros2 node list
```

El archivo XML es obligatorio en esta modalidad. Sin él verás solo `/parameter_events` y
`/rosout`, que son tus propios tópicos, y ninguno del robot.

---

## Paso 8 · Instalar el material del curso

```bash
cd ~/kit_alumno
bash instalar_kit.sh
```

Compila los paquetes en `~/ros2_ws_brazo`. El paquete de interfaces tarda unos minutos:
está generando código a partir de las definiciones de servicios y acciones.

Al terminar, comprueba:

```bash
source ~/ros2_ws_brazo/install/setup.bash
ros2 pkg list | grep jetcobot
ros2 interface show jetcobot_positions_interfaces/action/RunSequence
```

---

## Paso 9 · Antes de cada sesión de trabajo

**En cada terminal nueva que abras**, dos líneas:

```bash
source ~/ros2_ws_brazo/install/setup.bash
source ~/kit_alumno/conectar.sh $JETSON
```

`conectar.sh` se ejecuta con **`source`**, no con `bash`. Si lo corres con `bash`, las
variables se pierden al terminar el script y tu terminal se queda sin configurar. Es el
error más frecuente al empezar.

---

## Dónde corre cada cosa

| Máquina | Qué corre ahí | Cuántos |
|---|---|---|
| El Jetson | El driver `sync_plan_nx` | Uno por equipo |
| El Jetson | El broker, cuando lo tengan | Uno por equipo |
| **Tu Raspberry** | Tus nodos cliente y tus comandos | Uno por integrante |

**Antes de que alguien mande la primera pose, espacio despejado alrededor del brazo.**

---

## Reglas del laboratorio

**El brazo es un recurso compartido.** Un solo programa puede abrir su puerto. Antes de
levantar algo que lo use, confirma con tu equipo que nadie más lo tiene.

**Si algo no funciona, no cambies permisos ni detengas servicios.** Los robots tienen
configuración puesta a propósito, y lo que parece un obstáculo puede ser una protección.
Levanta la mano.

**Avisa antes de mover el brazo.** En voz alta, y mira que no haya manos cerca.

---

## Resumen

```bash
# Una sola vez
sudo apt install -y ros-humble-rosidl-default-generators ros-humble-rosbag2 \
  ros-humble-sensor-msgs python3-colcon-common-extensions python3-matplotlib
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=52'           >> ~/.bashrc
echo 'export ROS_LOCALHOST_ONLY=0'       >> ~/.bashrc
echo 'export JETSON=172.51.9.5'          >> ~/.bashrc
exec bash
cd ~/kit_alumno && bash instalar_kit.sh

# En cada terminal
source ~/ros2_ws_brazo/install/setup.bash
source ~/kit_alumno/conectar.sh $JETSON
```
