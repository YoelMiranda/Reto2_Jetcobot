"""arm_broker — el único nodo que publica en /joint_states.

Andamiaje entregado por el curso. Los bloques IMPLEMENTAR son lo que evalúa el
reto; el resto es instrumentación y se usa tal cual.
"""

import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState

from arm_broker_interfaces.action import MoveArm
from arm_broker_interfaces.msg import QueueState

from arm_broker import fk
from arm_broker.politicas import POLITICAS, Pedido


class ArmBroker(Node):

    def __init__(self):
        super().__init__('arm_broker')

        self.declare_parameter('politica', 'fifo')
        self.declare_parameter('tau_envejecimiento_s', 8.0)
        self.declare_parameter('cola_max', 20)
        self.declare_parameter('paso_max_rad', 1.2)
        self.declare_parameter('duracion_movimiento_s', 3.0)
        self.declare_parameter('pasos_interpolacion', 10)

        nombre = self.get_parameter('politica').value
        if nombre not in POLITICAS:
            raise RuntimeError(f'política desconocida: {nombre}. Hay {list(POLITICAS)}')
        clase = POLITICAS[nombre]
        if nombre == 'prioridad':
            self.politica = clase(self.get_parameter('tau_envejecimiento_s').value)
        else:
            self.politica = clase()

        self.cola_max = int(self.get_parameter('cola_max').value)
        self.paso_max = float(self.get_parameter('paso_max_rad').value)
        self.duracion = float(self.get_parameter('duracion_movimiento_s').value)
        self.pasos = max(1, int(self.get_parameter('pasos_interpolacion').value))

        self.grupo_entrada = ReentrantCallbackGroup()
        self.grupo_worker = MutuallyExclusiveCallbackGroup()

        self.lock = threading.Lock()
        self.pendientes = []
        self.por_goal_id = {}
        self.ejecutando = None
        self.q_actual = [0.0] * 6
        self.n_aceptados = 0
        self.n_rechazados = 0
        self.n_completados = 0
        self._parar = threading.Event()

        self.pub_joint = self.create_publisher(JointState, '/joint_states', 10)
        self.pub_cola = self.create_publisher(QueueState, '/arm/queue_state', 10)

        self.servidor = ActionServer(
            self,
            MoveArm,
            'move_arm',
            goal_callback=self.goal_callback,
            handle_accepted_callback=self.handle_accepted_callback,
            cancel_callback=self.cancel_callback,
            execute_callback=self.execute_callback,
            callback_group=self.grupo_entrada,
        )

        self.create_timer(0.2, self.publicar_estado_cola,
                          callback_group=self.grupo_worker)

        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

        self.get_logger().info(
            f'arm_broker listo · política={self.politica.nombre} · '
            f'cola_max={self.cola_max} · único publicador de /joint_states')

    # ========================= IMPLEMENTAR · ítem 2 ==========================
    def _registrar_rechazo(self, goal_request, motivo):
        """Deja constancia de un rechazo: log de ROS y una fila en rechazos.csv.

        El cliente solo recibe accepted=False (ROS 2 no permite devolver texto en la
        admisión), así que el motivo legible queda aquí. Archivo: variable de entorno
        ARM_BROKER_RECHAZOS, por defecto ./rechazos.csv.
        """
        import csv
        import os
        from datetime import datetime

        self.get_logger().warn(
            f'RECHAZADO [{goal_request.client_id}, prioridad {goal_request.priority}]: {motivo}')
        ruta = os.environ.get('ARM_BROKER_RECHAZOS', 'rechazos.csv')
        try:
            nuevo = not os.path.exists(ruta)
            with open(ruta, 'a', newline='') as f:
                w = csv.writer(f)
                if nuevo:
                    w.writerow(['hora', 'client_id', 'priority', 'motivo', 'joint_positions'])
                w.writerow([datetime.now().isoformat(timespec='milliseconds'),
                            goal_request.client_id, int(goal_request.priority), motivo,
                            ' '.join(f'{v:.4f}' for v in goal_request.joint_positions)])
        except OSError as e:
            self.get_logger().error(f'No pude escribir {ruta}: {e}')

    def goal_callback(self, goal_request):
        """Admisión. Barata e inmediata: acepta o rechaza, nunca ejecuta.

        Rechaza, con motivo explícito, si el objetivo está fuera de límites
        articulares, fuera del workspace, si el paso articular desde self.q_actual
        supera self.paso_max o si la cola está llena. La FK del ítem 1 es el portero.
        """
        q = list(goal_request.joint_positions)
        motivo = ''
        try:
            ok, motivo = fk.dentro_de_limites(q)
            if ok:
                ok, motivo = fk.dentro_del_workspace(q)
                if not ok:
                    motivo = f'fuera del workspace: {motivo}'
            else:
                motivo = f'fuera de límites articulares: {motivo}'
            if ok:
                with self.lock:
                    q_desde = list(self.q_actual)
                paso = fk.paso_articular(q_desde, q)
                if paso > self.paso_max:
                    ok = False
                    j = max(range(6), key=lambda i: abs(q[i] - q_desde[i]))
                    motivo = (f'paso articular excesivo: {paso:.2f} rad en {fk.JOINT_NAMES[j]} '
                              f'(máximo {self.paso_max:.2f} rad)')
            if ok:
                with self.lock:
                    llena = len(self.pendientes) >= self.cola_max
                if llena:
                    ok = False
                    motivo = f'cola llena ({self.cola_max} pedidos en espera)'
        except Exception as e:  # una admisión que falla no debe tumbar al broker
            ok = False
            motivo = f'error interno de admisión: {e}'

        if not ok:
            with self.lock:
                self.n_rechazados += 1
            self._registrar_rechazo(goal_request, motivo)
            return GoalResponse.REJECT

        with self.lock:
            self.n_aceptados += 1
        return GoalResponse.ACCEPT

    def handle_accepted_callback(self, goal_handle):
        """Encolar. AQUÍ NO SE EJECUTA NADA, y no se publica en /joint_states."""
        req = goal_handle.request
        pedido = Pedido(goal_handle, req.client_id, req.priority, req.joint_positions)
        with self.lock:
            self.pendientes.append(pedido)
            self.por_goal_id[pedido.goal_id] = pedido
        self.get_logger().info(
            f'ENCOLADO {pedido} · en espera: {len(self.pendientes)}')

    def _worker(self):
        """El único que decide a quién le toca. Corre en su propio hilo.

        La exclusión mutua está en pedido.fin.wait(): no se saca el siguiente pedido
        hasta que el actual terminó, así que nunca hay dos ejecutándose.
        """
        while not self._parar.is_set():
            pedido = None
            cancelados = []
            with self.lock:
                # Los que el cliente canceló mientras esperaban en la cola se descartan.
                cancelados = [p for p in self.pendientes if p.goal_handle.is_cancel_requested]
                for p in cancelados:
                    self.pendientes.remove(p)
                    self.por_goal_id.pop(p.goal_id, None)
                if self.ejecutando is None and self.pendientes:
                    i = self.politica.siguiente(self.pendientes)
                    if i is not None:
                        pedido = self.pendientes.pop(i)
                        pedido.t_inicio_ejec = time.time()
                        self.ejecutando = pedido

            for p in cancelados:
                self.get_logger().info(f'CANCELADO en cola {p}')
                try:
                    p.goal_handle.canceled()
                except Exception as e:
                    self.get_logger().warn(f'No pude cerrar el goal cancelado {p}: {e}')
                p.fin.set()

            if pedido is None:
                time.sleep(0.01)
                continue

            self.get_logger().info(f'EJECUTANDO {pedido} · esperó {pedido.espera_s:.2f} s')
            try:
                pedido.goal_handle.execute()
            except Exception as e:
                self.get_logger().error(f'execute() falló para {pedido}: {e}')
                try:
                    pedido.goal_handle.abort()
                except Exception:
                    pass
                pedido.resultado = 'aborted'
                pedido.fin.set()

            # Exclusión mutua: hasta que no termine este, no se toca el siguiente.
            while not pedido.fin.wait(0.2):
                if self._parar.is_set():
                    break

            with self.lock:
                self.ejecutando = None
                self.por_goal_id.pop(pedido.goal_id, None)
                if pedido.resultado == 'succeeded':
                    self.n_completados += 1
            self.politica.atendido(pedido)

    def execute_callback(self, goal_handle):
        """Ejecutar UN pedido. Lo llama el worker (vía execute()), nunca handle_accepted."""
        resultado = MoveArm.Result()
        pedido = self.por_goal_id.get(bytes(goal_handle.goal_id.uuid).hex()[:12])
        try:
            if pedido is None:
                goal_handle.abort()
                resultado.success = False
                resultado.message = 'goal desconocido para el broker'
                return resultado

            destino = [float(v) for v in goal_handle.request.joint_positions]
            with self.lock:
                origen = list(self.q_actual)
            espera = (pedido.t_inicio_ejec or time.time()) - pedido.t_llegada
            dt = self.duracion / self.pasos

            for k in range(1, self.pasos + 1):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    pedido.resultado = 'canceled'
                    resultado.success = False
                    resultado.message = f'cancelado en el paso {k - 1}/{self.pasos}'
                    resultado.wait_time_s = espera
                    resultado.exec_time_s = time.time() - pedido.t_inicio_ejec
                    return resultado

                self.mover([a + (b - a) * k / self.pasos for a, b in zip(origen, destino)])

                fb = MoveArm.Feedback()
                fb.state = 'EXECUTING'
                fb.queue_position = 0
                fb.elapsed_s = time.time() - pedido.t_inicio_ejec
                goal_handle.publish_feedback(fb)
                time.sleep(dt)

            goal_handle.succeed()
            pedido.resultado = 'succeeded'
            resultado.success = True
            resultado.message = 'ok'
            resultado.wait_time_s = espera
            resultado.exec_time_s = time.time() - pedido.t_inicio_ejec
            return resultado
        except Exception as e:
            self.get_logger().error(f'execute_callback falló: {e}')
            try:
                goal_handle.abort()
            except Exception:
                pass
            if pedido is not None:
                pedido.resultado = 'aborted'
            resultado.success = False
            resultado.message = f'error al ejecutar: {e}'
            return resultado
        finally:
            if pedido is not None:
                pedido.fin.set()  # sin esto el worker esperaría para siempre
    # =========================================================================

    def cancel_callback(self, goal_handle):
        return CancelResponse.ACCEPT

    # ----------------------------------------------------------- publicar
    def mover(self, q):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.name = fk.JOINT_NAMES
        msg.position = [float(v) for v in q]
        self.pub_joint.publish(msg)
        with self.lock:
            self.q_actual = list(q)

    def publicar_estado_cola(self):
        msg = QueueState()
        msg.stamp = self.get_clock().now().to_msg()
        with self.lock:
            ej = self.ejecutando
            msg.executing_client = ej.client_id if ej else ''
            msg.executing_goal_id = ej.goal_id if ej else ''
            msg.executing_elapsed_s = (time.time() - ej.t_inicio_ejec) if ej and ej.t_inicio_ejec else 0.0
            msg.queue_length = len(self.pendientes)
            msg.queued_goal_ids = [p.goal_id for p in self.pendientes]
            msg.queued_clients = [p.client_id for p in self.pendientes]
            msg.queued_priorities = [min(255, max(0, p.priority)) for p in self.pendientes]
            msg.queued_wait_s = [p.espera_s for p in self.pendientes]
            msg.total_accepted = self.n_aceptados
            msg.total_rejected = self.n_rechazados
            msg.total_completed = self.n_completados
            cola = list(self.pendientes)
        self.pub_cola.publish(msg)

        for posicion, p in enumerate(cola, start=1):
            try:
                fb = MoveArm.Feedback()
                fb.state = 'QUEUED'
                fb.queue_position = posicion
                fb.elapsed_s = p.espera_s
                p.goal_handle.publish_feedback(fb)
            except Exception:
                pass

    def destroy_node(self):
        self._parar.set()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    nodo = ArmBroker()
    executor = MultiThreadedExecutor()
    executor.add_node(nodo)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
