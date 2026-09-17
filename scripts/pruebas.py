#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import os
import time
import sys
import threading
import numpy as np
import matplotlib.pyplot as plt

# Variable global para control de interrupción con la tecla 'h'
abort_requested = False

def speak(text):
    print(f"🤖 Robot dice: {text}")
    # os.system(f'espeak -v es "{text}"') # Descomenta si usas altavoces reales

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

def monitor_tecla_h():
    """Hilo secundario que vigila si presionas la tecla 'h' para abortar y graficar"""
    global abort_requested
    while not abort_requested:
        try:
            linea = input().strip().lower()
            if linea == 'h':
                print("\n\n🛑 ¡TECLA 'h' PRESIONADA! Deteniendo ensayos...")
                print("📊 Generando gráfico y reporte con los datos recopilados hasta ahora...\n")
                abort_requested = True
                break
        except EOFError:
            break

def esperar_tecla_g():
    print("\n" + "="*55)
    print("⏸️  SISTEMA EN ESPERA - EVALUACIÓN EXPERIMENTAL (15 ENSAYOS)")
    print("👉 Presiona la tecla [ g ] y luego [ ENTER ] para iniciar la prueba...")
    print("👉 Presiona la tecla [ h ] y luego [ ENTER ] en cualquier momento para detener y ver gráficos...")
    print("="*55 + "\n")
    
    while True:
        tecla = input("Ingresa comando: ").strip().lower()
        if tecla == 'g':
            print("🚀 ¡Tecla 'g' recibida! Iniciando batería de 15 ensayos...")
            break
        elif tecla == 'h':
            print("🛑 Interrupción solicitada antes de iniciar.")
            sys.exit(0)
        else:
            print(f"⚠️ Tecla '{tecla}' no reconocida. Presiona 'g' para empezar.")

def mostrar_reporte_y_grafica(tiempos_totales, exitos, fallos):
    print("\n" + "="*50)
    print("📊 REPORTE FINAL DE EVALUACIÓN EXPERIMENTAL 📊")
    print("="*50)
    total_intentados = len(tiempos_totales) + fallos
    print(f"Total de ciclos procesados/intentados: {total_intentados}")
    print(f"Ciclos exitosos completos: {exitos}")
    print(f"Ciclos con fallos/abortados: {fallos}")
    
    if len(tiempos_totales) > 0:
        t_promedio = np.mean(tiempos_totales)
        t_std = np.std(tiempos_totales)
        t_min = np.min(tiempos_totales)
        t_max = np.max(tiempos_totales)
        
        print(f"⏱️ Tiempo Promedio por Ciclo: {t_promedio:.2f} segundos")
        print(f"📉 Desviación Estándar: {t_std:.2f} segundos")
        print(f"⚡ Tiempo Mínimo: {t_min:.2f} segundos")
        print(f"🐢 Tiempo Máximo: {t_max:.2f} segundos")
        print("="*50 + "\n")

        # Generar gráfico interactivo con Matplotlib
        ensayos = np.arange(1, len(tiempos_totales) + 1)
        plt.figure(figsize=(10, 5))
        plt.plot(ensayos, tiempos_totales, marker='o', linestyle='-', color='#1f77b4', label='Tiempo por Ciclo')
        plt.axhline(t_promedio, color='red', linestyle='--', label=f'Promedio: {t_promedio:.2f} s')
        
        plt.title('Recorrido: Farmacia ➔ Espera 1 ➔ Almacén ➔ Espera 2 ➔ Espera 3', fontweight='bold', fontsize=10)
        plt.xlabel('Número de Ensayo Exitoso')
        plt.ylabel('Tiempo de Recorrido [s]')
        plt.xticks(ensayos)
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper right')
        plt.tight_layout()
        plt.show()
    else:
        print("❌ No se registraron tiempos válidos para graficar.")
        print("="*50 + "\n")

def main():
    global abort_requested

    # Diccionario de coordenadas actualizado 100% al frame 'map'
    mapa_salas = {
        'farmacia': {
            'name': 'Farmacia',
            'frame_id': 'map',
            'x': 6.936511039733887, 'y': -4.785110950469971,
            'qz': 0.08544607345748186, 'qw': 0.9963427966973508
        },
        'sala1': {
            'name': 'Sala de Espera 1',
            'frame_id': 'map',
            'x': -5.879590034484863, 'y': 3.370567560195923,
            'qz': -0.6970520339350216, 'qw': 0.7170205450243735
        },
        'sala2': {
            'name': 'Sala de Espera 2',
            'frame_id': 'map',
            'x': -0.020469188690185547, 'y': 3.505204200744629,
            'qz': -0.7012816223451832, 'qw': 0.7128843427659973
        },
        'sala3': {
            'name': 'Sala de Espera 3',
            'frame_id': 'map',
            'x': 5.70540714263916, 'y': 3.480185031890869,
            'qz': -0.6910061971163519, 'qw': 0.7228488331226643
        },
        'almacen_farmacia': {
            'name': 'Almacén de Farmacia',
            'frame_id': 'map',
            'x': -4.633490562438965, 'y': -5.18907356262207,
            'qz': -0.6419011817479123, 'qw': 0.7667873713557323
        }
    }

    # NUEVO ORDEN DEL RECORRIDO (5 destinos)
    lugares_a_visitar = [
        mapa_salas['farmacia'],           # 1. Primero a Farmacia
        mapa_salas['sala1'],              # 2. Después a Sala de Espera 1
        mapa_salas['almacen_farmacia'],   # 3. Después a Almacén de Farmacia
        mapa_salas['sala2'],              # 4. Después a Sala de Espera 2
        mapa_salas['sala3']               # 5. Último a Sala de Espera 3
    ]

    rclpy.init()
    nav = BasicNavigator()

    print("Esperando a que Nav2 se active...")
    nav.waitUntilNav2Active()

    esperar_tecla_g()

    hilo_teclado = threading.Thread(target=monitor_tecla_h, daemon=True)
    hilo_teclado.start()

    NUM_ENSAYOS = 15
    tiempos_totales_ciclo = []
    ensayos_exitosos = 0
    ensayos_fallidos = 0

    for ensayo in range(1, NUM_ENSAYOS + 1):
        if abort_requested:
            break

        print(f"\n================ 🔄 INICIO ENSAYO {ensayo}/{NUM_ENSAYOS} ================")
        inicio_ciclo = time.time()
        
        ciclo_exitoso = True

        for habitacion in lugares_a_visitar:
            if abort_requested:
                break

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

            print(f"🚀 Navegando hacia: {habitacion['name']} (Frame: {habitacion['frame_id']})")
            nav.goToPose(goal_pose)

            while not nav.isTaskComplete():
                if abort_requested:
                    nav.cancelTask()
                    break
                time.sleep(0.5)

            if abort_requested:
                break

            result = nav.getResult()
            if result == TaskResult.SUCCEEDED:
                speak(f"He llegado a {habitacion['name']}")
                
                print(f"⏳ Esperando 2 segundos en {habitacion['name']}...")
                for _ in range(4):
                    if abort_requested:
                        break
                    time.sleep(0.5)
            else:
                print(f"❌ No se pudo llegar a {habitacion['name']}")
                ciclo_exitoso = False
                nav.clearAllCostmaps()
                break

        if abort_requested:
            break

        tiempo_total_ciclo = time.time() - inicio_ciclo

        if ciclo_exitoso:
            tiempos_totales_ciclo.append(tiempo_total_ciclo)
            ensayos_exitosos += 1
            print(f"🎉 Ensayo {ensayo} completado con éxito en {tiempo_total_ciclo:.2f} segundos.")
        else:
            ensayos_fallidos += 1
            print(f"❌ Ensayo {ensayo} marcado como FALLIDO.")

        if ensayo < NUM_ENSAYOS and not abort_requested:
            print("⏸️ Pausando 3 segundos antes del siguiente ensayo...")
            for _ in range(6):
                if abort_requested:
                    break
                time.sleep(0.5)

    print_happy_robot()
    rclpy.shutdown()

    mostrar_reporte_y_grafica(tiempos_totales_ciclo, ensayos_exitosos, ensayos_fallidos)

if __name__ == '__main__':
    main()