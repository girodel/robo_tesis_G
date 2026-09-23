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

class MotorRS775Node(Node):
    def __init__(self):
        super().__init__('motor_rs775_node')

        # Tópicos de publicación en ROS 2
        self.pub_sin_pid = self.create_publisher(Float64, 'motor/vel_sin_pid', 10)
        self.pub_con_pid = self.create_publisher(Float64, 'motor/vel_con_pid', 10)

        # ---------------------------------------------------------
        # PARÁMETROS FÍSICOS REALES DEL MOTOR RS-775 (PG45)
        # ---------------------------------------------------------
        V_in = 12.0       # Voltaje nominal [V]
        R = 1.00          # Resistencia de Armadura [Ohms]
        L = 0.00065       # Inductancia de Armadura [H] (0.65 mH)
        K = 0.022         # Constante de Torque y FEM [N*m/A]
        J = 1.25e-5       # Inercia del rotor [kg*m^2]
        B = 1.80e-5       # Coeficiente de Fricción Viscosa [N*m*s/rad]

        # ---------------------------------------------------------
        # PARÁMETROS PID DE ZIEGLER-NICHOLS (GANANCIA ÚLTIMA)
        # ---------------------------------------------------------
        Kp = 0.4398
        Ki = 150.5223
        Kd = 0.000321

        # 1. MODELO SIN PID (Lazo Abierto - Segundo Orden)
        num_2 = [K]
        den_2 = [J*L, J*R + L*B, B*R + K**2]
        sys_open_loop = signal.TransferFunction(num_2, den_2)

        # 2. MODELO CON PID (Lazo Cerrado)
        num_c = [Kd, Kp, Ki]
        den_c = [1, 0]

        num_L2 = np.convolve(num_c, num_2)
        den_L2 = np.convolve(den_c, den_2)
        num_T2 = num_L2
        den_T2 = np.polyadd(den_L2, num_L2)
        sys_closed_loop = signal.TransferFunction(num_T2, den_T2)

        # ---------------------------------------------------------
        # SIMULACIÓN (50 Milisegundos)
        # ---------------------------------------------------------
        self.dt = 0.00005                         # Paso de integración de 0.05 ms
        self.t_sim = np.arange(0, 0.05, self.dt)  # 50 ms de tiempo base
        
        # Respuesta al escalón
        _, self.y_sin_pid = signal.step(sys_open_loop, T=self.t_sim)
        _, self.y_con_pid = signal.step(sys_closed_loop, T=self.t_sim)

        # Escalar señales
        self.y_sin_pid = self.y_sin_pid * V_in     # Entrada de 12V
        self.setpoint = 3.351                       # 32 RPM ≈ 3.351 rad/s (Salida del reductor PG45)
        self.y_con_pid = self.y_con_pid * self.setpoint

        # ---------------------------------------------------------
        # CÁLCULO DEL TIEMPO DE ESTABILIZACIÓN / ASENTAMIENTO (Criterio del 2%)
        # ---------------------------------------------------------
        val_final_sin = self.y_sin_pid[-1]
        self.ts_sin_pid = self.calcular_tiempo_estabilizacion(self.t_sim, self.y_sin_pid, val_final_sin, tol=0.02)
        self.ts_con_pid = self.calcular_tiempo_estabilizacion(self.t_sim, self.y_con_pid, self.setpoint, tol=0.02)

        self.index = 0
        self.max_index = len(self.t_sim)
        self.stop_requested = False
        
        # INICIAR PAUSADO: Espera la tecla 'h' para arrancar el PID
        self.is_running = False  

        # Hilo para capturar teclas 'h' y 'g'
        self.input_thread = threading.Thread(target=self.esperar_teclas)
        self.input_thread.daemon = True
        self.input_thread.start()

        self.timer = self.create_timer(0.01, self.timer_callback)
        
        self.get_logger().info('======================================================')
        self.get_logger().info(' SIMULACIÓN MOTOR RS-775 (PG45) EN ROS 2')
        self.get_logger().info(f' --> t_estabilización SIN PID: {(self.ts_sin_pid * 1000):.2f} ms' if self.ts_sin_pid else ' --> SIN PID: No se estabilizó')
        self.get_logger().info(f' --> t_estabilización CON PID: {(self.ts_con_pid * 1000):.2f} ms' if self.ts_con_pid else ' --> CON PID: No se estabilizó')
        self.get_logger().info('------------------------------------------------------')
        self.get_logger().info(' [PAUSADO] PRESIONA "h" PARA INICIAR/REANUDAR EL CONTROL PID')
        self.get_logger().info(' [PAUSADO] PRESIONA "g" PARA DETENER Y GENERAR GRÁFICA')
        self.get_logger().info('======================================================')

    def calcular_tiempo_estabilizacion(self, t, y, val_final, tol=0.02):
        fuera_banda = np.where(np.abs(y - val_final) > (tol * val_final))[0]
        if len(fuera_banda) == 0:
            return t[0]
        idx = fuera_banda[-1] + 1
        if idx < len(t):
            return t[idx]
        return None

    def esperar_teclas(self):
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            while rclpy.ok():
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    tecla = sys.stdin.read(1).lower()
                    if tecla == 'h':
                        self.is_running = not self.is_running
                        if self.is_running:
                            self.get_logger().info('>>> [INICIADO] CONTROL PID Y PUBLICACIÓN DE TÓPICOS EN CURSO...')
                        else:
                            self.get_logger().info('>>> [PAUSADO] SIMULACIÓN EN PAUSA. PRESIONA "h" PARA CONTINUAR.')
                    elif tecla == 'g':
                        self.stop_requested = True
                        break
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def timer_callback(self):
        if self.stop_requested:
            self.timer.cancel()
            self.get_logger().info('======================================================')
            self.get_logger().info(' Generando gráfica con Tiempos de Estabilización...')
            self.get_logger().info('======================================================')
            self.mostrar_grafica()
            rclpy.shutdown()
            return

        if not self.is_running:
            return  # No hace nada mientras no presiones 'h'

        if self.index >= self.max_index:
            self.index = 0  # Bucle continuo de transmisión

        tiempo_actual_ms = self.t_sim[self.index] * 1000.0
        vel_sin_pid = float(self.y_sin_pid[self.index])
        vel_con_pid = float(self.y_con_pid[self.index])

        self.get_logger().info(
            f'Tiempo: {tiempo_actual_ms:.2f} ms | '
            f'Sin PID: {vel_sin_pid:.2f} rad/s | '
            f'Con PID: {vel_con_pid:.2f} rad/s'
        )

        msg_sin = Float64()
        msg_sin.data = vel_sin_pid
        self.pub_sin_pid.publish(msg_sin)

        msg_con = Float64()
        msg_con.data = vel_con_pid
        self.pub_con_pid.publish(msg_con)

        self.index += 1

    def mostrar_grafica(self):
        plt.figure(figsize=(11, 6))
        t_ms = self.t_sim * 1000.0

        plt.axhline(y=self.setpoint, color='green', linestyle=':', linewidth=2, 
                    label=f'Objetivo ({self.setpoint:.3f} rad/s ≈ 32 RPM)')
        
        plt.plot(t_ms, self.y_sin_pid, label='Sin PID (12V Directos)', color='orange', linewidth=2)
        plt.plot(t_ms, self.y_con_pid, label='Con PID Z-N (Kp=0.4398, Ki=150.52, Kd=0.000321)', color='blue', linewidth=2)
        
        if self.ts_con_pid is not None:
            ts_con_ms = self.ts_con_pid * 1000.0
            plt.axvline(x=ts_con_ms, color='blue', linestyle='--', alpha=0.7,
                        label=f'ts Con PID: {ts_con_ms:.2f} ms')
            plt.plot(ts_con_ms, self.setpoint, 'bo', markersize=8)

        if self.ts_sin_pid is not None:
            ts_sin_ms = self.ts_sin_pid * 1000.0
            plt.axvline(x=ts_sin_ms, color='orange', linestyle='--', alpha=0.7,
                        label=f'ts Sin PID: {ts_sin_ms:.2f} ms')
            plt.plot(ts_sin_ms, self.y_sin_pid[-1], 'ro', markersize=8)

        plt.title('Comparación de Tiempo de Estabilización ($t_s$ 2%) - Motor RS-775 (PG45)')
        plt.xlabel('Tiempo [Milisegundos]')
        plt.ylabel('Velocidad Angular [rad/s]')
        plt.grid(True)
        plt.legend(loc='lower right')
        plt.show()

def main(args=None):
    rclpy.init(args=args)
    node = MotorRS775Node()
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