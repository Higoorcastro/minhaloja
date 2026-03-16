import sqlite3
import json

def check_db():
    conn = sqlite3.connect('loja.db')
    conn.row_factory = sqlite3.Row
    print("--- USUARIOS ---")
    users = conn.execute("SELECT id, nome, login, papel, ativo FROM usuarios").fetchall()
    for u in users:
        print(dict(u))
        perms = conn.execute("SELECT modulo FROM usuario_permissoes WHERE usuario_id=?", (u['id'],)).fetchall()
        print(f"  Permissões: {[p['modulo'] for p in perms]}")
    conn.close()

if __name__ == "__main__":
    check_db()
