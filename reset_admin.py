import os
import psycopg2
import bcrypt

DB_URL = os.getenv('DB_URL')
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

new_senha = "O7(;5u8'@pm8rf,%4E33E}{JptAH.]6C"
hashed = bcrypt.hashpw(new_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

cur.execute("UPDATE superadmin_usuarios SET login=%s, senha_hash=%s WHERE id=1", ('admin', hashed))
conn.commit()
print("SENHA ATUALIZADA COM SUCESSO - ADMIN!")
conn.close()
