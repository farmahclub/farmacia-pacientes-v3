import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURACIÓN BASE DE DATOS ---
def crear_conexion():
    return sqlite3.connect('clinica_privada.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (dni TEXT PRIMARY KEY, nombre TEXT, email TEXT, password TEXT, medicacion TEXT, estado TEXT, fecha_confirmacion TEXT)''')
    conn.commit()
    conn.close()

# --- FUNCIONES DE GESTIÓN ---
def registrar_paciente(dni, nombre, email, password, medicacion):
    conn = crear_conexion()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO pacientes (dni, nombre, email, password, medicacion, estado) VALUES (?,?,?,?,?,?)",
                  (dni, nombre, email, password, medicacion, "Pendiente"))
        conn.commit()
        st.success(f"✅ Paciente {nombre} registrado con éxito.")
    except:
        st.error("❌ El DNI ya existe.")
    conn.close()

def eliminar_paciente(dni):
    conn = crear_conexion()
    c = conn.cursor()
    c.execute("DELETE FROM pacientes WHERE dni=?", (dni,))
    conn.commit()
    conn.close()
    st.rerun()

# --- INTERFAZ ---
st.set_page_config(page_title="Gestor Farmacia", page_icon="💊", layout="wide")
inicializar_db()

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Acceso Seguro")
    u = st.text_input("Email")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if u == "admin@clinica.com" and p == "admin77":
            st.session_state['auth'] = True
            st.rerun()
else:
    st.sidebar.title("Panel de Farmacia")
    menu = st.sidebar.radio("Ir a:", ["📊 Control de Envíos", "➕ Alta de Paciente", "⚙️ Gestión de Base de Datos"])

    if menu == "📊 Control de Envíos":
        st.header("Seguimiento de Recogidas")
        conn = crear_conexion()
        df = pd.read_sql("SELECT * FROM pacientes", conn)
        conn.close()
        if df.empty:
            st.info("No hay pacientes. Ve a 'Alta de Paciente'.")
        else:
            st.table(df[['nombre', 'dni', 'medicacion', 'estado']])

    elif menu == "➕ Alta de Paciente":
        st.header("Nuevo Registro")
        with st.form("nuevo_p"):
            d = st.text_input("DNI")
            n = st.text_input("Nombre")
            e = st.text_input("Email")
            passw = st.text_input("Clave para el paciente")
            med = st.text_input("Medicación")
            if st.form_submit_button("Guardar"):
                registrar_paciente(d, n, e, passw, med)

    elif menu == "⚙️ Gestión de Base de Datos":
        st.header("Administrar Pacientes")
        conn = crear_conexion()
        df = pd.read_sql("SELECT dni, nombre FROM pacientes", conn)
        conn.close()
        for i, row in df.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"{row['nombre']} ({row['dni']})")
            if col2.button("Eliminar", key=row['dni']):
                eliminar_paciente(row['dni'])
