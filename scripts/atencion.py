#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import os
import time
import sys

def speak(text):
    print(f"🤖 Robot dice en PC: {text}")
    os.system(f'espeak -v es "{text}"')

def print_happy_robot():
    robot_ascii = """
       +-----------------+
       |   ^         ^   |
       |   O         O   |
       |        -        |
       |                 |
       |    \\_______/    |
       +-----------------+
             __| |__
            /       \\
           /  [BAT]  \\
          /___________\\
           | |     | |
          _|_|_   _|_|_
    """
    print("\n" + "="*30)
    print("🌟 ¡MISIÓN COMPLETADA! 🌟")
    print(robot_ascii)
    print("="*30 + "\n")

def wait_for_web_signal(nav):
    print("\n⏸️  Modo Recorrido: Esperando confirmación desde el celular para ir a la siguiente sala...")
    flag_file = '/tmp/robot_continue'
    cancel_file = '/tmp/robot_cancel'
    
    if os.path.exists(flag_file):
        os.remove(flag_file)

    while True:
        if os.path.exists(cancel_file):
            print("🛑 Cancelación recibida mientras se esperaba. Abortando.")
            os.remove(cancel_file)
            sys.exit(0)
            
        if os.path.exists(flag_file):
            print("✅ ¡Orden web recibida! Avanzando...\n")
            os.remove(flag_file)
            break
        time.sleep(0.5)

def main():
    destino_archivo = '/tmp/robot_destino'
    cancel_file = '/tmp/robot_cancel'
    
    if os.path.exists(cancel_file):
        os.remove(cancel_file)
        
    if not os.path.exists(destino_archivo):
        print("❌ Error: No se especificó un destino. Usa la web.")
        sys.exit(1)
        
    with open(destino_archivo, 'r') as f:
        modo_solicitado = f.read().strip()

    mapa_salas = {
        'farmacia': {
            'name': 'Farmacia',
            'frame_id': 'map',
            'x': 6.936511039733887, 'y': -4.785110950469971,
            'qz': 0.08544607345748186, 'qw': 0.9963427966973508
        },
        'atencion1': {
            'name': 'Sala de Espera 1',
            'frame_id': 'map',
            'x': -5.879590034484863, 'y': 3.370567560195923,
            'qz': -0.6970520339350216, 'qw': 0.7170205450243735
        },
        'almacen_farmacia': {
            'name': 'Almacén de Farmacia',
            'frame_id': 'map',
            'x': -4.633490562438965, 'y': -5.18907356262207,
            'qz': -0.6419011817479123, 'qw': 0.7667873713557323
        },
        'atencion2': {
            'name': 'Sala de Espera 2',
            'frame_id': 'map',
            'x': -0.020469188690185547, 'y': 3.505204200744629,
            'qz': -0.7012816223451832, 'qw': 0.7128843427659973
        },
        'atencion3': {
            'name': 'Sala de Espera 3',
            'frame_id': 'map',
            'x': 5.70540714263916, 'y': 3.480185031890869,
            'qz': -0.6910061971163519, 'qw': 0.7228488331226643
        }
    }

    lugares_a_visitar = []
    if modo_solicitado == 'farmacia':
        lugares_a_visitar.append(mapa_salas['farmacia'])
    elif modo_solicitado == 'atencion1':
        lugares_a_visitar.append(mapa_salas['atencion1'])
    elif modo_solicitado == 'almacen_farmacia':
        lugares_a_visitar.append(mapa_salas['almacen_farmacia'])
    elif modo_solicitado == 'atencion2':
        lugares_a_visitar.append(mapa_salas['atencion2'])
    elif modo_solicitado == 'atencion3':
        lugares_a_visitar.append(mapa_salas['atencion3'])
    elif modo_solicitado == 'recorrido':
        lugares_a_visitar.append(mapa_salas['farmacia'])
        lugares_a_visitar.append(mapa_salas['atencion1'])
        lugares_a_visitar.append(mapa_salas['almacen_farmacia'])
        lugares_a_visitar.append(mapa_salas['atencion2'])
        lugares_a_visitar.append(mapa_salas['atencion3'])
    else:
        print(f"❌ Error: Modo '{modo_solicitado}' no reconocido.")
        sys.exit(1)

    rclpy.init()
    nav = BasicNavigator()
    nav.waitUntilNav2Active()

    for i, habitacion in enumerate(lugares_a_visitar):
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = habitacion['frame_id']
        goal_pose.header.stamp = nav.get_clock().now().to_msg()
        
        goal_pose.pose.position.x = habitacion['x']
        goal_pose.pose.position.y = habitacion['y']
        goal_pose.pose.position.z = 0.0
        
        goal_pose.pose.orientation.x = 0.0
        goal_pose.pose.orientation.y = 0.0
        goal_pose.pose.orientation.z = habitacion['qz']
        goal_pose.pose.orientation.w = habitacion['qw']

        print(f"🚀 Iniciando navegación hacia: {habitacion['name']}")
        
        nav.goToPose(goal_pose)

        while not nav.isTaskComplete():
            if os.path.exists(cancel_file):
                print("\n🛑 Frenando motores...")
                nav.cancelTask() 
                os.remove(cancel_file)
                sys.exit(0)
            time.sleep(0.5)

        result = nav.getResult()
        if result == TaskResult.SUCCEEDED:
            print("\n" + "="*60)
            print(f"✅ LLEGADA CONFIRMADA: {habitacion['name']}")
            print("="*60 + "\n")
            
            # Escribir el mensaje para que Flask lo mande al celular
            texto_llegada = f"Misión cumplida. He llegado a {habitacion['name']}"
            with open('/tmp/robot_llegada', 'w') as f:
                f.write(texto_llegada)
                
            speak(texto_llegada) # Sigue hablando en la PC si instalaste espeak
            
            if modo_solicitado == 'recorrido' and i < (len(lugares_a_visitar) - 1):
                wait_for_web_signal(nav)
        elif result == TaskResult.CANCELED:
            print(f"⚠️ Misión cancelada a mitad de camino")
            break
        else:
            texto_error = f"Error en la navegación. No pude llegar a {habitacion['name']}"
            with open('/tmp/robot_llegada', 'w') as f:
                f.write(texto_error)
            print(f"❌ {texto_error}")

    if not os.path.exists(cancel_file):
        print_happy_robot()
        
    rclpy.shutdown()

if __name__ == '__main__':
    main()