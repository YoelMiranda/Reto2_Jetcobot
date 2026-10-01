#!/usr/bin/env bash
# Prueba de humo: lanza 4 clientes desde ESTA máquina contra el broker.
# (En la medición real, cada integrante corre el suyo desde su propio equipo.)
#
#   bash herramientas/probar_cuatro_clientes.sh carga.csv
#
# Prioridades 1..4 (mayor = más urgente). Requiere el broker ya corriendo y
# `source ~/rb2_ws/install/setup.bash` en esta terminal.
TRAZA="${1:-carga.csv}"
[ -f "$TRAZA" ] || { echo "No encuentro $TRAZA (python3 herramientas/generar_carga.py --n 10 --salida $TRAZA)"; exit 1; }
for i in 1 2 3 4; do
  ros2 run arm_broker cliente --ros-args \
    -p client_id:=alumno$i -p priority:=$i -p traza:="$TRAZA" &
done
wait
echo "Listo: los 4 clientes terminaron."
