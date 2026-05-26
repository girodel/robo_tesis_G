#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time

class GraficadorMovimiento(Node):
    def __init__(self):
        super().__init__('graficador_movimiento')
        
        # Suscripciones a los tópicos de velocidad
        self.sub_cmd = self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, 10)
        self.sub_odom = self.create_subscription(Odometry, '/model/tetrabot/odometry', self.odom_callback, 10)
        
        self.t_start = time.time()
        
        # Listas para guardar los datos de la gráfica
        self.t_cmd, self.v_cmd = [], []
        self.t_odom, self.v_odom = [], []
        
        self.get_logger().info('Graficador iniciado. Abre RViz y manda al robot a moverse...')

    def cmd_callback(self, msg):
        self.t_cmd.append(time.time() - self.t_start)
        self.v_cmd.append(msg.linear.x)
        # Mantener solo los últimos 150 datos en pantalla
        if len(self.t_cmd) > 150:
            self.t_cmd.pop(0)
            self.v_cmd.pop(0)

    def odom_callback(self, msg):
        self.t_odom.append(time.time() - self.t_start)
        self.v_odom.append(msg.twist.twist.linear.x)
        if len(self.t_odom) > 150:
            self.t_odom.pop(0)
            self.v_odom.pop(0)

def main(args=None):
    rclpy.init(args=args)
    nodo = GraficadorMovimiento()

    # Configuración visual de la gráfica
    fig, ax = plt.subplots(figsize=(8, 5))
    linea_cmd, = ax.plot([], [], 'r--', label='Comando Nav2 (/cmd_vel)', linewidth=2)
    linea_odom, = ax.plot([], [], 'b-', label='Velocidad Real (/odom)', linewidth=2)
    
    ax.set_title('Transmisión de Movimiento: Aceleración y Suavizado', fontsize=14)
    ax.set_xlabel('Tiempo (segundos)')
    ax.set_ylabel('Velocidad Lineal X (m/s)')
    ax.set_ylim(-0.35, 0.35) # Ajustado al máximo de tu YAML (0.26)
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(loc='upper right')

    # Función que actualiza la gráfica constantemente
    def actualizar_grafica(frame):
        rclpy.spin_once(nodo, timeout_sec=0) # Escucha a ROS 2
        
        linea_cmd.set_data(nodo.t_cmd, nodo.v_cmd)
        linea_odom.set_data(nodo.t_odom, nodo.v_odom)
        
        # Mover el eje X para que la gráfica avance como un monitor cardíaco
        tiempo_actual = time.time() - nodo.t_start
        if tiempo_actual > 10:
            ax.set_xlim(tiempo_actual - 10, tiempo_actual)
        else:
            ax.set_xlim(0, 10)
            
        return linea_cmd, linea_odom

    # Iniciar la animación a 20 FPS (50ms)
    ani = FuncAnimation(fig, actualizar_grafica, interval=50, cache_frame_data=False)
    
    plt.tight_layout()
    plt.show() # Esta línea abre la ventana

    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()