#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from ros_gz_interfaces.msg import Light

class FaroBlinker(Node):
    def __init__(self):
        super().__init__('faro_blinker')
        
        # El publicador hacia el tópico del puente
        self.publisher_ = self.create_publisher(Light, '/world/area_emergencia/light_config', 10)
        
        # EL CAMBIO ESTÁ AQUÍ: Cambiamos 1.0 a 3.0 segundos
        self.timer = self.create_timer(3.0, self.timer_callback)
        self.luz_encendida = True
        
        self.get_logger().info('Iniciando ciclo del faro: 3 seg. encendido / 3 seg. apagado...')

    def timer_callback(self):
        msg = Light()
        # El nombre interno que Gazebo le da a tu luz (asegúrate de que sea el correcto)
        msg.name = "tetrabot::faro_trasero_link::faro_trasero_luz"
        msg.type = 2 # 2 significa luz tipo SPOT
        
        if self.luz_encendida:
            msg.range = 0.0 # Apagado
        else:
            msg.range = 10.0 # Prendido (distancia de la luz)
            
        self.publisher_.publish(msg)
        
        # Invierte el estado para la próxima vez que pasen 3 segundos
        self.luz_encendida = not self.luz_encendida 

def main(args=None):
    rclpy.init(args=args)
    node = FaroBlinker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()