#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time

class GraficadorVelocidad(Node):
    def __init__(self):
        super().__init__('graficador_velocidad_motores')
        
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10)
        
        self.t_start = time.time()
        
        # Listas para guardar el tiempo y la VELOCIDAD de las 4 llantas
        self.t_data = []
        self.vel_iz_del = []
        self.vel_iz_tra = []
        self.vel_der_del = []
        self.vel_der_tra = []
        
        # Nombres de los joints
        self.joint_iz_del = 'llanta_iz_del_joint'
        self.joint_iz_tra = 'llanta_iz_tra_joint'
        self.joint_der_del = 'llanta_dere_del_joint'
        self.joint_der_tra = 'llanta_dere_tra_joint'
        
        self.get_logger().info('Iniciando gráfica de velocidad de motores...')

    def listener_callback(self, msg):
        try:
            idx_iz_del = msg.name.index(self.joint_iz_del)
            idx_iz_tra = msg.name.index(self.joint_iz_tra)
            idx_der_del = msg.name.index(self.joint_der_del)
            idx_der_tra = msg.name.index(self.joint_der_tra)
            
            # Cambiamos "effort" por "velocity"
            if not msg.velocity:
                return 
                
            self.t_data.append(time.time() - self.t_start)
            
            self.vel_iz_del.append(msg.velocity[idx_iz_del])
            self.vel_iz_tra.append(msg.velocity[idx_iz_tra])
            self.vel_der_del.append(msg.velocity[idx_der_del])
            self.vel_der_tra.append(msg.velocity[idx_der_tra])
            
            if len(self.t_data) > 150:
                self.t_data.pop(0)
                self.vel_iz_del.pop(0)
                self.vel_iz_tra.pop(0)
                self.vel_der_del.pop(0)
                self.vel_der_tra.pop(0)
                
        except ValueError:
            pass # Ignoramos errores de nombre para no saturar la terminal

def main(args=None):
    rclpy.init(args=args)
    nodo = GraficadorVelocidad()

    fig, ax = plt.subplots(figsize=(10, 6))
    
    linea_iz_del, = ax.plot([], [], color='blue', label='Izquierda Delantera', linewidth=2)
    linea_iz_tra, = ax.plot([], [], color='cyan', label='Izquierda Trasera', linewidth=2, linestyle='--')
    linea_der_del, = ax.plot([], [], color='red', label='Derecha Delantera', linewidth=2)
    linea_der_tra, = ax.plot([], [], color='orange', label='Derecha Trasera', linewidth=2, linestyle='--')
    
    ax.set_title('Velocidad Angular de los Motores', fontsize=14)
    ax.set_xlabel('Tiempo (segundos)')
    ax.set_ylabel('Velocidad (rad/s)')
    ax.grid(True, linestyle=':', alpha=0.7)
    ax.legend(loc='upper right')

    def actualizar_grafica(frame):
        rclpy.spin_once(nodo, timeout_sec=0)
        
        if not nodo.t_data:
            return linea_iz_del, linea_iz_tra, linea_der_del, linea_der_tra
            
        linea_iz_del.set_data(nodo.t_data, nodo.vel_iz_del)
        linea_iz_tra.set_data(nodo.t_data, nodo.vel_iz_tra)
        linea_der_del.set_data(nodo.t_data, nodo.vel_der_del)
        linea_der_tra.set_data(nodo.t_data, nodo.vel_der_tra)
        
        t_actual = time.time() - nodo.t_start
        ax.set_xlim(max(0, t_actual - 10), max(10, t_actual))
        
        ax.relim()
        ax.autoscale_view(scalex=False, scaley=True)
            
        return linea_iz_del, linea_iz_tra, linea_der_del, linea_der_tra

    ani = FuncAnimation(fig, actualizar_grafica, interval=50, cache_frame_data=False)
    
    plt.tight_layout()
    plt.show()

    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()