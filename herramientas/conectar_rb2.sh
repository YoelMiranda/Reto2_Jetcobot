# conectar_rb2.sh — deja esta terminal lista para hablar con el JetCobot del equipo.
# SE USA CON `source`, no con `bash` (si no, las variables se pierden al terminar).
#
#   source ~/conectar_rb2.sh <IP_JETSON> [DOMINIO] [--discovery]
#
#   source ~/conectar_rb2.sh 172.51.9.5                  # dominio 72 (arm-03)
#   source ~/conectar_rb2.sh 172.51.9.5 72 --discovery   # si el lab usa Discovery Server

_ip="${1:-$JETSON}"
_dom=72
_disc=0
for _a in "${@:2}"; do
  if [ "$_a" = "--discovery" ]; then _disc=1; else _dom="$_a"; fi
done

if [ -z "$_ip" ]; then
  echo "Falta la IP del Jetson:  source ~/conectar_rb2.sh <IP_JETSON> [DOMINIO] [--discovery]"
  return 1 2>/dev/null || exit 1
fi

source /opt/ros/humble/setup.bash
[ -f "$HOME/rb2_ws/install/setup.bash" ] && source "$HOME/rb2_ws/install/setup.bash"

export JETSON="$_ip"
export ROS_DOMAIN_ID="$_dom"
export ROS_LOCALHOST_ONLY=0

if [ "$_disc" = "1" ]; then
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  export ROS_DISCOVERY_SERVER="$_ip:11811"
  export FASTRTPS_DEFAULT_PROFILES_FILE="$HOME/super_client_configuration_file.xml"
  [ -f "$FASTRTPS_DEFAULT_PROFILES_FILE" ] || \
    echo "AVISO: falta $FASTRTPS_DEFAULT_PROFILES_FILE  (scp jetson@$_ip:~/super_client_configuration_file.xml ~/)"
else
  unset ROS_DISCOVERY_SERVER FASTRTPS_DEFAULT_PROFILES_FILE
fi

ros2 daemon stop  >/dev/null 2>&1
ros2 daemon start >/dev/null 2>&1

echo "ROS_DISTRO=$ROS_DISTRO · dominio=$ROS_DOMAIN_ID · localhost_only=$ROS_LOCALHOST_ONLY · JETSON=$JETSON"
if ping -c 1 -W 2 "$JETSON" >/dev/null 2>&1; then echo "ping al Jetson: OK"; else echo "ping al Jetson: FALLA (es la red, no ROS)"; fi
[ "$_disc" = "1" ] && echo "modo Discovery Server: $ROS_DISCOVERY_SERVER"
echo "nodos visibles:"; ros2 node list
unset _ip _dom _disc _a
