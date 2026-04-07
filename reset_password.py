
import sqlite3
import bcrypt

# Configuración
DB_NAME = 'runcheck.db'
TARGET_EMAIL = 'locosju@hotmail.com'
NEW_PASSWORD = 'Admin123'

def reset_password(email, new_password):
    try:
        # Encriptar con bcrypt (el standard de la app)
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Verificar si existe
        c.execute("SELECT id, nombre, email FROM usuarios WHERE email = ?", (email,))
        user = c.fetchone()
        
        if not user:
            print(f"Error: El usuario {email} no existe en la base de datos.")
            return

        print(f"Usuario encontrado: ID {user[0]} - {user[1]}")
        
        # Actualizar
        c.execute("UPDATE usuarios SET password = ? WHERE email = ?", (hashed_password, email))
        conn.commit()
        
        if c.rowcount > 0:
            print(f"Contrasena actualizada correctamente para {email}.")
        else:
            print("No se realizo ningun cambio (tal vez ya era la misma contrasena?).")
            
        conn.close()
        
    except Exception as e:
        print(f"Ocurrio un error: {e}")

if __name__ == "__main__":
    print("Iniciando proceso de reseteo de contrasena...")
    reset_password(TARGET_EMAIL, NEW_PASSWORD)
