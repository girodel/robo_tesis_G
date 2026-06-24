#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import threading
import sys
import select
import termios
import tty

class Motor2ndOrderNode(Node):
    def __init__(self):
        super().__init__('motor_2nd_order_node')

        # Tópicos actualizados para reflejar la comparación
        self.pub_sin_pid = self.create_publisher(Float64, 'motor/vel_sin_pid', 10)
        self.pub_con_pid = self.create_publisher(Float64, 'motor/vel_con_pid', 10)

        # Parámetros físicos del motor
        V_in = 12.0
        R = 2.0
        L = 0.005
        K = 0.05
        J = 0.0001
        B = 0.00001

        # Parámetros del Controlador PI (De MATLAB)
        Kp = 0.1676
        Ki = 4.5995

        # ---------------------------------------------------------
        # 1. MODELO SIN PID (Lazo Abierto / Open Loop)
        # ---------------------------------------------------------
        # G2(s) = K / (J*L s^2 + (J*R + L*B) s + (B*R + K^2))
        num_2 = [K]
        den_2 = [J*L, J*R + L*B, B*R + K**2]
        sys_open_loop = signal.TransferFunction(num_2, den_2)

        # ---------------------------------------------------------
        # 2. MODELO CON PID (Lazo Cerrado / Closed Loop)
        # ---------------------------------------------------------
        # C(s) = (Kp*s + Ki) / s
        num_c = [Kp, Ki]
        den_c = [1, 0]

        # T(s) = (C * G2) / (1 + C * G2)
        num_L2 = np.convolve(num_c, num_2)
        den_L2 = np.convolve(den_c, den_2)
        num_T2 = num_L2
        den_T2 = np.polyadd(den_L2, num_L2)
        sys_closed_loop = signal.TransferFunction(num_T2, den_T2)

        # ---------------------------------------------------------
        # SIMULACIÓN (20 Segundos)
        # ---------------------------------------------------------
        self.dt = 0.01
        self.t_sim = np.arange(0, 20.0, self.dt)
        
        # Respuesta al escalón
        _, self.y_sin_pid = signal.step(sys_open_loop, T=self.t_sim)
        _, self.y_con_pid = signal.step(sys_closed_loop, T=self.t_sim)

        # Escalamos las señales de entrada correspondientes
        self.y_sin_pid = self.y_sin_pid * V_in       # Le inyectamos 12V directos
        
        self.setpoint = 100.0                        # Le pedimos exactamente 100 rad/s
        self.y_con_pid = self.y_con_pid * self.setpoint

        self.index = 0
        self.max_index = len(self.t_sim)
        self.stop_requested = False

        # Hilo para detener con la tecla 'g'
        self.input_thread = threading.Thread(target=self.esperar_tecla_g)
        self.input_thread.daemon = True
        self.input_thread.start()

        self.timer = self.create_timer(self.dt, self.timer_callback)
        
        self.get_logger().info('======================================================')
        self.get_logger().info(' SIMULACIÓN DE 2DO ORDEN INICIADA (CON VS SIN PID)')
        self.get_logger().info(' --> PRESIONA "g" PARA DETENER Y VER GRÁFICA')
        self.get_logger().info('======================================================')

    def esperar_tecla_g(self):
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            while rclpy.ok():
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    tecla = sys.stdin.read(1)
                    if tecla.lower() == 'g':
                        self.stop_requested = True
                        break
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def timer_callback(self):
        if self.stop_requested:
            self.timer.cancel()
            self.get_logger().info('======================================================')
            self.get_logger().info(' Tecla "g" detectada. Generando gráfica final...')
            self.get_logger().info('======================================================')
            self.mostrar_grafica()
            rclpy.shutdown()
            return

        if self.index >= self.max_index:
            self.index = 0
            self.get_logger().info('\n--- REINICIANDO CICLO DE 20 SEGUNDOS ---\n')

        tiempo_actual = self.t_sim[self.index]
        vel_sin_pid = float(self.y_sin_pid[self.index])
        vel_con_pid = float(self.y_con_pid[self.index])

        self.get_logger().info(f'Tiempo: {tiempo_actual:.2f}s | Sin PID (12V): {vel_sin_pid:.2f} | Con PID (100 rad/s): {vel_con_pid:.2f}')

        msg_sin = Float64()
        msg_sin.data = vel_sin_pid
        self.pub_sin_pid.publish(msg_sin)

        msg_con = Float64()
        msg_con.data = vel_con_pid
        self.pub_con_pid.publish(msg_con)

        self.index += 1

    def mostrar_grafica(self):
        plt.figure(figsize=(10, 6))
        
        # Línea de la velocidad objetivo para el PID
        plt.axhline(y=self.setpoint, color='green', linestyle=':', linewidth=2, 
                    label=f'Objetivo del PID ({self.setpoint} rad/s)')
        
        # Gráficas
        plt.plot(self.t_sim, self.y_sin_pid, label='Sin PID (12V Directos)', color='orange', linewidth=2)
        plt.plot(self.t_sim, self.y_con_pid, label='Con PID (Kp=0.1676, Ki=4.5995)', color='blue', linewidth=2)
        
        plt.title('Comparación Motor 2do Orden: Lazo Abierto vs Controlador PID')
        plt.xlabel('Tiempo [Segundos]')
        plt.ylabel('Velocidad [rad/s]')
        plt.grid(True)
        plt.legend()
        
        plt.show()

def main(args=None):
    rclpy.init(args=args)
    node = Motor2ndOrderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()