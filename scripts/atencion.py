#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import os
import time

def speak(text):
    """Función para que el robot hable usando espeak"""
    print(f"🤖 Robot dice: {text}")
    os.system(f'espeak -v es "{text}"')

def print_happy_robot():
    """Función para imprimir un robot sonriente en la terminal"""
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
    """Bloquea el script hasta que se presione el botón en la web"""
    print("\n⏸️  El robot está esperando confirmación desde el celular para continuar...")
    flag_file = '/tmp/robot_continue'
    
    # Limpiamos la señal por si existía de antes
    if os.path.exists(flag_file):
        os.remove(flag_file)

    # Espera infinita hasta que el servidor web cree el archivo
    while True:
        if os.path.exists(flag_file):
            print("✅ ¡Orden web recibida! Avanzando...\n")
            os.remove(flag_file) # Borramos la señal para la próxima parada
            break
        time.sleep(0.5)

def main():
    rclpy.init()
    nav = BasicNavigator()

    rooms = [
        {
            'name': 'Sala de espera farmacia',
            'frame_id': 'map',
            'x': 6.079612882957816, 'y': -4.391466473200874,
            'qz': -0.9066373487694229, 'qw': -0.42191079367130657
        },
        {
            'name': 'Sala de atención 1',
            'frame_id': 'map',
            'x': -3.982675852552293, 'y': 2.4858608729289147,
            'qz': 0.47691072057509853, 'qw': -0.8789517419065397
        }
    ]

    print("Esperando a que Nav2 se active...")
    nav.waitUntilNav2Active()

    for room in rooms:
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = room['frame_id']
        goal_pose.header.stamp = nav.get_clock().now().to_msg()
        
        goal_pose.pose.position.x = room['x']
        goal_pose.pose.position.y = room['y']
        goal_pose.pose.position.z = 0.0
        
        goal_pose.pose.orientation.x = 0.0
        goal_pose.pose.orientation.y = 0.0
        goal_pose.pose.orientation.z = room['qz']
        goal_pose.pose.orientation.w = room['qw']

        print(f"🚀 Iniciando navegación hacia: {room['name']}")
        nav.goToPose(goal_pose)

        while not nav.isTaskComplete():
            time.sleep(1)

        result = nav.getResult()
        if result == TaskResult.SUCCEEDED:
            speak(f"He llegado a {room['name']}")
            # Reemplazamos tu wait_for_g() por la espera web
            wait_for_web_signal()
        else:
            print(f"❌ No se pudo llegar a {room['name']}")

    print("🏁 Todas las posiciones han sido visitadas.")
    speak("Misión completada con éxito.")
    print_happy_robot()

    rclpy.shutdown()

if __name__ == '__main__':
    main()