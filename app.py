import streamlit as st
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import urllib.request
import json
import datetime
from datetime import timedelta
from io import BytesIO

# --- 1. CONFIGURACIÓN BASE DE DATOS ---
def crear_conexion():
    return sqlite3.connect('farmacia_v7.db', check_same_thread=False)

def inicializar_db():
    conn = crear_conexion()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes 
                 (num_historia TEXT PRIMARY KEY, nombre TEXT, primer_apellido TEXT, email TEXT, 
                  telefono TEXT, password TEXT, medicacion TEXT, codigo_nacional TEXT, estado TEXT, telegram_id TEXT)''')
    conn.commit()
    conn.close()

# --- 2. FUNCIONES DE APOYO ---
def enviar_email(destinatario, nombre, url_app, fecha, hora):
    try:
        remitente = st.secrets["EMAIL_REMITENTE"]
        pwd = st.secrets["EMAIL_PASSWORD"]
        fecha_str = fecha.strftime('%d/%m/%Y')
        hora_str = hora.strftime('%H:%M')
        cuerpo_mensaje = f"Hola {nombre},\n\nSu medicación ya está lista en nuestra farmacia.\n\n📅 Día de recogida: {fecha_str}\n🕒 Hora asignada (a partir de las): {hora_str}\n\nPara evitar esperas, le rogamos respete este horario.\n\nConfirme su recogida aquí:\n{url_app}"
        msg = MIMEText(cuerpo_mensaje)
        msg['Subject'] = "AVISO: Farmacia - Su Cita de Recogida"
        msg['From'] = remitente
        msg['To'] = destinatario
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remitente, pwd)
            server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except: return False

def enviar_telegram(chat_id, mensaje):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': mensaje}).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except: return False

def obtener_enlace_cima(cn, nombre_med):
    if not cn:
        med_encode = urllib.parse.quote(str(nombre_med))
        return f"https://cima.aemps.es/cima/publico/lista.html?raZonSocial={med_encode}"
    try:
        url_api = f"https://cima.aemps.es/cima/rest/medicamento?cn={cn}"
        req = urllib.request.Request(url_api, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                nregistro = data.get('nregistro')
                if nregistro: return f"https://cima.aemps.es/cima/dochtml/p/{nregistro}/Prospecto.html"
    except Exception: pass 
    return f"https://cima.aemps.es/cima/publico/lista.html?cn={cn}"

# --- 3. INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Farmacia Clientes", layout="wide", page_icon="💊")
inicializar_db()

URL_APP = "https://tdyxipgchc5jegixrwkbp9.streamlit.app/" 

if 'auth' not in st.session_state: st.session_state['auth'] = False

st.markdown("""
<style>
.footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: transparent; color: rgba(150, 150, 150, 0.4); text-align: right; padding-right: 20px; font-size: 12px; z-index: 100; }
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
<style> @keyframes moverAdelante { 0% { left: -150px; } 100% { left: 100%; } } </style>
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
    menu = st.sidebar.radio("Navegación", [
        "📊 Seguimiento Individual", 
        "🚀 Envío Masivo Programado",  # NUEVA OPCIÓN
        "🗂️ Editor Base de Datos", 
        "📤 Importar Excel", 
        "➕ Alta Manual", 
        "🚪 Salir"
    ])

    if menu == "📊 Seguimiento Individual":
        st.header("Seguimiento y Avisos Individuales")
        conn = crear_conexion(); df = pd.read_sql("SELECT * FROM pacientes", conn); conn.close()
        
        if df.empty:
            st.warning("No hay pacientes en la base de datos.")
        else:
            total = len(df); confirmados = len(df[df['estado'] == 'CONFIRMADO']); pendientes = total - confirmados
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("👥 Total Pacientes", total); col_m2.metric("⏳ Pendientes", pendientes); col_m3.metric("✅ Confirmados", confirmados)
            st.divider()

            for i, r in df.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 2])
                    c1.write(f"👤 **{r['nombre']} {r['primer_apellido']}**")
                    color = "🟢" if r['estado'] == "CONFIRMADO" else "🟡"
                    c2.write(f"{color} {r['estado']}")
                    
                    if r['estado'] == 'CONFIRMADO':
                        if c3.button("🔄 Nuevo Pedido", key=f"r_{r['num_historia']}"):
                            conn = crear_conexion(); c = conn.cursor()
                            c.execute("UPDATE pacientes SET estado='Pendiente' WHERE num_historia=?", (r['num_historia'],))
                            conn.commit(); conn.close(); st.rerun()
                    
                    with st.expander("🔔 Programar Recogida (Individual)"):
                        col_f, col_h = st.columns(2)
                        f_rec = col_f.date_input("Día de recogida", key=f"fd_{r['num_historia']}")
                        h_rec = col_h.time_input("Hora a partir de", key=f"fh_{r['num_historia']}")
                        st.write("Método de envío:")
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        
                        if col_btn1.button("📧 Email", key=f"e_{r['num_historia']}"):
                            if enviar_email(r['email'], r['nombre'], URL_APP, f_rec, h_rec): st.success("¡Email enviado!")
                            else: st.error("Error.")
                        
                        msg_wa = urllib.parse.quote(f"Hola {r['nombre']}, su medicación está lista.\nPuede pasar el {f_rec.strftime('%d/%m/%Y')} a las {h_rec.strftime('%H:%M')}.\nConfirme aquí: {URL_APP}")
                        col_btn2.markdown(f"[📲 WhatsApp](https://wa.me/{r['telefono']}?text={msg_wa})")
                        
                        if r['telegram_id']:
                            if col_btn3.button("✈️ Telegram", key=f"t_{r['num_historia']}"):
                                msg_tg = f"Hola {r['nombre']}, su medicación está lista.\n📅 Fecha: {f_rec.strftime('%d/%m/%Y')}\n🕒 Hora: {h_rec.strftime('%H:%M')}\nConfirme aquí: {URL_APP}"
                                if enviar_telegram(r['telegram_id'], msg_tg): st.success("Telegram enviado!")
                                else: st.error("Error.")
                    st.divider()

    # --- NUEVO: SISTEMA DE AGENDA MASIVA ---
    elif menu == "🚀 Envío Masivo Programado":
        st.header("Envío Masivo de Citas Escalonadas")
        st.write("Programa automáticamente los emails de los pacientes pendientes separándolos por intervalos de tiempo.")
        
        conn = crear_conexion()
        # Solo traemos a los pacientes "Pendientes"
        df_pendientes = pd.read_sql("SELECT num_historia, nombre, primer_apellido, email, medicacion FROM pacientes WHERE estado='Pendiente'", conn)
        conn.close()

        if df_pendientes.empty:
            st.info("🎉 ¡No hay pacientes pendientes de avisar!")
        else:
            st.write("### 1. Selecciona a quiénes quieres avisar")
            # Añadimos una columna de casillas (por defecto desmarcada)
            df_pendientes.insert(0, "Seleccionar", False)
            
            # Mostramos la tabla interactiva
            df_editada = st.data_editor(
                df_pendientes, 
                hide_index=True, 
                use_container_width=True,
                column_config={"Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False)}
            )
            
            seleccionados = df_editada[df_editada["Seleccionar"] == True]
            st.write(f"Pacientes seleccionados: **{len(seleccionados)}**")

            st.write("### 2. Configura la Agenda")
            col_d, col_h1, col_h2, col_m = st.columns(4)
            fecha_masiva = col_d.date_input("Día de entrega")
            hora_inicio = col_h1.time_input("Hora Primera Cita", datetime.time(10, 0))
            hora_fin = col_h2.time_input("Hora Límite", datetime.time(13, 30))
            intervalo = col_m.number_input("Intervalo (minutos)", min_value=1, value=5)

            if st.button("🚀 INICIAR ENVÍO AUTOMÁTICO (EMAIL)", use_container_width=True):
                if seleccionados.empty:
                    st.error("Debes marcar la casilla de al menos un paciente en la tabla.")
                else:
                    # Combinamos la fecha y hora para hacer cálculos
                    tiempo_actual = datetime.datetime.combine(fecha_masiva, hora_inicio)
                    tiempo_limite = datetime.datetime.combine(fecha_masiva, hora_fin)
                    
                    reporte = []
                    
                    with st.spinner('Procesando agenda y enviando correos silenciosos...'):
                        for idx, row in seleccionados.iterrows():
                            # Comprobar que no nos pasamos de la hora de cierre
                            if tiempo_actual > tiempo_limite:
                                st.warning(f"⚠️ Se alcanzó la hora límite. No se ha avisado a {row['nombre']} ni a los siguientes.")
                                break
                            
                            # Enviar el email real
                            exito = enviar_email(row['email'], row['nombre'], URL_APP, tiempo_actual.date(), tiempo_actual.time())
                            
                            # Guardar en el reporte
                            reporte.append({
                                "Paciente": f"{row['nombre']} {row['primer_apellido']}",
                                "Medicación": row['medicacion'],
                                "Hora Asignada": tiempo_actual.strftime('%H:%M'),
                                "Email": "✅ Enviado" if exito else "❌ Fallo"
                            })
                            
                            # Sumar los minutos (ej: 5 min) para el siguiente paciente
                            tiempo_actual += timedelta(minutes=intervalo)
                    
                    # Mostrar resumen final
                    st.success("¡Operación completada!")
                    st.write("📋 **Resumen de Citas Asignadas:**")
                    st.dataframe(pd.DataFrame(reporte), use_container_width=True)


    elif menu == "🗂️ Editor Base de Datos":
        st.header("Editor Interactivo de Pacientes")
        conn = crear_conexion(); df = pd.read_sql("SELECT * FROM pacientes", conn); conn.close()
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar Cambios"):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("DELETE FROM pacientes"); conn.commit()
            edited_df.to_sql('pacientes', conn, if_exists='append', index=False)
            conn.close(); st.success("¡Base de datos actualizada!")

    elif menu == "📤 Importar Excel":
        st.subheader("Carga Masiva de Pacientes")
        st.write("El Excel debe tener: `num_historia`, `nombre`, `primer_apellido`, `email`, `telefono`, `password`, `medicacion`, `codigo_nacional`, `telegram_id`.")
        file = st.file_uploader("Seleccionar Excel", type=['xlsx'])
        if file:
            df_excel = pd.read_excel(file)
            st.dataframe(df_excel.head())
            if st.button("Confirmar Importación"):
                conn = crear_conexion()
                df_excel['estado'] = "Pendiente"
                df_excel.to_sql('pacientes', conn, if_exists='append', index=False)
                conn.close(); st.success("¡Importación finalizada!")

    elif menu == "➕ Alta Manual":
        with st.form("registro_manual", clear_on_submit=True):
            h = st.text_input("Nº Historia / DNI"); n = st.text_input("Nombre"); a = st.text_input("Primer Apellido")
            e = st.text_input("Email"); t = st.text_input("Teléfono (34...)"); p = st.text_input("Clave Inicial")
            m = st.text_input("Medicación Asignada"); cn = st.text_input("Código Nacional (CN)")
            tg = st.text_input("Telegram ID (Opcional)")
            if st.form_submit_button("Registrar"):
                if h and n:
                    conn = crear_conexion(); c = conn.cursor()
                    try:
                        c.execute("INSERT INTO pacientes VALUES (?,?,?,?,?,?,?,?,?,?)", (h,n,a,e,t,p,m,cn,"Pendiente",tg))
                        conn.commit(); st.success("Paciente registrado.")
                    except: st.error("Error: El ID ya existe.")
                    finally: conn.close()

    if menu == "🚪 Salir": st.session_state['auth'] = False; st.rerun()

# --- VISTA PACIENTE ---
elif st.session_state['auth'] == "paciente":
    p = st.session_state['user_data']
    st.title(f"👋 Bienvenido/a, {p[1]} {p[2]}")
    
    medicacion = p[6]; codigo_nacional = p[7]; estado_actual = p[8]; telegram_actual = p[9]
    enlace_cima = obtener_enlace_cima(codigo_nacional, medicacion)
    
    titulo_cal = urllib.parse.quote("Recogida de Medicación")
    detalles_cal = urllib.parse.quote(f"Recuerda recoger: {medicacion}.\n¡Lleva tu QR!")
    enlace_cal = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo_cal}&details={detalles_cal}"

    st.markdown(f"""
<div style="background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
<h3 style="color: #004d99;">📦 Su Medicación:</h3>
<p style="font-size: 20px; font-weight: bold;">{medicacion}</p>
<p>Estado actual: <b>{estado_actual}</b></p>
<hr>
<div style="display: flex; gap: 10px; flex-wrap: wrap;">
    <a href="{enlace_cima}" target="_blank" style="text-decoration: none;">
        <button style="background-color: #008CBA; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📄 Leer prospecto en CIMA</button>
    </a>
    <a href="{enlace_cal}" target="_blank" style="text-decoration: none;">
        <button style="background-color: #FFA500; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">📅 Recordatorio Calendario</button>
    </a>
</div></div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    if estado_actual != 'CONFIRMADO':
        if st.button("✅ CONFIRMAR QUE PASARÉ A RECOGERLA", use_container_width=True):
            conn = crear_conexion(); c = conn.cursor()
            c.execute("UPDATE pacientes SET estado='CONFIRMADO' WHERE num_historia=?", (p[0],))
            conn.commit(); conn.close()
            lista_p = list(p); lista_p[8] = 'CONFIRMADO'; st.session_state['user_data'] = tuple(lista_p)
            st.balloons(); st.rerun()
    else:
        st.success("✅ Recogida confirmada. Por favor, muestra este código QR:")
        qr_data = urllib.parse.quote(f"ID:{p[0]} | Med:{p[6]}")
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_data}&color=004d99"
        c1, c2, c3 = st.columns([1,2,1])
        with c2: st.image(qr_url, width=200)

    st.write("---")
    with st.expander("⚙️ Ajustes de Cuenta y Notificaciones"):
        st.write("### ✈️ Avisos por Telegram")
        st.info("Para recibir avisos automáticos de la farmacia sin dar tu teléfono: \n1. Entra en Telegram y busca a **@getmyid_bot** para saber tu número ID.\n2. Busca nuestro bot y dale a 'Iniciar'.\n3. Pega tu ID numérico aquí abajo.")
        nuevo_tg = st.text_input("Tu ID de Telegram", value=telegram_actual if telegram_actual else "")
        nueva_p = st.text_input("Cambiar mi contraseña", type="password")
        if st.button("Guardar Ajustes"):
            conn = crear_conexion(); c = conn.cursor()
            if nueva_p:
                c.execute("UPDATE pacientes SET password=?, telegram_id=? WHERE num_historia=?", (nueva_p, nuevo_tg, p[0]))
            else:
                c.execute("UPDATE pacientes SET telegram_id=? WHERE num_historia=?", (nuevo_tg, p[0]))
            conn.commit(); conn.close()
            lista_p = list(p); lista_p[9] = nuevo_tg; st.session_state['user_data'] = tuple(lista_p)
            st.success("Ajustes guardados con éxito.")

    if st.button("Cerrar Sesión"): st.session_state['auth'] = False; st.rerun()
