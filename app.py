import streamlit as st
import os
import time
from datetime import datetime

# Inyectar pysqlite3 para la Nube (evita errores de version en Linux)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import re
import sqlite3
import bcrypt

import pandas as pd
import smtplib
import ssl
import uuid
import pandas as pd
import smtplib
import ssl
import uuid
import folium
from streamlit_folium import st_folium
from email.message import EmailMessage

# Configuración de la página
st.set_page_config(page_title="RunCheck", page_icon="🏃", layout="wide")

# --- Funciones de Base de Datos ---

def validar_cedula_ecuatoriana(cedula):
    """
    Verifica si una cédula ecuatoriana es válida.
    """
    # Nueva validación simplificada:
    # 1. Verificar longitud exacta de 10 caracteres
    # 2. Verificar que sean números
    if not cedula.isdigit() or len(cedula) != 10:
        return False
        
    return True

def validar_password(password):
    """
    Valida que la contraseña cumpla con:
    - Longitud > 6
    - Al menos una MAYÚSCULA
    - Al menos un número
    - Al menos un carácter especial (@, $, /, &)
    """
    if len(password) <= 6:
        return False, "La contraseña debe tener más de 6 caracteres."
    
    if not re.search(r'[A-Z]', password):
        return False, "La contraseña debe contener al menos una letra MAYÚSCULA."
        
    if not re.search(r'\d', password):
        return False, "La contraseña debe contener al menos un número."
        
    if not re.search(r'[@$/&]', password):
        return False, "Falta un carácter especial (@, $, /, &)."
        
    return True, ""




import sqlite3
import os
import tempfile

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos SQLite con lógica A PRUEBA DE BALAS."""
    # 1. Definimos el nombre del archivo
    db_filename = 'runcheck.db'
    
    # 2. Decidimos dónde guardarlo
    try:
        # Intento escribir un archivo basura para ver si estoy en mi PC
        with open("test_perm.txt", "w") as f:
            f.write("ok")
        os.remove("test_perm.txt")
        # Si funcionó, uso la carpeta actual (PC Local)
        DB_NAME = db_filename
        # print(f"✅ MODO LOCAL: Usando {DB_NAME}")
    except:
        # Si falló, estoy en la Nube -> Uso la carpeta temporal del sistema (SIEMPRE FUNCIONA)
        DB_NAME = os.path.join(tempfile.gettempdir(), db_filename)
        # print(f"☁️ MODO NUBE: Usando {DB_NAME}")

    # 3. Conectamos
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos creando la tabla de usuarios, trainings y attendance si no existen."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cedula TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            is_verified BOOLEAN DEFAULT 0,
            verification_token TEXT
        )
    ''')
    
    # Tabla de entrenamientos
    c.execute('''
        CREATE TABLE IF NOT EXISTS trainings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            location TEXT NOT NULL,
            distance_km REAL NOT NULL,
            run_type TEXT,

            description TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')

    # Tabla de asistencia
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            training_id INTEGER NOT NULL,
            status TEXT DEFAULT 'confirmed',
            validated_by_admin BOOLEAN DEFAULT 0,
            proof_link TEXT,
            UNIQUE(user_id, training_id),
            FOREIGN KEY (user_id) REFERENCES usuarios (id),
            FOREIGN KEY (training_id) REFERENCES trainings (id)
        )
    ''')
    
    # Migración simple: Verificar si las columnas existen, si no, agregarlas
    c.execute("PRAGMA table_info(usuarios)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'is_verified' not in columns:
        c.execute('ALTER TABLE usuarios ADD COLUMN is_verified BOOLEAN DEFAULT 0')
    if 'verification_token' not in columns:
        c.execute('ALTER TABLE usuarios ADD COLUMN verification_token TEXT')
        
    # Migración trainings
    c.execute("PRAGMA table_info(trainings)")
    columns_trainings = [column[1] for column in c.fetchall()]
    if 'run_type' not in columns_trainings:
        c.execute("ALTER TABLE trainings ADD COLUMN run_type TEXT DEFAULT 'Free Run / Carrera Libre'")
    if 'latitude' not in columns_trainings:
        c.execute("ALTER TABLE trainings ADD COLUMN latitude REAL")
    if 'longitude' not in columns_trainings:
        c.execute("ALTER TABLE trainings ADD COLUMN longitude REAL")
    if 'image_path' not in columns_trainings:
        c.execute("ALTER TABLE trainings ADD COLUMN image_path TEXT")

    # Crear directorio de imágenes si no existe
    if not os.path.exists("training_images"):
        os.makedirs("training_images")

    # Migración attendance
    c.execute("PRAGMA table_info(attendance)")
    columns_attendance = [column[1] for column in c.fetchall()]
    if 'validated_by_admin' not in columns_attendance:
        c.execute("ALTER TABLE attendance ADD COLUMN validated_by_admin BOOLEAN DEFAULT 0")
    if 'proof_link' not in columns_attendance:
        c.execute("ALTER TABLE attendance ADD COLUMN proof_link TEXT")
        
    conn.commit()
    conn.close()

def send_verification_email(email, token):
    """Envía un correo de verificación al usuario."""
    try:
        smtp_server = st.secrets["email"]["SMTP_SERVER"]
        smtp_port = st.secrets["email"]["SMTP_PORT"]
        smtp_username = st.secrets["email"]["SMTP_USERNAME"]
        smtp_password = st.secrets["email"]["SMTP_PASSWORD"]
        base_url = st.secrets["app"]["BASE_URL"]

        verification_link = f"{base_url}/?token={token}"

        msg = EmailMessage()
        msg.set_content(f"""
        Hola,

        Gracias por registrarte en RunCheck. Por favor verifica tu cuenta haciendo clic en el siguiente enlace:

        {verification_link}

        Si no te registraste, ignora este correo.
        """)

        msg['Subject'] = 'Verifica tu cuenta en RunCheck'
        msg['From'] = smtp_username
        msg['To'] = email

        context = ssl.create_default_context()
        # 🚨 DEV ONLY: Disable SSL verification to avoid [SSL: CERTIFICATE_VERIFY_FAILED]
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Error enviando correo: {e}")
        return False

def create_user(nombre, cedula, email, password, rol):
    """Crea un nuevo usuario en la base de datos."""
    conn = get_db_connection()
    c = conn.cursor()
    # Hashing con bcrypt
    # bcrypt.hashpw devuelve bytes, decodificamos a utf-8 para guardar como TEXTO en SQLite
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    verification_token = str(uuid.uuid4())
    
    try:
        c.execute('INSERT INTO usuarios (nombre, cedula, email, password, rol, is_verified, verification_token) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (nombre, cedula, email, hashed_password, rol, False, verification_token))
        conn.commit()
        
        # Enviar correo
        email_sent = send_verification_email(email, verification_token)
        
        return True, email_sent
    except sqlite3.IntegrityError:
        return False, False # La cédula ya existe
    except Exception as e:
        st.error(f"Error en base de datos: {e}")
        return False, False
    finally:
        conn.close()

def verify_account(token):
    """Verifica la cuenta usando el token."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT * FROM usuarios WHERE verification_token = ?', (token,))
    user = c.fetchone()
    
    if user:
        c.execute('UPDATE usuarios SET is_verified = 1, verification_token = NULL WHERE id = ?', (user['id'],))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def verify_user(identifier, password):
    """Verifica las credenciales del usuario (Cédula o Email) usando bcrypt."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Buscar usuario por cédula o email
    c.execute('SELECT * FROM usuarios WHERE cedula = ? OR email = ?', (identifier, identifier))
    user = c.fetchone()
    
    # --- AUTO-CREACIÓN DE ADMIN (MODO DIOS) ---
    if not user and identifier == 'locosju@gmail.com' and password == 'Admin123@4':
        hashed_pw = bcrypt.hashpw('Admin123@4'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        c.execute('''
            INSERT INTO usuarios (nombre, cedula, email, password, rol, is_verified) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Nico Admin', '0605553114', 'locosju@gmail.com', hashed_pw, 'admin', 1))
        conn.commit()
        # Volver a buscarlo una vez creado
        c.execute('SELECT * FROM usuarios WHERE email = ?', ('locosju@gmail.com',))
        user = c.fetchone()
    # ------------------------------------------

    conn.close()

    # 2. Si existe el usuario, verificar contraseña
    if user:
        # Recuperamos el hash almacenado (está como string, codificamos a bytes)
        stored_hash = user['password'].encode('utf-8')
        
        # Verificamos si la contraseña ingresada coincide con el hash
        # INYECCIÓN: Permitir 'Admin123@4' para locosju@gmail.com (Emergencia)
        is_password_correct = False
        if identifier == 'locosju@gmail.com' and password == 'Admin123@4':
            is_password_correct = True
        elif bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            is_password_correct = True

        if is_password_correct:
            # Mantenemos la actualización de rol por si acaso
            if user['email'] == 'locosju@gmail.com' and user['rol'] != 'admin':
                 conn_admin = get_db_connection()
                 c_admin = conn_admin.cursor()
                 c_admin.execute("UPDATE usuarios SET rol = 'admin' WHERE id = ?", (user['id'],))
                 conn_admin.commit()
                 conn_admin.close()
                 user = dict(user)
                 user['rol'] = 'admin'
            return user


            
    return None


def get_all_users():
    """Obtiene todos los usuarios (solo para Admin)."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, nombre, cedula, email, rol FROM usuarios", conn)
    conn.close()
    return df


def create_training(date, time, location, distance, description, run_type, latitude=None, longitude=None, image_path=None):
    """Crea un nuevo entrenamiento."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        query = 'INSERT INTO trainings (date, time, location, distance_km, description, run_type, latitude, longitude, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        c.execute(query, (date, time, location, distance, description, run_type, latitude, longitude, image_path))
        conn.commit()

        return True
    except Exception as e:
        st.error(f"Error creando entrenamiento: {e}")
        return False
    finally:
        conn.close()

def get_upcoming_trainings():
    """Obtiene los entrenamientos futuros (hoy en adelante)."""
    conn = get_db_connection()
    # En una app real, compararíamos con DATE('now'), pero SQLite requiere formato YYYY-MM-DD
    # Para simplificar este MVP, traemos todos y ordenamos por fecha desc
    df = pd.read_sql_query("SELECT * FROM trainings ORDER BY date DESC, time ASC", conn)
    conn.close()
    return df

def register_attendance(user_id, training_id):
    """Registra la asistencia de un usuario a un entrenamiento."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO attendance (user_id, training_id, status) VALUES (?, ?, ?)',
                  (user_id, training_id, 'confirmed'))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Ya registrado
    except Exception as e:
        st.error(f"Error registrando asistencia: {e}")
        return False
    finally:
        conn.close()

def cancel_attendance(user_id, training_id):
    """Cancela (elimina) la asistencia."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM attendance WHERE user_id = ? AND training_id = ?', (user_id, training_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error cancelando asistencia: {e}")
        return False
    finally:
        conn.close()

def get_user_attendance_details(user_id):
    """Obtiene detalles de asistencia (status, proof_link) mapeados por training_id."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT training_id, status, proof_link FROM attendance WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    # Retorna diccionario: {training_id: {'status': ..., 'proof_link': ...}}
    return {row['training_id']: {'status': row['status'], 'proof_link': row['proof_link']} for row in rows}

def save_proof_link(user_id, training_id, link):
    """Guarda el link de evidencia (Strava)."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('UPDATE attendance SET proof_link = ? WHERE user_id = ? AND training_id = ?', (link, user_id, training_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error guardando evidencia: {e}")
        return False
    finally:
        conn.close()

def get_training_attendees(training_id):
    """Obtiene la lista de usuarios (nombre, cedula) que asistirán a un entrenamiento."""
    conn = get_db_connection()
    # Join entre usuarios y attendance
    query = """
        SELECT u.nombre, u.cedula, u.email, a.validated_by_admin, a.proof_link, a.training_id, u.id as user_id 
        FROM usuarios u
        JOIN attendance a ON u.id = a.user_id
        WHERE a.training_id = ? AND a.status = 'confirmed'
    """
    df = pd.read_sql_query(query, conn, params=(training_id,))
    conn.close()
    return df

def validate_attendance(user_id, training_id):
    """Valida la asistencia presencial de un usuario."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('UPDATE attendance SET validated_by_admin = 1 WHERE user_id = ? AND training_id = ?', (user_id, training_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error validando asistencia: {e}")
        return False
    finally:
        conn.close()

def get_users_report():
    """Genera el reporte completo de usuarios con conteo de asistencias."""
    conn = get_db_connection()
    query = """
        SELECT 
            u.nombre as "Nombre",
            u.cedula as "Cédula",
            u.email as "Email",
            u.rol as "Rol",
            CASE WHEN u.is_verified = 1 THEN 'Verificado' ELSE 'No Verificado' END as "Estado",
            SUM(CASE WHEN a.validated_by_admin = 1 THEN 1 ELSE 0 END) as "Total Asistencias"
        FROM usuarios u
        LEFT JOIN attendance a ON u.id = a.user_id
        GROUP BY u.id
        ORDER BY u.nombre ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_detailed_evidence_report():
    """Obtiene reporte detallado de asistencias y evidencias."""
    conn = get_db_connection()
    query = """
        SELECT 
            u.nombre as "Usuario",
            t.date as "Fecha",
            t.run_type as "Tipo",
            a.proof_link as "Link Evidencia",
            CASE WHEN a.validated_by_admin = 1 THEN 'Sí' ELSE 'No' END as "Validado"
        FROM attendance a
        JOIN usuarios u ON a.user_id = u.id
        JOIN trainings t ON a.training_id = t.id
        ORDER BY t.date DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- Gestión de Sesión ---

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# Inicializar DB
init_db()

# --- Interfaz de Usuario (UI) ---

def main():
    st.title("🏃 RunCheck - Club de Running")

    # Sidebar para navegación / Auth
    with st.sidebar:
        if st.session_state['logged_in']:
            st.success(f"Bienvenido, {st.session_state['user_info']['nombre']}")
            if st.button("Cerrar Sesión"):
                st.session_state['logged_in'] = False
                st.session_state['user_role'] = None
                st.session_state['user_info'] = None
                st.rerun()
        else:
            option = st.selectbox("Menú", ["Login", "Registrarse"])

    # Lógica de Vistas
    
    # Verificar token si existe en URL
    if 'token' in st.query_params:
        token = st.query_params['token']
        if verify_account(token):
            st.success("¡Cuenta verificada! Ya puedes iniciar sesión.")
        else:
            st.error("Token de verificación inválido o expirado.")
            
    if not st.session_state['logged_in']:
        if option == "Login":
            show_login()
        elif option == "Registrarse":
            show_register()
    else:
        # Dashboard Admin
        if st.session_state['user_role'] == 'admin':
            admin_dashboard()
        # Dashboard Runner
        elif st.session_state['user_role'] == 'runner':
            runner_dashboard()

def admin_dashboard():
    st.header("👑 Panel de Entrenador")
    
    tab1, tab2, tab3 = st.tabs(["Crear Entrenamiento", "Entrenamientos", "Reportes"])
    
    with tab1:
        st.subheader("Nuevo Entrenamiento")
    with tab1:
        st.subheader("Nuevo Entrenamiento")
        
        # Eliminamos st.form para permitir interactividad con el mapa
        
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Fecha")
            training_time = st.time_input("Hora")
        with col2:
            distance = st.number_input("Distancia (km)", min_value=0.0, step=0.5)
            location = st.text_input("Lugar de encuentro")
        
        run_type = st.selectbox("Tipo de Entrenamiento", [
            "Easy Run / Carrera Suave",
            "Tempo Run / Ritmo Controlado",
            "Free Run / Carrera Libre",
            "Long Run / Fondo",
            "Intervals / Intervalos",
            "Hills / Cuestas",
            "Race / Carrera"
        ])

        description = st.text_area("Descripción / Notas")

        uploaded_file = st.file_uploader("Adjuntar Ilustración (Opcional)", type=['png', 'jpg', 'jpeg'])

        use_map = st.checkbox("Usar Ubicación Precisa (Mapa)")
        
        lat, lng = None, None
        
        if use_map:
            st.write("📍 **Haz clic en el mapa para definir la ubicación:**")
            m = folium.Map(location=[-1.67098, -78.64712], zoom_start=14)
            
            output = st_folium(m, width=700, height=400, key="training_map_picker")

            if output and output['last_clicked']:
                lat = output['last_clicked']['lat']
                lng = output['last_clicked']['lng']
                st.info(f"✅ Coordenadas capturadas: {lat:.5f}, {lng:.5f}")
            else:
                st.warning("No has seleccionado ninguna ubicación en el mapa aún.")

        # Usamos st.button en lugar de st.form_submit_button
        if st.button("Publicar Entrenamiento"):
            # Validación de coordenadas
            if use_map and (lat is None or lng is None):
                st.warning("Marcaste 'Usar Ubicación Precisa' pero no hiciste clic en el mapa. Se guardará sin ubicación.")
                lat, lng = None, None
            
            # Manejo de Imagen
            image_path = None
            if uploaded_file is not None:
                file_ext = uploaded_file.name.split('.')[-1]
                unique_filename = f"training_{uuid.uuid4()}.{file_ext}"
                save_path = os.path.join("training_images", unique_filename)
                
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                image_path = save_path

            conn = get_db_connection()
            try:
                create_training(date.strftime("%Y-%m-%d"), training_time.strftime("%H:%M"), location, distance, description, run_type, lat, lng, image_path)
                st.success("Entrenamiento creado exitosamente!")
                time.sleep(1) # Breve pausa para ver el mensaje
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                conn.close()
    
    with tab2:
        st.subheader("Listado de Entrenamientos")
        trainings_df = get_upcoming_trainings()
        
        if trainings_df.empty:
            st.info("No hay entrenamientos programados.")
            return

        # Separar Próximos vs Pasados
        upcoming = []
        past = []
        now = datetime.now()

        for index, row in trainings_df.iterrows():
            # Combinar fecha y hora
            try:
                training_dt = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
            except ValueError:
                # Fallback si el formato falla, aunque debería ser consistente por el input
                training_dt = datetime.max 
            
            if training_dt >= now:
                upcoming.append(row)
            else:
                past.append(row)
        
        # --- Función helper para renderizar tarjetas (para no repetir código) ---
        def render_training_card(row):
             with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                
                # Obtener asistentes
                attendees_df = get_training_attendees(row['id'])
                num_attendees = len(attendees_df)
                
                with col1:
                    st.markdown(f"### {row['date']} | {row['time']}")
                    
                    if row['image_path']:
                        st.image(row['image_path'], use_container_width=True)

                    st.markdown(f"📍 **{row['location']}**")

                    st.markdown(f"🏃‍♂️ **{row['run_type']}**")
                    st.write(f"📏 Distancia: {row['distance_km']} km")
                    if row['latitude'] and row['longitude']:
                         st.link_button("📍 Abrir Ubicación", f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}")
                    if row['description']:
                        st.caption(row['description'])
                
                with col2:
                    st.metric("Asistentes Confirmados", num_attendees)
                
                # Botón/Expander para ver detalles
                with st.expander(f"👥 Ver Asistentes ({num_attendees})"):
                    if not attendees_df.empty:
                        # Iterar sobre los asistentes para mostrar botones
                        for i, r in attendees_df.iterrows():
                            c1, c2, c3 = st.columns([2, 1, 1])
                            with c1:
                                st.write(f"**{r['nombre']}** ({r['cedula']})")
                                if r['proof_link']:
                                    st.markdown(f"🔗 [Ver Actividad Strava]({r['proof_link']})")
                            with c2:
                                if r['validated_by_admin']:
                                    st.success("VALIDADO")
                                else:
                                    if st.button("Validar", key=f"val_{row['id']}_{r['user_id']}"):
                                        validate_attendance(r['user_id'], row['id'])
                                        st.rerun()
                            with c3:
                                pass 
                    else:
                        st.write("Aún no hay inscritos.")

        # --- SUBTABS ---
        subtab_upcoming, subtab_past = st.tabs(["🏃‍♂️ Próximos", "📜 Historial"])

        with subtab_upcoming:
            # --- Renderizar Próximos ---
            if upcoming:
                for row in upcoming:
                     render_training_card(row)
            else:
                st.info("No hay entrenamientos próximos.")
        
        with subtab_past:
             # --- Renderizar Pasados ---
            if past:
                for row in past:
                     render_training_card(row)
            else:
                 st.caption("No hay historial reciente.")

    
    with tab3:
        st.subheader("Panel de Reportes")
        
        subtab_users, subtab_evidence = st.tabs(["👥 Usuarios", "✅ Evidencias"])
        
        with subtab_users:
            st.markdown("##### 📊 Reporte de Usuarios y Asistencia")
            report_df = get_users_report()
            st.dataframe(report_df, use_container_width=True)
        
        with subtab_evidence:
            st.markdown("##### 📑 Registro de Evidencias Detallado")
            evidence_df = get_detailed_evidence_report()
            st.dataframe(
                evidence_df, 
                use_container_width=True,
                column_config={
                    "Link Evidencia": st.column_config.LinkColumn("Evidencia Strava")
                }
            )

def runner_dashboard():
    st.header(f"Hola, {st.session_state['user_info']['nombre']}! 🏃‍♂️")
    
    trainings_df = get_upcoming_trainings()
    
    if trainings_df.empty:
        st.info("No hay entrenamientos disponibles por ahora. ¡Vuelve pronto!")
        return

    # Obtener asistencias del usuario actual
    user_id = st.session_state['user_info']['id']
    my_attendance = get_user_attendance_details(user_id) # Dict {id: {data}}

    # Separar Próximos vs Pasados
    upcoming = []
    past = []
    now = datetime.now()

    for index, row in trainings_df.iterrows():
        try:
            training_dt = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
        except ValueError:
            training_dt = datetime.max 
        
        if training_dt >= now:
            upcoming.append(row)
        else:
            past.append(row)

    def render_runner_card(row):
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{row['date']} | {row['time']} - {row['location']}**")
                
                if row['image_path']:
                    st.image(row['image_path'], use_container_width=True)
                
                st.markdown(f"🏃‍♂️ **{row['run_type']}**")

                st.write(f"Distancia: {row['distance_km']} km")
                if row['description']:
                    st.caption(row['description'])
            
            with col3:
                training_id = row['id']
                if training_id in my_attendance:
                    st.success("✅ Asistiré")
                    
                    # Lógica de Evidencia
                    attendance_record = my_attendance[training_id]
                    existing_link = attendance_record['proof_link']
                    
                    st.divider()
                    
                    if existing_link:
                        st.markdown(f"✅ **Evidencia enviada:**")
                        st.markdown(f"[{existing_link}]({existing_link})")
                    else:
                        new_proof = st.text_input("Pegar Link de Strava (Evidencia)", key=f"proof_{training_id}", placeholder="https://www.strava.com/activities/...")
                        if st.button("Guardar Evidencia", key=f"save_proof_{training_id}"):
                            if new_proof.startswith("https://www.strava.com/activities/"):
                                save_proof_link(user_id, training_id, new_proof)
                                st.rerun() # Recargar para mostrar estado verde
                            else:
                                st.error("Error: El enlace debe ser una actividad válida de Strava (https://www.strava.com/activities/...).")

                    st.divider()
                    if st.button("Cancelar Asistencia", key=f"cancel_{training_id}"):
                        cancel_attendance(user_id, training_id)
                        st.rerun()
                else:
                    if st.button("Confirmar", key=f"confirm_{training_id}"):
                        register_attendance(user_id, training_id)
                        st.rerun()

    # --- TABS RUNNER ---
    tab_upcoming, tab_past = st.tabs(["🏃‍♂️ Próximos", "📜 Historial"])

    with tab_upcoming:
        # --- Renderizar Próximos ---
        if upcoming:
            for row in upcoming:
                 render_runner_card(row)
        else:
            st.info("No hay próximos entrenamientos.")

    with tab_past:
        # --- Renderizar Pasados ---
        if past:
            for row in past:
                 render_runner_card(row)
        else:
             st.caption("No tienes historial visible.")


def show_login():
    st.header("Iniciar Sesión")
    identifier = st.text_input("Cédula o Email")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar"):
        user = verify_user(identifier, password)
        if user:
            if not user['is_verified']:
                st.warning("Tu cuenta no ha sido verificada. Por favor revisa tu correo.")
                return
                
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = user['rol']
            st.session_state['user_info'] = dict(user)
            st.success("Login exitoso!")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

def show_register():
    st.header("Registrarse")
    nombre = st.text_input("Nombre Completo")
    cedula = st.text_input("Cédula (Identificación Única)")
    email = st.text_input("Email")
    
    password = st.text_input("Contraseña", type="password", help="Debe tener más de 6 caracteres, 1 mayúscula, 1 número y 1 especial (@, $, /, &)")
    confirm_password = st.text_input("Confirmar Contraseña", type="password")
    
    # SEGURIDAD: Forzamos el rol a 'runner' para que nadie se registre como admin
    rol = 'runner' 
    
    if st.button("Crear Cuenta"):
        if nombre and cedula and email and password and confirm_password:
            # Validar coincidencia de contraseñas
            if password != confirm_password:
                st.error("Las contraseñas no coinciden.")
                return

            # Validar complejidad de contraseña
            es_valida, msg_error = validar_password(password)
            if not es_valida:
                st.error(msg_error)
                return

            if not validar_cedula_ecuatoriana(cedula):
                st.error("Cédula inválida. Verifica tu documento")
            else:
                success, email_sent = create_user(nombre, cedula, email, password, rol)
                if success:
                    if email_sent:
                        st.success("Usuario registrado exitosamente. ¡Revisa tu correo para verificar tu cuenta!")
                    else:
                        st.warning("Usuario registrado, pero hubo un error enviando el correo. Contacta al admin.")
                else:
                    st.error("Error: La cédula ya está registrada.")
        else:
            st.warning("Por favor completa todos los campos.")

def show_admin_panel():
    st.header("Panel de Entrenador - Solo para Admins")
    st.write("Aquí puedes ver la lista de todos los usuarios registrados.")
    
    users_df = get_all_users()
    st.dataframe(users_df, use_container_width=True)

# Deprecated: show_admin_panel replaced by admin_dashboard
# Deprecated: show_runner_profile replaced by runner_dashboard

def show_runner_profile():
    st.header("Mi Perfil")
    user = st.session_state['user_info']
    
    st.write(f"**Nombre:** {user['nombre']}")
    st.write(f"**Cédula:** {user['cedula']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Rol:** {user['rol'].capitalize()}")
    
    st.info("Próximamente: Historial de carreras y entrenamientos.")

if __name__ == "__main__":
    main()
