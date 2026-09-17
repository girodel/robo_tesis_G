#!/usr/bin/env python3
from flask import Flask, render_template_string, request, redirect, url_for, session
import subprocess
import socket
import os
import time

app = Flask(__name__)
app.secret_key = 'mi_llave_secreta_super_segura_para_el_robot'

USUARIO_CORRECTO = "joker"
CONTRASENA_CORRECTA = "giro12"

proceso_nodo = None

def obtener_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Acceso - Control Robot</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f0f2f5;}
        .login-card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); display: inline-block; width: 85%; max-width: 350px; }
        h3 { color: #333; margin-bottom: 20px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 16px;}
        .btn-login { background-color: #007bff; color: white; width: 100%; padding: 12px; border: none; border-radius: 6px; font-size: 18px; font-weight: bold; cursor: pointer;}
        .error-msg { color: #dc3545; font-weight: bold; margin-bottom: 10px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h3>🔐 Control de Robot</h3>
        {% if error %}
            <div class="error-msg">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Usuario" required autocomplete="off">
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit" class="btn-login">Ingresar</button>
        </form>
    </div>
</body>
</html>
"""

PANEL_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Panel Control Nav2</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 20px; background-color: #f0f2f5;}
        .btn { padding: 12px; font-size: 16px; margin: 8px; border: none; border-radius: 8px; cursor: pointer; width: 90%; max-width: 350px; color: white; font-weight: bold;}
        
        .btn-farmacia { background-color: #17a2b8; } 
        .btn-atencion1 { background-color: #fd7e14; }
        .btn-atencion2 { background-color: #e83e8c; }
        .btn-atencion3 { background-color: #20c997; } 
        .btn-almacen { background-color: #6610f2; }   
        
        .btn-tour { background-color: #343a40; margin-top: 15px;} 
        .btn-continuar { background-color: #007bff; margin-top: 20px;} 
        .btn-cerrar { background-color: #dc3545; margin-top: 20px;} 
        
        .btn-logout { background-color: #6c757d; padding: 8px; font-size: 14px; width: auto; position: absolute; top: 10px; right: 10px; }
        #status { margin-top: 20px; font-size: 16px; font-weight: bold; color: #444; border: 1px solid #ccc; padding: 10px; background: white; border-radius: 8px; display: inline-block; width: 85%; max-width: 330px;}
        .seccion { margin-top: 15px; border-top: 2px dashed #ccc; padding-top: 15px; }
        
        /* Estilos de la Batería */
        .bateria-container { margin: 10px auto 20px auto; width: 85%; max-width: 350px; background: #e9ecef; border-radius: 10px; border: 2px solid #ccc; overflow: hidden; position: relative; height: 30px; }
        .bateria-barra { height: 100%; width: 100%; background-color: #28a745; transition: width 0.5s ease-in-out, background-color 0.5s; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; white-space: nowrap; }
    </style>
</head>
<body>
    <a href="/logout"><button class="btn btn-logout">🔒 Salir</button></a>
    <h2>Control de Navegación</h2>

    <div class="bateria-container">
        <div id="bateria-barra" class="bateria-barra">100% 🔋</div>
    </div>
    
    <div><strong>Destinos Directos:</strong></div>
    <button class="btn btn-farmacia" onclick="irA('farmacia')">🏥 Ir a Farmacia</button>
    <br>
    <button class="btn btn-atencion1" onclick="irA('atencion1')">🩺 Ir a Sala Espera 1</button>
    <br>
    <button class="btn btn-atencion2" onclick="irA('atencion2')">🩺 Ir a Sala Espera 2</button>
    <br>
    <button class="btn btn-atencion3" onclick="irA('atencion3')">🩺 Ir a Sala Espera 3</button>
    <br>
    <button class="btn btn-almacen" onclick="irA('almacen_farmacia')">📦 Ir al Almacén</button>
    
    <div class="seccion">
        <div><strong>Modo Trayectoria:</strong></div>
        <button class="btn btn-tour" onclick="irA('recorrido')">🗺️ INICIAR RECORRIDO COMPLETO</button>
        <br>
        <button class="btn btn-continuar" onclick="continuar()">⏩ CONTINUAR A SIGUIENTE SALA</button>
    </div>
    
    <button class="btn btn-cerrar" onclick="cerrar()">■ DETENER ROBOT / CANCELAR</button>
    
    <br>
    <div id="status">Conexión Segura Activa. Esperando órdenes...</div>

    <script>
        // --- MOTOR DE VOZ PARA EL CELULAR ---
        function hablar(texto) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel(); // Evita que se acumulen voces
                let msg = new SpeechSynthesisUtterance(texto);
                msg.lang = "es-ES";
                msg.rate = 1.0;
                window.speechSynthesis.speak(msg);
            }
        }

        // --- LÓGICA DE BATERÍA ---
        let bateria = 100;
        let barraBateria = document.getElementById("bateria-barra");
        
        let intervaloBateria = setInterval(() => {
            if (bateria > 0) {
                bateria--;
                barraBateria.style.width = bateria + "%";
                barraBateria.innerText = bateria + "% 🔋";

                if (bateria <= 50 && bateria > 20) {
                    barraBateria.style.backgroundColor = "#ffc107"; 
                    barraBateria.style.color = "black";
                } else if (bateria <= 20) {
                    barraBateria.style.backgroundColor = "#dc3545"; 
                    barraBateria.style.color = "white";
                }

                if (bateria === 20) {
                    document.getElementById("status").innerText = "⚠️ ADVERTENCIA: El robot requiere recargarse";
                    document.getElementById("status").style.color = "red";
                    hablar("El robot requiere recargarse");
                }
            } else {
                clearInterval(intervaloBateria);
                document.getElementById("status").innerText = "🛑 Batería agotada. Robot apagado.";
            }
        }, 2400);

        // --- LÓGICA DE MOVIMIENTO ---
        function irA(sala) {
            if (bateria === 0) return;
            let destino_texto = "";
            if(sala === 'farmacia') destino_texto = "Farmacia";
            else if(sala === 'atencion1') destino_texto = "Sala de Espera 1";
            else if(sala === 'atencion2') destino_texto = "Sala de Espera 2";
            else if(sala === 'atencion3') destino_texto = "Sala de Espera 3";
            else if(sala === 'almacen_farmacia') destino_texto = "Almacén de Farmacia";
            else destino_texto = "Recorrido Completo";
            
            document.getElementById("status").innerText = "🚀 Yendo a: " + destino_texto;
            hablar("Orden recibida. Me dirijo a " + destino_texto);
            
            fetch('/ejecutar_ir_a/' + sala);
        }

        function continuar() {
            if (bateria === 0) return;
            document.getElementById("status").innerText = "⏩ Avanzando a la siguiente sala...";
            hablar("Avanzando a la siguiente sala");
            fetch('/ejecutar_continuar');
        }

        function cerrar() {
            document.getElementById("status").innerText = "🛑 Frenando robot y cancelando misión...";
            hablar("Misión cancelada. Deteniendo motores.");
            fetch('/ejecutar_cerrar');
        }

        // --- VERIFICAR LLEGADA CONSTANTEMENTE ---
        setInterval(() => {
            fetch('/estado_robot')
            .then(response => response.text())
            .then(data => {
                if (data.trim() !== "") {
                    document.getElementById("status").innerText = "✅ " + data;
                    hablar(data); // Hace que el celular diga el mensaje de llegada
                }
            }).catch(e => console.log(e));
        }, 1500); // Consulta cada 1.5 segundos
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    if session.get('autenticado'):
        return render_template_string(PANEL_PAGE)
    return render_template_string(LOGIN_PAGE, error=None)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == USUARIO_CORRECTO and password == CONTRASENA_CORRECTA:
        session['autenticado'] = True
        return redirect(url_for('index'))
    else:
        return render_template_string(LOGIN_PAGE, error="Usuario o contraseña incorrectos")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/estado_robot')
def estado_robot():
    """Ruta que la web consulta para saber si el robot llegó a su destino"""
    if not session.get('autenticado'): return "", 401
    archivo_llegada = '/tmp/robot_llegada'
    if os.path.exists(archivo_llegada):
        with open(archivo_llegada, 'r') as f:
            mensaje = f.read().strip()
        os.remove(archivo_llegada) # Lo borramos para que no repita el audio
        return mensaje
    return ""

@app.route('/ejecutar_ir_a/<sala>')
def ejecutar_ir_a(sala):
    if not session.get('autenticado'): return "No autorizado", 401
    global proceso_nodo
    
    with open('/tmp/robot_cancel', 'w') as f: f.write('stop')
    time.sleep(1.0) 
    
    if proceso_nodo:
        proceso_nodo.terminate()
        subprocess.run(["pkill", "-f", "atencion.py"])
    
    if os.path.exists('/tmp/robot_cancel'): os.remove('/tmp/robot_cancel')
    if os.path.exists('/tmp/robot_llegada'): os.remove('/tmp/robot_llegada')
    
    with open('/tmp/robot_destino', 'w') as f:
        f.write(sala)
        
    comando = ["ros2", "run", "my_robot_description", "atencion.py"]
    proceso_nodo = subprocess.Popen(comando)
    return "OK"

@app.route('/ejecutar_continuar')
def continuar():
    if not session.get('autenticado'): return "No autorizado", 401
    with open('/tmp/robot_continue', 'w') as f:
        f.write('go')
    return "OK"

@app.route('/ejecutar_cerrar')
def cerrar():
    if not session.get('autenticado'): return "No autorizado", 401
    with open('/tmp/robot_cancel', 'w') as f:
        f.write('stop')
    return "OK"

if __name__ == '__main__':
    ip_actual = obtener_ip_local()
    url_servidor = f"http://{ip_actual}:5000/"
    
    print("\n" + "="*50)
    print("      SISTEMA DE CONTROL REMOTO PARA TESIS")
    print(f" URL de acceso: {url_servidor}")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000)