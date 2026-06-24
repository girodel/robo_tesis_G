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

class MotorComparisonNode(Node):
    def __init__(self):
        super().__init__('motor_comparison_node')

        self.pub_orden_1 = self.create_publisher(Float64, 'motor/vel_orden_1', 10)
        self.pub_orden_2 = self.create_publisher(Float64, 'motor/vel_orden_2', 10)

        # Parámetros físicos del motor de 12V
        V_in = 12.0
        R = 2.0
        L = 0.005
        K = 0.05
        J = 0.0001
        B = 0.00001

        # Calcular el tiempo de estabilización (aprox 4 tau)
        self.tau = (J * R) / (B * R + K**2)
        self.tiempo_estabilizacion = 4 * self.tau

        # Funciones de transferencia
        num_1 = [K]
        den_1 = [J*R, B*R + K**2]
        sys_1 = signal.TransferFunction(num_1, den_1)

        num_2 = [K]
        den_2 = [J*L, J*R + L*B, B*R + K**2]
        sys_2 = signal.TransferFunction(num_2, den_2)

        # Simulación de un ciclo de 20 segundos
        self.dt = 0.01  # Resolución de 10 milisegundos
        self.t_sim = np.arange(0, 20.0, self.dt)
        _, self.y1 = signal.step(sys_1, T=self.t_sim)
        _, self.y2 = signal.step(sys_2, T=self.t_sim)

        self.y1 = self.y1 * V_in
        self.y2 = self.y2 * V_in

        self.index = 0
        self.max_index = len(self.t_sim)
        self.stop_requested = False

        # Iniciar el hilo que escucha el teclado en segundo plano
        self.input_thread = threading.Thread(target=self.esperar_tecla_g)
        self.input_thread.daemon = True
        self.input_thread.start()

        # Iniciar el timer para el bucle
        self.timer = self.create_timer(self.dt, self.timer_callback)
        
        self.get_logger().info('======================================================')
        self.get_logger().info(' SIMULACIÓN EN BUCLE INICIADA')
        self.get_logger().info(' --> PRESIONA LA TECLA "g" PARA DETENER Y VER GRÁFICA')
        self.get_logger().info('======================================================')

    def esperar_tecla_g(self):
        # Configuración para leer el teclado en Linux sin presionar Enter
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
        # 1. Comprobar si el usuario presionó 'g'
        if self.stop_requested:
            self.timer.cancel()
            self.get_logger().info('======================================================')
            self.get_logger().info(' Tecla "g" detectada. Deteniendo simulación...')
            # AQUÍ IMPRIMIMOS EL TIEMPO DE ESTABILIZACIÓN ANTES DE LA GRÁFICA
            self.get_logger().info(f' -> EL MOTOR SE ESTABILIZA EN: {self.tiempo_estabilizacion:.3f} segundos')
            self.get_logger().info('======================================================')
            self.mostrar_grafica()
            rclpy.shutdown()
            return

        # 2. Comprobar si llegamos al final de los 20 segundos para reiniciar el bucle
        if self.index >= self.max_index:
            self.index = 0
            self.get_logger().info('\n--- REINICIANDO CICLO DE 20 SEGUNDOS ---\n')

        # 3. Publicar e imprimir los datos
        tiempo_actual = self.t_sim[self.index]
        vel_1 = float(self.y1[self.index])
        vel_2 = float(self.y2[self.index])

        self.get_logger().info(f'Tiempo: {tiempo_actual:.2f}s | Vel 1er Orden: {vel_1:.4f} | Vel 2do Orden: {vel_2:.4f}')

        msg_1 = Float64()
        msg_1.data = vel_1
        self.pub_orden_1.publish(msg_1)

        msg_2 = Float64()
        msg_2.data = vel_2
        self.pub_orden_2.publish(msg_2)

        self.index += 1

    def mostrar_grafica(self):
        plt.figure(figsize=(10, 6))
        plt.plot(self.t_sim, self.y1, label='1er Orden (Aproximación)', color='blue', linewidth=2)
        plt.plot(self.t_sim, self.y2, label='2do Orden (Física Real)', color='red', linestyle='--', linewidth=2)
        
        plt.axvline(x=self.tiempo_estabilizacion, color='green', linestyle=':', 
                    label=f'Estabilización ({self.tiempo_estabilizacion:.3f}s)')
        
        plt.title('Respuesta al Escalón del Motor de 12V (20 Segundos)')
        plt.xlabel('Tiempo [Segundos]')
        plt.ylabel('Velocidad [rad/s]')
        plt.grid(True)
        plt.legend()
        
        plt.show()

def main(args=None):
    rclpy.init(args=args)
    node = MotorComparisonNode()
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