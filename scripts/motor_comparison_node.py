#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import numpy as np
from scipy import signal

class MotorComparisonNode(Node):
    def __init__(self):
        super().__init__('motor_comparison_node')

        # Creamos dos tópicos para publicar las velocidades
        self.pub_orden_1 = self.create_publisher(Float64, 'motor/vel_orden_1', 10)
        self.pub_orden_2 = self.create_publisher(Float64, 'motor/vel_orden_2', 10)

        # Parámetros físicos del motor de 12V
        V_in = 12.0
        R = 2.0
        L = 0.005
        K = 0.05
        J = 0.0001
        B = 0.00001

        # Funciones de transferencia
        # 1er Orden (Aproximación para control)
        num_1 = [K]
        den_1 = [J*R, B*R + K**2]
        sys_1 = signal.TransferFunction(num_1, den_1)

        # 2do Orden (Física real completa)
        num_2 = [K]
        den_2 = [J*L, J*R + L*B, B*R + K**2]
        sys_2 = signal.TransferFunction(num_2, den_2)

        # MODIFICACIÓN 1: Duración de 20 segundos
        self.dt = 0.01  # Resolución de 10 milisegundos (100 Hz)
        t_sim = np.arange(0, 20.0, self.dt)
        _, self.y1 = signal.step(sys_1, T=t_sim)
        _, self.y2 = signal.step(sys_2, T=t_sim)

        # Multiplicar por el voltaje de entrada (12V)
        self.y1 = self.y1 * V_in
        self.y2 = self.y2 * V_in

        self.index = 0
        self.max_index = len(t_sim)

        # Timer para publicar los datos en tiempo real
        self.timer = self.create_timer(self.dt, self.timer_callback)
        self.get_logger().info('Publicando simulación... Abre rqt_plot para ver las gráficas.')

    def timer_callback(self):
        if self.index < self.max_index:
            # Publicar velocidad de 1er orden
            msg_1 = Float64()
            msg_1.data = float(self.y1[self.index])
            self.pub_orden_1.publish(msg_1)

            # Publicar velocidad de 2do orden
            msg_2 = Float64()
            msg_2.data = float(self.y2[self.index])
            self.pub_orden_2.publish(msg_2)

            self.index += 1
        else:
            # MODIFICACIÓN 2: Reiniciar el índice a 0 para crear el bucle infinito
            self.index = 0
            self.get_logger().info('Reiniciando el ciclo de 20 segundos...')

def main(args=None):
    rclpy.init(args=args)
    node = MotorComparisonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()