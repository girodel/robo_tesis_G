#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import os
import time
import sys

def speak(text):
    print(f"🤖 Robot dice: {text}")
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

def wait_for_web_signal():
    """Bloquea el script hasta que se presione el botón CONTINUAR en la web"""
    print("\n⏸️  Modo Recorrido: Esperando confirmación desde el celular para ir a la siguiente sala...")
    flag_file = '/tmp/robot_continue'
    
    if os.path.exists(flag_file):
        os.remove(flag_file)

    while True:
        if os.path.exists(flag_file):
            print("✅ ¡Orden web recibida! Avanzando...\n")
            os.remove(flag_file)
            break
        time.sleep(0.5)

def main():
    destino_archivo = '/tmp/robot_destino'
    if not os.path.exists(destino_archivo):
        print("❌ Error: No se especificó un destino. Usa la web.")
        sys.exit(1)
        
    with open(destino_archivo, 'r') as f:
        modo_solicitado = f.read().strip()

    # Definición del mapa de coordenadas
    mapa_salas = {
        'farmacia': {
            'name': 'Sala de espera farmacia',
            'frame_id': 'map',
            'x': 6.079612882957816, 'y': -4.391466473200874,
            'qz': -0.9066373487694229, 'qw': -0.42191079367130657
        },
        'atencion1': {
            'name': 'Sala de atención 1',
            'frame_id': 'map',
            'x': -3.982675852552293, 'y': 2.4858608729289147,
            'qz': 0.47691072057509853, 'qw': -0.8789517419065397
        }
    }

    # Armamos la lista de lugares a visitar según lo que se pidió en la web
    lugares_a_visitar = []
    if modo_solicitado == 'farmacia':
        lugares_a_visitar.append(mapa_salas['farmacia'])
    elif modo_solicitado == 'atencion1':
        lugares_a_visitar.append(mapa_salas['atencion1'])
    elif modo_solicitado == 'recorrido':
        lugares_a_visitar.append(mapa_salas['farmacia'])
        lugares_a_visitar.append(mapa_salas['atencion1'])
    else:
        print(f"❌ Error: Modo '{modo_solicitado}' no reconocido.")
        sys.exit(1)

    rclpy.init()
    nav = BasicNavigator()

    print("Esperando a que Nav2 se active...")
    nav.waitUntilNav2Active()

    # Bucle de navegación
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
            time.sleep(1)

        result = nav.getResult()
        if result == TaskResult.SUCCEEDED:
            speak(f"He llegado a {habitacion['name']}")
            
            # Si estamos en modo recorrido Y no es la última sala, pausamos
            if modo_solicitado == 'recorrido' and i < (len(lugares_a_visitar) - 1):
                wait_for_web_signal()
        else:
            print(f"❌ No se pudo llegar a {habitacion['name']}")

    print_happy_robot()
    rclpy.shutdown()

if __name__ == '__main__':
    main()