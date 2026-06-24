#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

class Motor2ndOrderNode(Node):
    def __init__(self):
        super().__init__('motor_2nd_order_node')

        self.pub_sin_pid = self.create_publisher(Float64, 'motor/vel_sin_pid', 10)
        self.pub_con_pid = self.create_publisher(Float64, 'motor/vel_con_pid', 10)

        V_in = 12.0
        R = 2.0
        L = 0.005
        K = 0.05
        J = 0.0001
        B = 0.00001

        Kp = 0.1676
        Ki = 4.5995

        num_2 = [K]
        den_2 = [J*L, J*R + L*B, B*R + K**2]
        sys_open_loop = signal.TransferFunction(num_2, den_2)

        num_c = [Kp, Ki]
        den_c = [1, 0]
        num_L2 = np.convolve(num_c, num_2)
        den_L2 = np.convolve(den_c, den_2)
        num_T2 = num_L2
        den_T2 = np.polyadd(den_L2, num_L2)
        sys_closed_loop = signal.TransferFunction(num_T2, den_T2)

        self.dt = 0.01
        self.t_sim = np.arange(0, 20.0, self.dt)
        
        _, self.y_sin_pid = signal.step(sys_open_loop, T=self.t_sim)
        _, self.y_con_pid = signal.step(sys_closed_loop, T=self.t_sim)

        self.y_sin_pid = self.y_sin_pid * V_in       
        self.setpoint = 100.0                        
        self.y_con_pid = self.y_con_pid * self.setpoint

        self.index = 0
        self.max_index = len(self.t_sim)

        self.timer = self.create_timer(self.dt, self.timer_callback)
        self.get_logger().info('Nodo iniciado por la Web. Esperando señal de Parar...')

    def timer_callback(self):
        if self.index >= self.max_index:
            self.timer.cancel()
            self.get_logger().info('Límite de 20s alcanzado.')
            self.guardar_grafica()
            rclpy.shutdown()
            return

        vel_sin_pid = float(self.y_sin_pid[self.index])
        vel_con_pid = float(self.y_con_pid[self.index])

        msg_sin = Float64()
        msg_sin.data = vel_sin_pid
        self.pub_sin_pid.publish(msg_sin)

        msg_con = Float64()
        msg_con.data = vel_con_pid
        self.pub_con_pid.publish(msg_con)

        self.index += 1

    def guardar_grafica(self):
        # Recortar los datos al instante en el que se presionó el botón "Parar"
        t_plot = self.t_sim[:self.index]
        y_sin_plot = self.y_sin_pid[:self.index]
        y_con_plot = self.y_con_pid[:self.index]

        plt.figure(figsize=(10, 6))
        plt.axhline(y=self.setpoint, color='green', linestyle=':', linewidth=2, label=f'Objetivo ({self.setpoint} rad/s)')
        plt.plot(t_plot, y_sin_plot, label='Sin PID', color='orange', linewidth=2)
        plt.plot(t_plot, y_con_plot, label='Con PID', color='blue', linewidth=2)
        
        plt.title('Comparación Motor 2do Orden')
        plt.xlabel('Tiempo [s]')
        plt.ylabel('Velocidad [rad/s]')
        plt.grid(True)
        plt.legend()
        
        # Guarda en la memoria temporal de Linux
        plt.savefig('/tmp/grafica_motor.png', bbox_inches='tight')
        plt.close()

def main(args=None):
    rclpy.init(args=args)
    node = Motor2ndOrderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Se activa cuando presionas el botón "PARAR" en tu celular
        node.get_logger().info('Señal de detención recibida. Dibujando gráfica...')
        node.guardar_grafica()
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()