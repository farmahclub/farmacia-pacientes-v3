import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURACIÓN Y BASE DE DATOS ---
def crear_conexion():
    return sqlite3.connect('clinica_privada.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (dni TEXT PRIMARY KEY, nombre TEXT, email TEXT, password TEXT, medicacion TEXT, estado TEXT, fecha_confirmacion TEXT)''')
    conn.commit()
    conn.close()

# Función nueva para eliminar
def eliminar_paciente(dni):
    conn = crear_conexion()
    c = conn.cursor()
    c.execute("DELETE FROM pacientes WHERE dni=?", (dni,))
    conn.commit()
    conn.close()

# --- 2. INTERFAZ DE ADMINISTRADOR ---
def panel_administrador():
    st.sidebar.title("Panel de Farmacia")
    menu = st.sidebar.radio("Ir a:", ["📊 Control de Envíos", "➕ Alta de Paciente", "⚙️ Gestión de Base de Datos"])

    if menu == "📊 Control de Envíos":
        st.header("Seguimiento de Recogidas")
        # Aquí va tu tabla actual de envíos...

    elif menu == "➕ Alta de Paciente":
        st.header("Registrar Nuevo Paciente")
        # Aquí va tu formulario de alta...

    elif menu == "⚙️ Gestión de Base de Datos":
        st.header("🛠️ Administración de Pacientes")
        conn = crear_conexion()
        df = pd.read_sql("SELECT dni, nombre, email, medicacion FROM pacientes", conn)
        conn.close()

        if df.empty:
            st.info("No hay pacientes registrados aún.")
        else:
            for i, row in df.iterrows():
                with st.expander(f"👤 {row['nombre']} (DNI: {row['dni']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Email:** {row['email']}")
                        st.write(f"**Medicación:** {row['medicacion']}")
                    with col2:
                        if st.button(f"🗑️ Eliminar a {row['nombre']}", key=f"del_{row['dni']}"):
                            eliminar_paciente(row['dni'])
                            st.success(f"Paciente {row['nombre']} eliminado.")
                            st.rerun()

# --- 3. LÓGICA DE LOGIN ---
st.set_page_config(page_title="Gestor Farmacéutico", page_icon="💊", layout="wide")
inicializar_db()

if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Acceso Seguro")
    with st.form("login"):
        u = st.text_input("Email")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if u == "admin@clinica.com" and p == "admin77":
                st.session_state['auth'] = True
                st.session_state['user_role'] = "admin"
                st.rerun()
            # ... lógica para login de pacientes ...
else:
    panel_administrador()
