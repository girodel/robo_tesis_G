#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class CinematicaDirectaTanque(Node):
    def __init__(self):
        super().__init__('cinematica_directa_tanque')
        
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10)
        
        # --- PARÁMETROS FÍSICOS ---
        self.R = 0.05  # Radio (5 cm)
        self.L = 0.20  # Distancia entre llantas (20 cm)
        
        # Nombres de los joints (Asegúrate que coincidan con tu URDF)
        self.joint_iz_del = 'llanta_iz_del_joint'
        self.joint_iz_tra = 'llanta_iz_tra_joint'
        self.joint_der_del = 'llanta_dere_del_joint'
        self.joint_der_tra = 'llanta_dere_tra_joint'
        
        self.get_logger().info('Cinemática Iniciada. Esperando velocidades de Gazebo...')

    def listener_callback(self, msg):
        try:
            # Buscar índices
            idx_iz_del = msg.name.index(self.joint_iz_del)
            idx_iz_tra = msg.name.index(self.joint_iz_tra)
            idx_der_del = msg.name.index(self.joint_der_del)
            idx_der_tra = msg.name.index(self.joint_der_tra)
            
            # 🔥 PROTECCIÓN CONTRA EL ERROR (IndexError) 🔥
            if not msg.velocity:
                return # Si la lista está vacía, ignoramos el ciclo y no hacemos matemáticas
                
            # Extraer velocidades
            w_iz_del = msg.velocity[idx_iz_del]
            w_iz_tra = msg.velocity[idx_iz_tra]
            w_der_del = msg.velocity[idx_der_del]
            w_der_tra = msg.velocity[idx_der_tra]
            
            # 1. Convertir a lineal (v = w * R)
            v_iz_del = w_iz_del * self.R
            v_iz_tra = w_iz_tra * self.R
            v_der_del = w_der_del * self.R
            v_der_tra = w_der_tra * self.R
            
            # 2. Promediar lados
            v_izq = (v_iz_del + v_iz_tra) / 2.0
            v_der = (v_der_del + v_der_tra) / 2.0
            
            # 3. Cinemática Directa Final
            v = (v_der + v_izq) / 2.0
            omega = (v_der - v_izq) / self.L
            
            self.get_logger().info(f'Movimiento -> Lineal: {v:.3f} m/s | Rotación: {omega:.3f} rad/s')
            
        except ValueError:
            self.get_logger().warn('Faltan llantas en /joint_states. Revisa tu URDF.', once=True)

def main(args=None):
    rclpy.init(args=args)
    nodo = CinematicaDirectaTanque()
    rclpy.spin(nodo)
    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()