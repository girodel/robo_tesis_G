#!/usr/bin/env python3
from flask import Flask, render_template_string
import subprocess
import os

app = Flask(__name__)
proceso_nodo = None

# Interfaz adaptada para Navegación Nav2
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Navegación Nav2</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 30px; background-color: #f0f2f5;}
        .btn { padding: 15px; font-size: 18px; margin: 10px; border: none; border-radius: 8px; cursor: pointer; width: 85%; max-width: 350px; color: white; font-weight: bold;}
        .btn-iniciar { background-color: #28a745; } /* Verde */
        .btn-continuar { background-color: #007bff; } /* Azul */
        .btn-cerrar { background-color: #dc3545; } /* Rojo */
        #status { margin-top: 15px; font-size: 18px; font-weight: bold; color: #444; }
    </style>
</head>
<body>
    <h2>Control de Navegación</h2>
    
    <button class="btn btn-iniciar" onclick="iniciar()">▶ INICIAR NAVEGACIÓN</button>
    <button class="btn btn-continuar" onclick="continuar()">⏩ CONTINUAR A SIGUIENTE SALA</button>
    <button class="btn btn-cerrar" onclick="cerrar()">■ CANCELAR MISIÓN</button>
    
    <div id="status">Esperando comandos...</div>

    <script>
        function iniciar() {
            document.getElementById("status").innerText = "Robot en movimiento hacia el objetivo...";
            fetch('/ejecutar_iniciar');
        }

        function continuar() {
            document.getElementById("status").innerText = "Orden enviada. Avanzando a la siguiente sala...";
            fetch('/ejecutar_continuar');
        }

        function cerrar() {
            document.getElementById("status").innerText = "Misión cancelada abruptamente.";
            fetch('/ejecutar_cerrar');
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/ejecutar_iniciar')
def iniciar():
    global proceso_nodo
    # IMPORTANTE: Asegúrate de que "atencion.py" coincida con el nombre que le diste a tu script
    comando = ["ros2", "run", "my_robot_description", "atencion.py"]
    proceso_nodo = subprocess.Popen(comando)
    return "OK"

@app.route('/ejecutar_continuar')
def continuar():
    # Creamos el archivo "señal" que el script atencion.py está esperando
    with open('/tmp/robot_continue', 'w') as f:
        f.write('go')
    return "OK"

@app.route('/ejecutar_cerrar')
def cerrar():
    global proceso_nodo
    if proceso_nodo:
        proceso_nodo.terminate()
        proceso_nodo = None
    # Matamos el proceso del nodo por seguridad
    subprocess.run(["pkill", "-f", "atencion.py"])
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)