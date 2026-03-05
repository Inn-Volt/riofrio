from flask import Flask, request, jsonify, render_template_string, redirect, session
import os
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "innvolt2026riofrio")

DATABASE_URL = os.environ.get("DATABASE_URL")

# ==================== BASE DE DATOS ====================
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS numeros (
            id SERIAL PRIMARY KEY,
            numero VARCHAR(20) UNIQUE NOT NULL,
            creado_en TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(20),
            numero VARCHAR(20),
            resultado VARCHAR(20),
            fecha TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comandos (
            id SERIAL PRIMARY KEY,
            comando VARCHAR(20),
            ejecutado BOOLEAN DEFAULT FALSE,
            creado_en TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# ==================== PANEL HTML ====================
PANEL_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel InnVolt - Rio Frio</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
body{
  font-family:'Inter',sans-serif;
  background:#0a0a0a;
  color:#fff;
  min-height:100vh;
  padding:20px;
}
.header{
  max-width:900px;margin:0 auto 30px auto;
  display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:16px;
}
.logo-wrap{display:flex;align-items:center;gap:10px;}
.logo-icon{
  width:42px;height:42px;
  background:linear-gradient(135deg,#f5a623,#e08c00);
  border-radius:10px;
  display:flex;align-items:center;justify-content:center;
  font-size:20px;font-weight:900;color:#000;
}
.logo-text{font-size:24px;font-weight:900;letter-spacing:2px;}
.logo-text span{color:#f5a623;}
.tagline{font-size:11px;letter-spacing:2px;color:#f5a623;text-transform:uppercase;}
.btn-logout{
  padding:8px 16px;font-size:12px;font-weight:600;
  border:1px solid #333;border-radius:8px;
  background:transparent;color:#888;cursor:pointer;
  text-decoration:none;letter-spacing:1px;text-transform:uppercase;
}
.btn-logout:hover{border-color:#ff4444;color:#ff4444;}
.grid{
  max-width:900px;margin:0 auto;
  display:grid;grid-template-columns:1fr 1fr;gap:20px;
}
@media(max-width:600px){.grid{grid-template-columns:1fr;}}
.card{
  background:#111;border:1px solid #222;
  border-radius:16px;padding:24px;
}
.card-title{
  font-size:11px;letter-spacing:3px;text-transform:uppercase;
  color:#f5a623;margin-bottom:16px;
}
.btn-main{
  display:block;width:100%;padding:16px;
  font-size:16px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  border:none;border-radius:10px;
  background:linear-gradient(135deg,#f5a623,#e08c00);
  color:#000;cursor:pointer;margin-bottom:8px;
}
.btn-main:hover{opacity:0.9;}
.btn-main:disabled{background:#333;color:#555;cursor:not-allowed;}
.status-ok{
  font-size:12px;color:#22c55e;
  text-align:center;margin-top:8px;min-height:18px;
}
.num-list{list-style:none;}
.num-list li{
  display:flex;justify-content:space-between;align-items:center;
  padding:10px 12px;background:#1a1a1a;
  border:1px solid #222;border-radius:8px;margin-bottom:8px;
  font-size:14px;color:#ccc;
}
.btn-del{
  background:#2a0a0a;border:1px solid #5a1a1a;
  color:#ff4444;padding:4px 10px;border-radius:6px;
  font-size:12px;cursor:pointer;border:none;
}
input[type=text]{
  width:100%;padding:12px;font-size:14px;
  background:#1a1a1a;border:1px solid #333;
  border-radius:8px;color:#fff;margin-bottom:10px;outline:none;
}
input[type=text]:focus{border-color:#f5a623;}
.hist-item{
  padding:10px 12px;background:#1a1a1a;
  border:1px solid #222;border-radius:8px;margin-bottom:6px;
  font-size:13px;
}
.hist-item .tipo{color:#f5a623;font-weight:600;}
.hist-item .num{color:#ccc;}
.hist-item .fecha{color:#555;font-size:11px;margin-top:2px;}
.badge-ok{color:#22c55e;}
.badge-no{color:#ff4444;}
.empty{color:#555;font-size:13px;text-align:center;padding:20px 0;}
.full-card{grid-column:1/-1;}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="logo-wrap">
      <div class="logo-icon">IV</div>
      <div class="logo-text">INN<span>VOLT</span></div>
    </div>
    <div class="tagline">Panel de Control - Rio Frio</div>
  </div>
  <a href="/logout" class="btn-logout">Cerrar sesion</a>
</div>

<div class="grid">

  <!-- ABRIR PORTON -->
  <div class="card">
    <div class="card-title">Control Remoto</div>
    <button class="btn-main" onclick="abrirPorton()" id="btnAbrir">ABRIR PORTON</button>
    <div class="status-ok" id="statusAbrir"></div>
  </div>

  <!-- AGREGAR NUMERO -->
  <div class="card">
    <div class="card-title">Agregar Numero</div>
    <input type="text" id="nuevoNum" placeholder="Ej: +56912345678">
    <button class="btn-main" onclick="agregarNumero()">AGREGAR</button>
    <div class="status-ok" id="statusAdd"></div>
  </div>

  <!-- LISTA NUMEROS -->
  <div class="card">
    <div class="card-title">Numeros Autorizados ({{ numeros|length }}/20)</div>
    {% if numeros %}
    <ul class="num-list">
      {% for n in numeros %}
      <li>
        <span>{{ n.numero }}</span>
        <button class="btn-del" onclick="eliminarNumero('{{ n.numero }}')">Eliminar</button>
      </li>
      {% endfor %}
    </ul>
    {% else %}
    <div class="empty">Sin numeros registrados</div>
    {% endif %}
  </div>

  <!-- HISTORIAL -->
  <div class="card">
    <div class="card-title">Historial de Accesos</div>
    {% if historial %}
      {% for h in historial %}
      <div class="hist-item">
        <div>
          <span class="tipo">{{ h.tipo }}</span>
          <span class="num"> — {{ h.numero }}</span>
          <span class="{{ 'badge-ok' if h.resultado == 'autorizado' else 'badge-no' }}"> {{ h.resultado }}</span>
        </div>
        <div class="fecha">{{ h.fecha.strftime('%d/%m/%Y %H:%M:%S') }}</div>
      </div>
      {% endfor %}
    {% else %}
    <div class="empty">Sin registros aun</div>
    {% endif %}
  </div>

</div>

<script>
function abrirPorton(){
  var btn = document.getElementById('btnAbrir');
  var st = document.getElementById('statusAbrir');
  btn.disabled = true;
  btn.innerText = 'ENVIANDO...';
  fetch('/api/abrir', {method:'POST', headers:{'X-API-Key':'{{ api_key }}'}})
    .then(r=>r.json())
    .then(d=>{
      st.innerText = 'Comando enviado! El porton abrira en unos segundos.';
      setTimeout(()=>{
        btn.disabled=false;
        btn.innerText='ABRIR PORTON';
        st.innerText='';
      }, 5000);
    });
}

function agregarNumero(){
  var n = document.getElementById('nuevoNum').value.trim();
  var st = document.getElementById('statusAdd');
  if(!n){ st.innerText='Ingresa un numero'; return; }
  fetch('/api/numeros/add', {
    method:'POST',
    headers:{'Content-Type':'application/json','X-API-Key':'{{ api_key }}'},
    body: JSON.stringify({numero: n})
  }).then(r=>r.json()).then(d=>{
    if(d.ok){ st.innerText='Numero agregado!'; setTimeout(()=>location.reload(),1000); }
    else{ st.innerText = d.error || 'Error'; }
  });
}

function eliminarNumero(n){
  if(!confirm('Eliminar ' + n + '?')) return;
  fetch('/api/numeros/del', {
    method:'POST',
    headers:{'Content-Type':'application/json','X-API-Key':'{{ api_key }}'},
    body: JSON.stringify({numero: n})
  }).then(r=>r.json()).then(d=>{
    if(d.ok) location.reload();
  });
}
</script>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login - InnVolt Rio Frio</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
body{
  font-family:'Inter',sans-serif;
  background:#0a0a0a;color:#fff;
  min-height:100vh;display:flex;
  align-items:center;justify-content:center;padding:20px;
}
.card{
  width:100%;max-width:380px;
  background:#111;border:1px solid #222;
  border-radius:16px;padding:32px 28px;text-align:center;
}
.logo-wrap{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:6px;}
.logo-icon{
  width:42px;height:42px;
  background:linear-gradient(135deg,#f5a623,#e08c00);
  border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-size:20px;font-weight:900;color:#000;
}
.logo-text{font-size:24px;font-weight:900;letter-spacing:2px;}
.logo-text span{color:#f5a623;}
.tagline{font-size:11px;letter-spacing:2px;color:#f5a623;text-transform:uppercase;margin-bottom:28px;}
input[type=password]{
  width:100%;padding:14px;font-size:15px;
  background:#1a1a1a;border:1px solid #333;
  border-radius:8px;color:#fff;margin-bottom:12px;outline:none;
}
input[type=password]:focus{border-color:#f5a623;}
.btn{
  display:block;width:100%;padding:16px;
  font-size:16px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  border:none;border-radius:10px;
  background:linear-gradient(135deg,#f5a623,#e08c00);
  color:#000;cursor:pointer;
}
.error{color:#ff4444;font-size:13px;margin-top:10px;}
</style>
</head>
<body>
<div class="card">
  <div class="logo-wrap">
    <div class="logo-icon">IV</div>
    <div class="logo-text">INN<span>VOLT</span></div>
  </div>
  <div class="tagline">Panel Rio Frio</div>
  <form method="post">
    <input type="password" name="pass" placeholder="Contrasena de acceso" autofocus>
    <button type="submit" class="btn">INGRESAR</button>
    {% if error %}<div class="error">Contrasena incorrecta</div>{% endif %}
  </form>
</div>
</body>
</html>
"""

# ==================== RUTAS WEB ====================
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "Voltinn.2026")
API_KEY = os.environ.get("API_KEY", "innvolt-riofrio-2026")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("pass") == PANEL_PASSWORD:
            session["auth"] = True
            return redirect("/panel")
        return render_template_string(LOGIN_HTML, error=True)
    if session.get("auth"):
        return redirect("/panel")
    return render_template_string(LOGIN_HTML, error=False)

@app.route("/panel")
def panel():
    if not session.get("auth"):
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT numero FROM numeros ORDER BY creado_en ASC")
    numeros = cur.fetchall()
    cur.execute("SELECT tipo, numero, resultado, fecha FROM historial ORDER BY fecha DESC LIMIT 20")
    historial = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(PANEL_HTML, numeros=numeros, historial=historial, api_key=API_KEY)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ==================== API PARA ESP32 ====================
def check_api_key():
    return request.headers.get("X-API-Key") == API_KEY

@app.route("/api/numeros", methods=["GET"])
def api_numeros():
    if not check_api_key():
        return jsonify({"error": "no autorizado"}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT numero FROM numeros")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"numeros": [r["numero"] for r in rows]})

@app.route("/api/numeros/add", methods=["POST"])
def api_add():
    if not check_api_key():
        return jsonify({"error": "no autorizado"}), 403
    data = request.get_json()
    numero = data.get("numero", "").strip()
    if not numero:
        return jsonify({"ok": False, "error": "numero vacio"})
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO numeros (numero) VALUES (%s) ON CONFLICT DO NOTHING", (numero,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/numeros/del", methods=["POST"])
def api_del():
    if not check_api_key():
        return jsonify({"error": "no autorizado"}), 403
    data = request.get_json()
    numero = data.get("numero", "").strip()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM numeros WHERE numero = %s", (numero,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/abrir", methods=["POST"])
def api_abrir():
    if not check_api_key():
        return jsonify({"error": "no autorizado"}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO comandos (comando) VALUES ('abrir')")
    cur.execute("INSERT INTO historial (tipo, numero, resultado) VALUES ('remoto', 'panel-web', 'autorizado')")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/comando", methods=["GET"])
def api_comando():
    if not check_api_key():
        return jsonify({"error": "no autorizado"}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, comando FROM comandos WHERE ejecutado = FALSE ORDER BY creado_en ASC LIMIT 1")
    cmd = cur.fetchone()
    if cmd:
        cur.execute("UPDATE comandos SET ejecutado = TRUE WHERE id = %s", (cmd["id"],))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"comando": cmd["comando"]})
    cur.close()
    conn.close()
    return jsonify({"comando": None})

@app.route("/api/historial/add", methods=["POST"])
def api_historial():
    if not check_api_key():
        return jsonify({"error": "no autorizado"}), 403
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO historial (tipo, numero, resultado) VALUES (%s, %s, %s)",
        (data.get("tipo"), data.get("numero"), data.get("resultado"))
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

# ==================== INICIO ====================
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print("Error init_db:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
