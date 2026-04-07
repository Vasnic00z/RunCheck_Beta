
import sqlite3

def list_users():
    conn = sqlite3.connect('runcheck.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios")
    users = cursor.fetchall()
    print("Users found:")
    for user in users:
        print(user)
    conn.close()

if __name__ == "__main__":
    list_users()
