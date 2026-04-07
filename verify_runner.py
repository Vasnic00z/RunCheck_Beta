
import sqlite3

def verify_user_by_email(email):
    try:
        conn = sqlite3.connect('runcheck.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user:
            print(f"Found user: {user}")
            cursor.execute("UPDATE usuarios SET is_verified = 1 WHERE email = ?", (email,))
            conn.commit()
            print(f"User '{email}' verification status updated to TRUE.")
        else:
            print(f"User with email '{email}' not found.")
            
        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    verify_user_by_email('nico_perezvas@outlook.com')
