
import sqlite3

def update_user():
    try:
        conn = sqlite3.connect('runcheck.db')
        cursor = conn.cursor()
        
        # Check if user exists first
        cursor.execute("SELECT * FROM usuarios WHERE cedula = '0605553114'")
        user = cursor.fetchone()
        
        if user:
            print(f"Found user: {user}")
            cursor.execute("UPDATE usuarios SET is_verified = 1 WHERE cedula = '0605553114'")
            conn.commit()
            print("User verification status updated to TRUE.")
        else:
            print("User with cedula '0605553114' not found.")
            
        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    update_user()
