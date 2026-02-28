import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import urllib.parse
from io import BytesIO

# --- 1. CONFIGURACIÓN BASE DE DATOS (VERSIÓN FINAL) ---
def crear_conexion():
    return sqlite3.connect('farmacia_final_v4.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (num_historia TEXT PRIMARY KEY, nombre TEXT, email TEXT, telefono TEXT, 
                  password TEXT, medicacion TEXT, estado TEXT, fecha_confirmacion TEXT)''')
    conn.commit()
    conn.close()

# --- 2. FUNCIÓN DE ENVÍO DE EMAIL ---
def enviar_email(destinatario, nombre, url_app):
    try:
        remitente = st.secrets["EMAIL_REMITENTE"]
        pwd = st.secrets["EMAIL_PASSWORD"]
        msg = MIMEText(f"Hola {nombre}, su medicación está lista.\nConfirme su recogida haciendo clic aquí: {url_app}")
        msg['Subject'] = "AVISO: Medicación Lista - Farmacia"
        msg['From'] = remitente
        msg['To'] = destinatario
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remitente, pwd)
            server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except: return False

# --- 3. INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Gestión Farmacia Pro", layout="wide", page_icon="💊")
inicializar_db()

# --- IMPORTANTE: SUSTITUYE ESTA URL POR LA QUE TE DA STREAMLIT ---
URL_APP = "https://farmacia-pacientes-v3.streamlit.app/" 

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

# --- PANTALLA DE ACCESO DINÁMICA ---
if not st.session_state['auth']:
    st.title("🔐 Acceso Seguro Farmacia")
    
    # --- ANIMACIÓN DINÁMICA DEL CAMIÓN DE REPARTO ---
    st.markdown("""
    <div style="width: 100%; height: 200px; background-color: #f0f8ff; border-radius: 15px; overflow: hidden; position: relative; display: flex; align-items: center; justify-content: center; border: 2px solid #e0f0ff;">
        <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 80px; background: linear-gradient(0deg, #d3d3d3 0%, rgba(211,211,211,0) 100%);"></div>
        
        <div style="position: absolute; bottom: 15px; animation: moverCamion 8s infinite linear;">
            <div style="font-size: 80px; position: relative;">
                🚚
                <div style="position: absolute; left: -25px; bottom: 5px; animation: humo 1s infinite;">
                    <span style="font-size: 20px; color: gray; opacity: 0.5;">💨</span>
                </div>
            </div>
        </div>
        
        <div style="z-index: 1; text-align: center; color: #004d99; font-weight: bold; font-family: sans-serif;">
            <div style="font-size: 28px;">SU MEDICACIÓN ESTÁ EN CAMINO</div>
            <div style="font-size: 16px; opacity: 0.8;">Acceda para confirmar su recogida</div>
        </div>
    </div>
    
    <style>
    @keyframes moverCamion {
        0% { left: -150px; transform: scaleX(1); }
        45% { left: calc(100% - 150px); transform: scaleX(1); }
        50% { left: calc(100% - 150px); transform: scaleX(-1); }
        95% { left: -150px; transform: scaleX(-1); }
        100% { left: -150px; transform: scaleX(1); }
    }
    @keyframes humo {
        0% { transform: translate(0,0) scale(1); opacity: 0.5; }
        100% { transform: translate(-20px, -10px) scale(1.5); opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    tab1, tab2 = st.tabs(["🔒 Administración", "👤 Pacientes"])
    
    with tab1:
        u = st.text_input("Usuario Admin")
        p = st.text_input("Clave Admin", type="password")
        if st.button("Entrar como Admin"):
            if u == "admin@clinica.com" and p == "admin77":
                st.session_state['auth'] = "admin"
                st.rerun()
            else: st.error("Credenciales incorrectas")
    
    with tab2:
        hc_pac = st.text_input("Nº Historia Clínica")
        pw_pac = st.text_input("Contraseña Paciente", type="password")
        if st.button("Acceder mis datos"):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("SELECT * FROM pacientes WHERE num_historia=? AND password=?", (hc_pac, pw_pac))
            paciente = c.fetchone()
            conn.close()
            if paciente:
                st.session_state['auth'] = "paciente"
                st.session_state['user_data'] = paciente
                st.rerun()
            else: st.error("Datos incorrectos")

# --- VISTA ADMINISTRADOR ---
elif st.session_state['auth'] == "admin":
    st.sidebar.title("Panel de Control")
    menu = st.sidebar.radio("Ir a:", ["📊 Seguimiento", "➕ Alta Paciente", "📥 Exportar Excel", "🚪 Salir"])

    if menu == "📊 Seguimiento":
        st.header("Control de Recogidas")
        conn = crear_conexion(); df = pd.read_sql("SELECT * FROM pacientes", conn); conn.close()
        if df.empty: st.info("No hay pacientes registrados.")
        else:
            for i, row in df.iterrows():
                c1, c2, c3, c4 = st.columns([2,1,1,1])
                c1.write(f"**{row['nombre']}** ({row['num_historia']})")
                estado_color = "🟢" if row['estado'] == "CONFIRMADO" else "🟡"
                c2.write(f"{estado_color} {row['estado']}")
                
                if c3.button("📧 Email", key=f"e_{row['num_historia']}"):
                    if enviar_email(row['email'], row['nombre'], URL_APP): 
                        st.success("Enviado")
                
                msg_wa = urllib.parse.quote(f"Hola {row['nombre']}, su medicación está lista. Confirme aquí: {URL_APP}")
                c4.markdown(f"[![WA](https://img.shields.io/badge/WhatsApp-25D366?style=flat&logo=whatsapp&logoColor=white)](https://wa.me/{row['telefono']}?text={msg_wa})")

    elif menu == "➕ Alta Paciente":
        with st.form("alta", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            hc = col_a.text_input("Nº Historia")
            nom = col_b.text_input("Nombre Completo")
            em = col_a.text_input("Email")
            tel = col_b.text_input("Teléfono (ej: 34600000000)")
            med = col_a.text_input("Medicación")
            pwd = col_b.text_input("Clave para el paciente")
            if st.form_submit_button("Guardar Paciente"):
                conn = crear_conexion(); c = conn.cursor()
                try:
                    c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?)",(hc,nom,em,tel,pwd,med,"Pendiente",""))
                    conn.commit(); conn.close(); st.success(f"Paciente {nom} registrado correctamente")
                except:
                    st.error("Error: Historia Clínica ya existe.")
                    conn.close()

    elif menu == "📥 Exportar Excel":
        conn = crear_conexion(); df = pd.read_sql("SELECT * FROM pacientes", conn); conn.close()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Descargar Tabla de Pacientes", output.getvalue(), "listado_pacientes.xlsx")

    if menu == "🚪 Salir":
        st.session_state['auth'] = False; st.rerun()

# --- VISTA PACIENTE ---
elif st.session_state['auth'] == "paciente":
    p = st.session_state['user_data']
    st.title(f"👋 Bienvenido/a, {p[1]}")
    st.markdown(f"""
    <div style="background-color: #e1f5fe; padding: 20px; border-radius: 10px; border-left: 5px solid #01579b;">
        <h4>Información de su pedido:</h4>
        <p><b>Medicación:</b> {p[5]}</p>
        <p><b>Estado actual:</b> {p[6]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    if st.button("✅ CONFIRMAR QUE PASARÉ A RECOGERLA"):
        conn = crear_conexion(); c = conn.cursor()
        c.execute("UPDATE pacientes SET estado='CONFIRMADO' WHERE num_historia=?", (p[0],))
        conn.commit(); conn.close()
        st.balloons()
        st.success("¡Confirmación registrada! El personal de farmacia ya ha sido avisado.")
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state['auth'] = False; st.rerun()
