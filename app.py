import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import urllib.parse

# --- 1. CONFIGURACIÓN Y BASE DE DATOS ---
def crear_conexion():
    return sqlite3.connect('clinica_privada.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    # Cambiado DNI por num_historia
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (num_historia TEXT PRIMARY KEY, nombre TEXT, email TEXT, telefono TEXT, password TEXT, medicacion TEXT, estado TEXT, fecha_confirmacion TEXT)''')
    conn.commit()
    conn.close()

# --- 2. FUNCIONES DE GESTIÓN ---
def eliminar_paciente(num_historia):
    conn = crear_conexion()
    c = conn.cursor()
    c.execute("DELETE FROM pacientes WHERE num_historia=?", (num_historia,))
    conn.commit()
    conn.close()
    st.rerun()

def actualizar_paciente(num_historia, nuevo_nombre, nueva_med, nuevo_tel):
    conn = crear_conexion()
    c = conn.cursor()
    c.execute("UPDATE pacientes SET nombre=?, medicacion=?, telefono=? WHERE num_historia=?", (nuevo_nombre, nueva_med, nuevo_tel, num_historia))
    conn.commit()
    conn.close()
    st.success("Datos actualizados")

# --- 3. FUNCIONES DE ENVÍO ---
def enviar_email(destinatario, nombre, fecha):
    try:
        remitente = st.secrets["EMAIL_REMITENTE"]
        password = st.secrets["EMAIL_PASSWORD"]
        url_app = "https://https://rlgempgxpbcskamagrk83v.streamlit.app/"
        
        msg = MIMEText(f"Hola {nombre}, tu medicación está lista para recoger el {fecha}.\nConfirma aquí: {url_app}")
        msg['Subject'] = "Medicación Lista - Farmacia"
        msg['From'] = remitente
        msg['To'] = destinatario

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remitente, password)
            server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except:
        return False

# --- 4. INTERFAZ ---
st.set_page_config(page_title="Gestor Farmacia Pro", page_icon="💊", layout="wide")
inicializar_db()

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Acceso Farmacia")
    u = st.text_input("Usuario")
    p = st.text_input("Clave", type="password")
    if st.button("Entrar"):
        if u == "admin@clinica.com" and p == "admin77":
            st.session_state['auth'] = True
            st.rerun()
else:
    st.sidebar.title("Menú Principal")
    menu = st.sidebar.radio("Ir a:", ["📊 Control y Envíos", "➕ Nuevo Paciente", "⚙️ Gestión y Modificación"])

    if menu == "📊 Control y Envíos":
        st.header("Seguimiento de Recogidas")
        conn = crear_conexion()
        df = pd.read_sql("SELECT * FROM pacientes", conn)
        conn.close()
        
        if df.empty:
            st.info("Base de datos vacía.")
        else:
            for i, row in df.iterrows():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                col1.write(f"**{row['nombre']}** (H.C: {row['num_historia']})")
                col2.write(f"Estado: {row['estado']}")
                
                # BOTÓN EMAIL
                if col3.button("📧 Email", key=f"em_{row['num_historia']}"):
                    if enviar_email(row['email'], row['nombre'], "mañana"):
                        st.success("Email enviado")
                
                # BOTÓN WHATSAPP
                texto_wa = urllib.parse.quote(f"Hola {row['nombre']}, tu medicación está lista. Confirma aquí: https://rlgempgxpbckskamagrk83v.streamlit.app/")
                url_wa = f"https://wa.me/{row['telefono']}?text={texto_wa}"
                col4.markdown(f"[![WA](https://img.shields.io/badge/WhatsApp-25D366?style=flat&logo=whatsapp&logoColor=white)]({url_wa})")

    elif menu == "➕ Nuevo Paciente":
        st.header("Registro de Historia Clínica")
        with st.form("alta"):
            hc = st.text_input("Número de Historia Clínica")
            nom = st.text_input("Nombre Completo")
            em = st.text_input("Email")
            tel = st.text_input("Teléfono (con 34 delante)")
            med = st.text_input("Medicación")
            pwd = st.text_input("Contraseña para el paciente")
            if st.form_submit_button("Guardar Paciente"):
                conn = crear_conexion()
                c = conn.cursor()
                c.execute("INSERT INTO pacientes (num_historia, nombre, email, telefono, password, medicacion, estado) VALUES (?,?,?,?,?,?,?)",
                          (hc, nom, em, tel, pwd, med, "Pendiente"))
                conn.commit()
                conn.close()
                st.success("Registrado")

    elif menu == "⚙️ Gestión y Modificación":
        st.header("Administrar o Modificar Pacientes")
        conn = crear_conexion()
        df = pd.read_sql("SELECT * FROM pacientes", conn)
        conn.close()
        
        for i, row in df.iterrows():
            with st.expander(f"Modificar: {row['nombre']} (HC: {row['num_historia']})"):
                nuevo_n = st.text_input("Nombre", value=row['nombre'], key=f"n_{row['num_historia']}")
                nueva_m = st.text_input("Medicación", value=row['medicacion'], key=f"m_{row['num_historia']}")
                nuevo_t = st.text_input("Teléfono", value=row['telefono'], key=f"t_{row['num_historia']}")
                
                c1, c2 = st.columns(2)
                if c1.button("Guardar Cambios", key=f"save_{row['num_historia']}"):
                    actualizar_paciente(row['num_historia'], nuevo_n, nueva_m, nuevo_t)
                if c2.button("🗑️ Eliminar Definitivamente", key=f"del_{row['num_historia']}"):
                    eliminar_paciente(row['num_historia'])

