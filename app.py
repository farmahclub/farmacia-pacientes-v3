import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import urllib.request
import json
from io import BytesIO

# --- 1. CONFIGURACIÓN BASE DE DATOS (Mantenemos v6 con CN) ---
def crear_conexion():
    return sqlite3.connect('farmacia_v6.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (num_historia TEXT PRIMARY KEY, nombre TEXT, primer_apellido TEXT, email TEXT, 
                  telefono TEXT, password TEXT, medicacion TEXT, codigo_nacional TEXT, estado TEXT)''')
    conn.commit()
    conn.close()

# --- 2. FUNCIONES DE APOYO ---
def enviar_email(destinatario, nombre, url_app):
    try:
        remitente = st.secrets["EMAIL_REMITENTE"]
        pwd = st.secrets["EMAIL_PASSWORD"]
        msg = MIMEText(f"Hola {nombre}, su medicación está lista.\nAcceda con su apellido aquí: {url_app}")
        msg['Subject'] = "AVISO: Farmacia - Medicación Lista"
        msg['From'] = remitente
        msg['To'] = destinatario
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remitente, pwd)
            server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except: return False

def obtener_enlace_cima(cn, nombre_med):
    # Si no hay CN, busca por el nombre en la lupa de CIMA
    if not cn:
        med_encode = urllib.parse.quote(str(nombre_med))
        return f"https://cima.aemps.es/cima/publico/lista.html?raZonSocial={med_encode}"
    
    try:
        # Magia: Conectamos a la API del Ministerio para sacar el enlace DIRECTO al prospecto
        url_api = f"https://cima.aemps.es/cima/rest/medicamento?cn={cn}"
        req = urllib.request.Request(url_api, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                nregistro = data.get('nregistro')
                if nregistro:
                    # Este es el enlace exacto al texto del prospecto
                    return f"https://cima.aemps.es/cima/dochtml/p/{nregistro}/Prospecto.html"
    except Exception as e:
        pass # Si falla (ej. CIMA está caído), salta a la búsqueda normal
    
    return f"https://cima.aemps.es/cima/publico/lista.html?cn={cn}"

# --- 3. INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Farmacia Clientes", layout="wide", page_icon="💊")
inicializar_db()

# URL REAL DE TU APP
URL_APP = "https://tdyxipgchc5jegixrwkbp9.streamlit.app/" 

if 'auth' not in st.session_state: st.session_state['auth'] = False

# --- MARCA DE AGUA FLOTANTE ---
st.markdown("""
<style>
.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: transparent;
color: rgba(150, 150, 150, 0.4);
text-align: right;
padding-right: 20px;
font-size: 12px;
z-index: 100;
}
</style>
<div class="footer">® By Juanma - Todos los derechos reservados</div>
""", unsafe_allow_html=True)

# --- PANTALLA DE ACCESO ---
if not st.session_state['auth']:
    st.markdown("""
<div style="width: 100%; height: 220px; background-color: #f0f8ff; border-radius: 15px; overflow: hidden; position: relative; display: flex; align-items: center; justify-content: center; border: 2px solid #e0f0ff;">
<div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 60px; background: #f0f0f0;"></div>
<div style="position: absolute; bottom: 20px; animation: moverAdelante 8s infinite linear;">
<div style="text-align: center;">
<div style="font-size: 30px; margin-bottom: -10px;">💊</div>
<div style="font-size: 70px; transform: scaleX(-1); display: inline-block;">🚚</div>
</div>
</div>
<div style="z-index: 1; text-align: center; color: #004d99; font-family: Arial, sans-serif;">
<h1 style="margin:0; letter-spacing: 2px;">GESTIÓN DE FARMACIA</h1>
<p style="font-size: 18px; font-weight: bold;">Acceso Exclusivo para Pacientes</p>
</div>
</div>
<style>
@keyframes moverAdelante {
0% { left: -150px; }
100% { left: 100%; }
}
</style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.write("---")
        ape_login = st.text_input("Introduzca su Primer Apellido")
        pass_login = st.text_input("Introduzca su Contraseña", type="password")
        
        if st.button("🔓 ACCEDER A MIS DATOS", use_container_width=True):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("SELECT * FROM pacientes WHERE LOWER(primer_apellido)=LOWER(?) AND password=?", (ape_login, pass_login))
            p = c.fetchone()
            conn.close()
            if p:
                st.session_state['auth'] = "paciente"
                st.session_state['user_data'] = p
                st.rerun()
            else: st.error("Datos de acceso incorrectos.")

    st.write("")
    with st.expander("🛠️"):
        u_admin = st.text_input("Admin User")
        p_admin = st.text_input("Admin Pass", type="password")
        if st.button("Login Admin"):
            if u_admin == "admin@clinica.com" and p_admin == "admin77":
                st.session_state['auth'] = "admin"
                st.rerun()

# --- VISTA ADMINISTRADOR ---
elif st.session_state['auth'] == "admin":
    st.sidebar.header("Panel de Gestión")
    menu = st.sidebar.radio("Navegación", ["📊 Dashboard & Avisos", "🗂️ Editor Base de Datos", "📤 Importar Excel", "➕ Alta Manual", "🚪 Salir"])

    if menu == "📊 Dashboard & Avisos":
        st.header("Seguimiento de Recogidas")
        conn = crear_conexion(); df = pd.read_sql("SELECT * FROM pacientes", conn); conn.close()
        
        if df.empty:
            st.warning("No hay pacientes en la base de datos.")
        else:
            total = len(df)
            confirmados = len(df[df['estado'] == 'CONFIRMADO'])
            pendientes = total - confirmados
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("👥 Total Pacientes", total)
            col_m2.metric("⏳ Pendientes", pendientes)
            col_m3.metric("✅ Confirmados", confirmados)
            st.divider()

            for i, r in df.iterrows():
                with st.container():
                    # Añadimos espacio para el botón de "Nuevo Pedido"
                    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1.5])
                    c1.write(f"👤 **{r['nombre']} {r['primer_apellido']}**")
                    color = "🟢" if r['estado'] == "CONFIRMADO" else "🟡"
                    c2.write(f"{color} {r['estado']}")
                    
                    if c3.button("📧 Email", key=f"e_{r['num_historia']}"):
                        if enviar_email(r['email'], r['nombre'], URL_APP): st.success("OK")
                    
                    msg_wa = urllib.parse.quote(f"Hola {r['nombre']}, su medicación está lista. Acceda aquí: {URL_APP}")
                    c4.markdown(f"[📲 WhatsApp](https://wa.me/{r['telefono']}?text={msg_wa})")
                    
                    # BOTÓN DE RESTABLECER (Solo sale si ya han recogido el pedido)
                    if r['estado'] == 'CONFIRMADO':
                        if c5.button("🔄 Nuevo Pedido", key=f"r_{r['num_historia']}"):
                            conn = crear_conexion(); c = conn.cursor()
                            c.execute("UPDATE pacientes SET estado='Pendiente' WHERE num_historia=?", (r['num_historia'],))
                            conn.commit(); conn.close()
                            st.rerun()
                    
                    st.divider()

    elif menu == "🗂️ Editor Base de Datos":
        st.header("Editor Interactivo de Pacientes")
        st.info("💡 Haz doble clic en cualquier celda para editar. Selecciona filas a la izquierda y presiona 'Suprimir' para borrar.")
        
        conn = crear_conexion()
        df = pd.read_sql("SELECT * FROM pacientes", conn)
        conn.close()

        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

        if st.button("💾 Guardar Cambios Permanentes"):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("DELETE FROM pacientes")
            conn.commit()
            edited_df.to_sql('pacientes', conn, if_exists='append', index=False)
            conn.close()
            st.success("¡Base de datos actualizada correctamente!")

    elif menu == "📤 Importar Excel":
        st.subheader("Carga Masiva de Pacientes")
        st.write("El Excel debe tener: `num_historia`, `nombre`, `primer_apellido`, `email`, `telefono`, `password`, `medicacion`, `codigo_nacional`.")
        file = st.file_uploader("Seleccionar archivo Excel", type=['xlsx'])
        if file:
            df_excel = pd.read_excel(file)
            st.write("Vista previa:")
            st.dataframe(df_excel.head())
            if st.button("🚀 Confirmar Importación"):
                conn = crear_conexion()
                df_excel['estado'] = "Pendiente"
                df_excel.to_sql('pacientes', conn, if_exists='append', index=False)
                conn.close()
                st.success("¡Importación finalizada!")

    elif menu == "➕ Alta Manual":
        # Activar el "clear_on_submit" para que las celdas se vacíen al guardar
        with st.form("registro_manual", clear_on_submit=True):
            h = st.text_input("Nº Historia / DNI")
            n = st.text_input("Nombre")
            a = st.text_input("Primer Apellido")
            e = st.text_input("Email")
            t = st.text_input("Teléfono (34...)")
            p = st.text_input("Clave Inicial")
            m = st.text_input("Medicación Asignada")
            cn = st.text_input("Código Nacional (CN - Opcional, 6 dígitos)")
            
            if st.form_submit_button("Registrar Nuevo Paciente"):
                if h and n: # Comprobación básica de que haya escrito algo
                    conn = crear_conexion(); c = conn.cursor()
                    try:
                        c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?)", (h,n,a,e,t,p,m,cn,"Pendiente"))
                        conn.commit()
                        # Quitamos el st.rerun() para permitir que el formulario se limpie visualmente
                        st.success(f"¡Paciente {n} {a} registrado! El formulario se ha vaciado para el siguiente.")
                    except: 
                        st.error("Error: El ID / Nº Historia ya existe en el sistema.")
                    finally: 
                        conn.close()
                else:
                    st.warning("Por favor, introduzca al menos el ID y el Nombre.")

    if menu == "🚪 Salir": st.session_state['auth'] = False; st.rerun()

# --- VISTA PACIENTE ---
elif st.session_state['auth'] == "paciente":
    p = st.session_state['user_data']
    st.title(f"👋 Bienvenido/a, {p[1]} {p[2]}")
    
    # DATOS DEL PACIENTE
    medicacion = p[6]
    codigo_nacional = p[7]
    estado_actual = p[8]
    
    # NUEVA CONEXIÓN INTELIGENTE A CIMA
    enlace_cima = obtener_enlace_cima(codigo_nacional, medicacion)
    
    # Construcción del evento para Google Calendar
    titulo_cal = urllib.parse.quote("Recogida de Medicación - Farmacia")
    detalles_cal = urllib.parse.quote(f"Recuerda ir a la farmacia a recoger: {medicacion}.\n¡No olvides llevar tu QR de la App!")
    enlace_cal = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo_cal}&details={detalles_cal}"

    st.markdown(f"""
<div style="background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
<h3 style="color: #004d99;">📦 Su Medicación:</h3>
<p style="font-size: 20px; font-weight: bold;">{medicacion}</p>
<p>Estado actual: <b>{estado_actual}</b></p>
<hr>
<div style="display: flex; gap: 10px; flex-wrap: wrap;">
    <a href="{enlace_cima}" target="_blank" style="text-decoration: none;">
        <button style="background-color: #008CBA; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
            📄 Leer prospecto exacto en CIMA
        </button>
    </a>
    <a href="{enlace_cal}" target="_blank" style="text-decoration: none;">
        <button style="background-color: #FFA500; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
            📅 Añadir recordatorio al Calendario
        </button>
    </a>
</div>
</div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # LÓGICA DEL QR Y CONFIRMACIÓN
    if estado_actual != 'CONFIRMADO':
        if st.button("✅ CONFIRMAR QUE PASARÉ A RECOGERLA", use_container_width=True):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("UPDATE pacientes SET estado='CONFIRMADO' WHERE num_historia=?", (p[0],))
            conn.commit(); conn.close()
            
            # Actualizamos la memoria temporal para mostrar el QR
            lista_p = list(p)
            lista_p[8] = 'CONFIRMADO'
            st.session_state['user_data'] = tuple(lista_p)
            
            st.balloons()
            st.rerun()
            
    else:
        st.success("✅ Recogida confirmada. Por favor, muestra este código QR en el mostrador de la farmacia:")
        # Generador de QR dinámico a través de API
        qr_data = urllib.parse.quote(f"Paciente:{p[1]} {p[2]} | ID:{p[0]} | Med:{p[6]}")
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_data}&color=004d99"
        
        col_qr1, col_qr2, col_qr3 = st.columns([1,2,1])
        with col_qr2:
            st.image(qr_url, width=200)

    st.write("---")
    with st.expander("⚙️ Ajustes de Cuenta"):
        nueva_p = st.text_input("Cambiar mi contraseña", type="password")
        if st.button("Guardar nueva clave"):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("UPDATE pacientes SET password=? WHERE num_historia=?", (nueva_p, p[0]))
            conn.commit(); conn.close(); st.success("Contraseña actualizada con éxito.")

    if st.button("Cerrar Sesión"): st.session_state['auth'] = False; st.rerun()
