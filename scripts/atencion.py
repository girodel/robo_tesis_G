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
    # Instalación necesaria: sudo apt install espeak
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

def wait_for_g():
    """Bloquea el script hasta que el usuario presione 'g' y Enter"""
    print("\n⏸️  El robot está esperando confirmación para continuar.")
    while True:
        entrada = input("👉 Presiona la letra 'g' y Enter para ir a la siguiente posición: ").strip().lower()
        if entrada == 'g':
            print("✅ Orden recibida. Avanzando...\n")
            break
        else:
            print("⚠️  Entrada no válida. Debes escribir la letra 'g' para continuar.")

def main():
    rclpy.init()
    nav = BasicNavigator()

    # --- Configuración de las Salas (Almacén Actualizado) ---
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

    # Esperar a que Nav2 esté completamente listo
    print("Esperando a que Nav2 se active...")
    nav.waitUntilNav2Active()

    for room in rooms:
        # Crear mensaje de posición
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

        print(f"🚀 Iniciando navegación hacia: {room['name']} (Frame: {room['frame_id']})")
        nav.goToPose(goal_pose)

        # Monitorear hasta llegar
        while not nav.isTaskComplete():
            time.sleep(1)

        # Verificar resultado
        result = nav.getResult()
        if result == TaskResult.SUCCEEDED:
            speak(f"He llegado a {room['name']}")
            # Interrupción manual: Espera a que presiones 'g' antes de continuar
            wait_for_g()
        else:
            print(f"❌ No se pudo llegar a {room['name']}")

    print("🏁 Todas las posiciones han sido visitadas.")
    speak("Misión completada con éxito.")
    
    # Imprimimos el robot sonriente en la terminal
    print_happy_robot()

    rclpy.shutdown()

if __name__ == '__main__':
    main()