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
        
        .btn-add { background-color: #ffc107; color: black; width: 40%; font-size: 14px; padding: 10px; margin: 4px; display: inline-block; }
        .btn-start-route { background-color: #28a745; margin-top: 10px;}
        .btn-clear-route { background-color: #6c757d; margin-top: 10px;}
        
        .btn-cerrar { background-color: #dc3545; margin-top: 20px;} 
        
        .btn-logout { background-color: #6c757d; padding: 8px; font-size: 14px; width: auto; position: absolute; top: 10px; right: 10px; }
        #status { margin-top: 20px; font-size: 16px; font-weight: bold; color: #444; border: 1px solid #ccc; padding: 10px; background: white; border-radius: 8px; display: inline-block; width: 85%; max-width: 330px;}
        .seccion { margin-top: 15px; border-top: 2px dashed #ccc; padding-top: 15px; }
        
        .ruta-box { margin: 10px auto; padding: 10px; background: #e9ecef; border-radius: 5px; width: 85%; max-width: 330px; font-weight: bold; color: #333; min-height: 24px;}
        
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
    <button class="btn btn-farmacia" onclick="irA('farmacia', 'Farmacia')">🏥 Ir a Farmacia</button>
    <br>
    <button class="btn btn-atencion1" onclick="irA('atencion1', 'Sala Espera 1')">🩺 Ir a Sala Espera 1</button>
    <br>
    <button class="btn btn-atencion2" onclick="irA('atencion2', 'Sala Espera 2')">🩺 Ir a Sala Espera 2</button>
    <br>
    <button class="btn btn-atencion3" onclick="irA('atencion3', 'Sala Espera 3')">🩺 Ir a Sala Espera 3</button>
    <br>
    <button class="btn btn-almacen" onclick="irA('almacen_farmacia', 'Almacén de Farmacia')">📦 Ir al Almacén</button>
    
    <div class="seccion">
        <div><strong>Ruta Personalizada:</strong></div>
        <div class="ruta-box" id="ruta-display">📍 (Ruta vacía)</div>
        
        <div>
            <button class="btn btn-add" onclick="agregarARuta('farmacia', 'Farmacia')">+ Farmacia</button>
            <button class="btn btn-add" onclick="agregarARuta('atencion1', 'Sala 1')">+ Sala 1</button>
            <button class="btn btn-add" onclick="agregarARuta('atencion2', 'Sala 2')">+ Sala 2</button>
            <button class="btn btn-add" onclick="agregarARuta('atencion3', 'Sala 3')">+ Sala 3</button>
            <button class="btn btn-add" onclick="agregarARuta('almacen_farmacia', 'Almacén')">+ Almacén</button>
        </div>
        
        <button class="btn btn-start-route" onclick="iniciarRutaPersonalizada()">▶️ INICIAR RUTA</button>
        <br>
        <button class="btn btn-clear-route" onclick="limpiarRuta()">🗑️ LIMPIAR RUTA</button>
    </div>
    
    <button class="btn btn-cerrar" onclick="cerrar()">■ DETENER ROBOT / CANCELAR</button>
    
    <br>
    <div id="status">Conexión Segura Activa. Esperando órdenes...</div>

    <script>
        // --- MOTOR DE VOZ PARA EL CELULAR ---
        function hablar(texto) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel(); 
                let msg = new SpeechSynthesisUtterance(texto);
                msg.lang = "es-ES";
                msg.rate = 1.0;
                window.speechSynthesis.speak(msg);
            }
        }

        // --- LÓGICA DE BATERÍA ---
        let bateria = 100;
        let barraBateria = document.getElementById("bateria-barra");
        
        // 100% de caída en 360 segundos (6 minutos) = 1% cada 3.6 segundos (3600 ms)
        let intervaloBateria = setInterval(() => {
            if (bateria > 0) {
                bateria--;
                barraBateria.style.width = bateria + "%";
                barraBateria.innerText = bateria + "% 🔋";

                if (bateria <= 50 && bateria > 20) {
                    barraBateria.style.backgroundColor = "#ffc107"; 
                    barraBateria.style.color = "black";
                } else if (bateria <= 20 && bateria > 0) {
                    barraBateria.style.backgroundColor = "#dc3545"; 
                    barraBateria.style.color = "white";
                }

                if (bateria === 20) {
                    document.getElementById("status").innerText = "⚠️ ADVERTENCIA: El robot requiere recargarse";
                    document.getElementById("status").style.color = "red";
                    hablar("El robot requiere recargarse");
                }
                
                // CERO ABSOLUTO: Frenado forzoso
                if (bateria === 0) {
                    clearInterval(intervaloBateria);
                    document.getElementById("status").innerText = "🛑 Batería agotada. Motores apagados.";
                    document.getElementById("status").style.color = "white";
                    document.getElementById("status").style.backgroundColor = "black";
                    hablar("Batería agotada. Motores apagados.");
                    fetch('/ejecutar_cerrar'); // Manda a frenar a ROS 2 inmediatamente
                }
            }
        }, 3600); // 3600 ms = 3.6 segundos por 1% -> 360 segundos (6 minutos total)

        // --- LÓGICA DE RUTA PERSONALIZADA ---
        let ids_ruta = [];
        let nombres_ruta = [];

        function agregarARuta(id, nombre) {
            ids_ruta.push(id);
            nombres_ruta.push(nombre);
            document.getElementById("ruta-display").innerText = "📍 " + nombres_ruta.join(" ➔ ");
        }

        function limpiarRuta() {
            ids_ruta = [];
            nombres_ruta = [];
            document.getElementById("ruta-display").innerText = "📍 (Ruta vacía)";
        }

        function iniciarRutaPersonalizada() {
            if (bateria <= 0) {
                alert("⛔ Batería agotada. Recargue el robot para continuar.");
                return;
            }
            if (ids_ruta.length === 0) {
                alert("Primero agrega salas a tu ruta.");
                return;
            }
            let destino_texto = nombres_ruta.join(", luego a ");
            let destino_codigos = ids_ruta.join(",");
            
            document.getElementById("status").innerText = "🚀 Ejecutando ruta: " + nombres_ruta.join(" ➔ ");
            hablar("Iniciando ruta personalizada. Me dirijo a " + destino_texto);
            
            fetch('/ejecutar_ir_a/' + destino_codigos);
            limpiarRuta();
        }

        // --- LÓGICA DE MOVIMIENTO DIRECTO ---
        function irA(sala, nombre) {
            if (bateria <= 0) {
                alert("⛔ Batería agotada. Recargue el robot para continuar.");
                return;
            }
            
            document.getElementById("status").innerText = "🚀 Yendo a: " + nombre;
            hablar("Orden recibida. Me dirijo a " + nombre);
            
            fetch('/ejecutar_ir_a/' + sala);
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
                    hablar(data); 
                }
            }).catch(e => console.log(e));
        }, 1500);
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
    if not session.get('autenticado'): return "", 401
    archivo_llegada = '/tmp/robot_llegada'
    if os.path.exists(archivo_llegada):
        with open(archivo_llegada, 'r') as f:
            mensaje = f.read().strip()
        os.remove(archivo_llegada) 
        return mensaje
    return ""

@app.route('/ejecutar_ir_a/<sala>')
def ejecutar_ir_a(sala):
    if not session.get('autenticado'): return "No autorizado", 401
    global proceso_nodo
    
    # 1. Enviar señal de cancelación a atencion.py
    with open('/tmp/robot_cancel', 'w') as f: 
        f.write('stop')
    
    # 2. Esperar 2.5 segundos. Esto le da tiempo al robot de detenerse por completo
    # y al script anterior de desconectarse sin crashear a Nav2 ni perder su ubicación
    time.sleep(2.5) 
    
    # 3. Limpieza forzada por si se quedó colgado (ya no debería ser necesario, pero es un seguro)
    if proceso_nodo:
        proceso_nodo.terminate()
        subprocess.run(["pkill", "-f", "atencion.py"])
        proceso_nodo = None
    
    if os.path.exists('/tmp/robot_cancel'): os.remove('/tmp/robot_cancel')
    if os.path.exists('/tmp/robot_llegada'): os.remove('/tmp/robot_llegada')
    
    # 4. Iniciar la nueva ruta desde donde se quedó
    with open('/tmp/robot_destino', 'w') as f:
        f.write(sala)
        
    comando = ["ros2", "run", "my_robot_description", "atencion.py"]
    proceso_nodo = subprocess.Popen(comando)
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