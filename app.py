import streamlit as st
import sqlite3
import pandas as pd
import urllib.parse
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURACIÓN DE CREDENCIALES ---
EMAIL_REMITENTE = "farmahclub@gmail.com"
EMAIL_PASSWORD = "efsc gffl hjww ylhi"  # <--- COLOCA AQUÍ TUS 16 LETRAS DE GOOGLE

# --- 2. FUNCIONES DE BASE DE DATOS ---
def crear_conexion():
    return sqlite3.connect('clinica_privada.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (id INTEGER PRIMARY KEY, nombre TEXT, email TEXT UNIQUE, 
                  password TEXT, medicacion TEXT, telefono TEXT, 
                  fecha_recogida TEXT, confirmado INTEGER)''')
    
    c.execute("SELECT * FROM pacientes WHERE email='admin@clinica.com'")
    if not c.fetchone():
        c.execute("INSERT INTO pacientes (nombre, email, password, medicacion, telefono, confirmado) VALUES ('Admin Farmacia', 'admin@clinica.com', 'admin77', 'GESTION', '000', 0)")
    conn.commit()
    conn.close()

# --- 3. FUNCIÓN DE ENVÍO DE EMAIL (MÁXIMA PRIVACIDAD) ---
def enviar_email_privado(destinatario, nombre_completo, fecha):
    try:
        nombre_pila = nombre_completo.split()[0]
        url_acceso = "http://localhost:8501" # Cambiará al subir a GitHub
        
        cuerpo = f"""
        Hola {nombre_pila},
        
        Confirma tu asistencia a la recogida de medicación en el centro asignado.
        
        📅 Fecha: {fecha}
        
        🔗 Enlace de acceso: {url_acceso}
        
        Atentamente,
        Tu Farmacia.
        """
        msg = MIMEText(cuerpo)
        msg['Subject'] = f'Aviso de recogida para {nombre_pila}'
        msg['From'] = EMAIL_REMITENTE
        msg['To'] = destinatario

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
            server.sendmail(EMAIL_REMITENTE, destinatario, msg.as_string())
        return True
    except:
        return False

# --- 4. INTERFAZ ---
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
            conn = crear_conexion()
            res = pd.read_sql(f"SELECT * FROM pacientes WHERE email='{u}' AND password='{p}'", conn)
            conn.close()
            if not res.empty:
                st.session_state['auth'] = True
                st.session_state['user'] = res.iloc[0]
                st.rerun()
            else: st.error("Credenciales incorrectas")

else:
    user = st.session_state['user']
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['auth'] = False
        st.rerun()

    # --- PANEL ADMINISTRADOR ---
    if user['email'] == 'admin@clinica.com':
        st.title("💊 Panel de Control Farmacéutico")
        
        tab1, tab2 = st.tabs(["📊 Envíos y Gestión", "👤 Alta de Paciente"])
        
        with tab1:
            conn = crear_conexion()
            df = pd.read_sql("SELECT * FROM pacientes WHERE email != 'admin@clinica.com'", conn)
            conn.close()
            
            df['Estado'] = df['confirmado'].apply(lambda x: "🟢 Confirmado" if x == 1 else "🔴 Pendiente")
            
            st.write("Selecciona pacientes en la tabla:")
            event = st.dataframe(
                df[['id', 'nombre', 'email', 'telefono', 'Estado']], 
                use_container_width=True, 
                hide_index=True, 
                on_select="rerun", 
                selection_mode="multi-row"
            )

            indices = event.selection.rows
            if indices:
                pacientes_sel = df.iloc[indices]
                f_cita = st.date_input("Fecha de recogida:", format="DD/MM/YYYY")
                
                col_mail, col_wa = st.columns(2)
                
                with col_mail:
                    if st.button("📧 ENVIAR AVISOS POR EMAIL"):
                        for idx, p in pacientes_sel.iterrows():
                            conn = crear_conexion()
                            conn.execute("UPDATE pacientes SET fecha_recogida = ?, confirmado = 0 WHERE id = ?", (f_cita.strftime("%d/%m/%Y"), int(p['id'])))
                            conn.commit()
                            conn.close()
                            enviar_email_privado(p['email'], p['nombre'], f_cita.strftime("%d/%m/%Y"))
                        st.success(f"✅ Emails enviados.")

                with col_wa:
                    st.write("📲 **Enlaces directos WhatsApp:**")
                    url_acceso = "http://localhost:8501"
                    for idx, p in pacientes_sel.iterrows():
                        nombre_pila = p['nombre'].split()[0]
                        texto_wa = f"Hola {nombre_pila}, confirma tu asistencia a la recogida de medicacion en el centro asignado para el dia {f_cita.strftime('%d/%m/%Y')}. Accede aqui: {url_acceso}"
                        link_wa = f"https://wa.me/{p['telefono']}?text={urllib.parse.quote(texto_wa)}"
                        st.markdown(f"👉 [Enviar a {nombre_pila}]({link_wa})")

        with tab2:
            with st.form("alta"):
                st.subheader("Registrar nuevo paciente")
                c1, c2 = st.columns(2)
                n = c1.text_input("Nombre y Apellidos")
                e = c2.text_input("Email")
                t = c1.text_input("Teléfono (Prefijo + número)")
                p = c2.text_input("Contraseña acceso")
                m = st.text_area("Medicación asignada")
                if st.form_submit_button("Registrar"):
                    conn = crear_conexion()
                    conn.execute("INSERT INTO pacientes (nombre, email, telefono, password, medicacion, confirmado) VALUES (?,?,?,?,?,0)", (n,e,t,p,m))
                    conn.commit()
                    conn.close()
                    st.success("Registrado correctamente.")

    # --- PANEL PACIENTE ---
    else:
        st.title(f"👋 Hola, {user['nombre']}")
        st.markdown(f"""
            <div style="background-color: #f0f7ff; padding: 25px; border-radius: 15px; border-left: 10px solid #007bff;">
                <h2 style="color: #007bff;">📋 Tu Medicación</h2>
                <p style="font-size: 1.3em;"><b>Fármaco:</b> {user['medicacion']}</p>
                <p><b>Fecha de recogida:</b> {user['fecha_recogida'] if user['fecha_recogida'] else 'Pendiente'}</p>
            </div>
        """, unsafe_allow_html=True)
        
        if user['confirmado'] == 0:
            if st.button("✅ Confirmar Asistencia", use_container_width=True):
                conn = crear_conexion()
                conn.execute("UPDATE pacientes SET confirmado = 1 WHERE id = ?", (int(user['id']),))
                conn.commit()
                conn.close()
                st.balloons()
                st.rerun()