import os
import sys
import sqlite3
import hashlib
import secrets
import threading
import webbrowser
from datetime import datetime, date
from functools import wraps
from flask import (Flask, render_template, request, jsonify, g,
                   session, redirect)

# ── Path helpers ───────────────────────────────────────────────────────────
def resource_path(rel):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

def data_path(filename):
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

DB_PATH = data_path('loja.db')

app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=data_path('static'))
app.secret_key = 'gestao-loja-secret-key-2024-xK9pL'

ALL_MODULES = ['dashboard','pdv','vendas','os','produtos',
               'clientes','financeiro','relatorios','usuarios', 'settings']

# ── Database ───────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        login TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        papel TEXT NOT NULL DEFAULT 'operador',
        ativo INTEGER DEFAULT 1,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS usuario_permissoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        modulo TEXT NOT NULL,
        UNIQUE(usuario_id, modulo)
    );
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        nome TEXT NOT NULL,
        descricao TEXT,
        categoria_id INTEGER REFERENCES categorias(id),
        preco_custo REAL DEFAULT 0,
        preco_venda REAL DEFAULT 0,
        estoque INTEGER DEFAULT 0,
        estoque_minimo INTEGER DEFAULT 0,
        unidade TEXT DEFAULT 'UN',
        ativo INTEGER DEFAULT 1,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf_cnpj TEXT,
        telefone TEXT,
        email TEXT,
        endereco TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE,
        cliente_id INTEGER REFERENCES clientes(id),
        cliente_nome TEXT,
        vendedor_id INTEGER REFERENCES vendedores(id),
        vendedor_nome TEXT,
        subtotal REAL DEFAULT 0,
        desconto REAL DEFAULT 0,
        total REAL DEFAULT 0,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        status TEXT DEFAULT 'CONCLUIDA',
        observacao TEXT,
        motivo_cancelamento TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS venda_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
        produto_id INTEGER REFERENCES produtos(id),
        produto_nome TEXT,
        quantidade REAL NOT NULL,
        preco_unitario REAL NOT NULL,
        desconto REAL DEFAULT 0,
        subtotal REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE,
        cliente_id INTEGER REFERENCES clientes(id),
        cliente_nome TEXT,
        equipamento TEXT,
        problema TEXT,
        diagnostico TEXT,
        solucao TEXT,
        tecnico TEXT,
        status TEXT DEFAULT 'ABERTA',
        prioridade TEXT DEFAULT 'NORMAL',
        previsao TEXT,
        valor_servico REAL DEFAULT 0,
        valor_pecas REAL DEFAULT 0,
        desconto REAL DEFAULT 0,
        total REAL DEFAULT 0,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime')),
        checklist TEXT,
        senha_padrao TEXT,
        senha_pin TEXT,
        cliente_cpf TEXT,
        cliente_telefone TEXT
    );
    CREATE TABLE IF NOT EXISTS os_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        os_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
        produto_id INTEGER REFERENCES produtos(id),
        produto_nome TEXT,
        quantidade REAL NOT NULL,
        preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        categoria TEXT DEFAULT 'GERAL',
        valor REAL NOT NULL,
        data TEXT NOT NULL,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_nota TEXT,
        fornecedor TEXT,
        total REAL DEFAULT 0,
        data TEXT NOT NULL,
        observacao TEXT,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS compra_itens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
        produto_id INTEGER REFERENCES produtos(id),
        produto_nome TEXT,
        quantidade REAL NOT NULL,
        preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chave TEXT UNIQUE NOT NULL,
        valor TEXT
    );
    CREATE TABLE IF NOT EXISTS vendedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ativo INTEGER DEFAULT 1,
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS contas_receber (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER REFERENCES clientes(id),
        descricao TEXT NOT NULL,
        valor_total REAL NOT NULL,
        data_vencimento TEXT NOT NULL,
        status TEXT DEFAULT 'PENDENTE',
        criado_em TEXT DEFAULT (datetime('now','localtime')),
        atualizado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS recebimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conta_id INTEGER NOT NULL REFERENCES contas_receber(id) ON DELETE CASCADE,
        valor_pago REAL NOT NULL,
        data_pagamento TEXT NOT NULL,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        criado_em TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    conn.commit()

    # Admin user seed
    if not conn.execute("SELECT id FROM usuarios WHERE login='admin'").fetchone():
        cur2 = conn.execute(
            "INSERT INTO usuarios(nome,login,senha_hash,papel) VALUES(?,?,?,?)",
            ('Administrador', 'admin', hash_pw('admin123'), 'admin')
        )
        uid = cur2.lastrowid
        for m in ALL_MODULES:
            conn.execute("INSERT OR IGNORE INTO usuario_permissoes(usuario_id,modulo) VALUES(?,?)", (uid, m))
        conn.commit()
    
    # Migrations
    try: db_migrate(conn)
    except: pass
    
    conn.commit()

    for c in ['Eletrônicos','Informática','Celulares','Acessórios','Peças','Serviços','Outros']:
        try: conn.execute("INSERT INTO categorias(nome) VALUES(?)", (c,))
        except: pass
    conn.commit()

    # Migrações (para bases existentes)
    try: conn.execute("ALTER TABLE ordens_servico ADD COLUMN checklist TEXT")
    except: pass
    try: conn.execute("ALTER TABLE ordens_servico ADD COLUMN senha_padrao TEXT")
    except: pass
    try: conn.execute("ALTER TABLE ordens_servico ADD COLUMN senha_pin TEXT")
    except: pass
    conn.commit()
    conn.close()

def db_migrate(conn):
    # Add cliente_cpf and cliente_telefone to ordens_servico if they don't exist
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ordens_servico)").fetchall()]
    if 'cliente_cpf' not in cols:
        conn.execute("ALTER TABLE ordens_servico ADD COLUMN cliente_cpf TEXT")
    if 'cliente_telefone' not in cols:
        conn.execute("ALTER TABLE ordens_servico ADD COLUMN cliente_telefone TEXT")
    
    # Add vendedor_id and vendedor_nome to vendas
    cols_vendas = [r[1] for r in conn.execute("PRAGMA table_info(vendas)").fetchall()]
    if 'vendedor_id' not in cols_vendas:
        conn.execute("ALTER TABLE vendas ADD COLUMN vendedor_id INTEGER REFERENCES vendedores(id)")
    if 'vendedor_nome' not in cols_vendas:
        conn.execute("ALTER TABLE vendas ADD COLUMN vendedor_nome TEXT")

    # Create config table if it doesn't exist
    conn.execute("CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT UNIQUE NOT NULL, valor TEXT)")

    # Create vendedores table if it doesn't exist
    conn.execute("CREATE TABLE IF NOT EXISTS vendedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, ativo INTEGER DEFAULT 1, criado_em TEXT DEFAULT (datetime('now','localtime')))")

    # Create contas_receber and recebimentos tables if they don't exist
    conn.execute('''CREATE TABLE IF NOT EXISTS contas_receber (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER REFERENCES clientes(id),
        descricao TEXT NOT NULL, valor_total REAL NOT NULL, data_vencimento TEXT NOT NULL,
        status TEXT DEFAULT 'PENDENTE', criado_em TEXT DEFAULT (datetime('now','localtime')), atualizado_em TEXT DEFAULT (datetime('now','localtime')))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS recebimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conta_id INTEGER NOT NULL REFERENCES contas_receber(id) ON DELETE CASCADE,
        valor_pago REAL NOT NULL, data_pagamento TEXT NOT NULL, forma_pagamento TEXT DEFAULT 'DINHEIRO',
        criado_em TEXT DEFAULT (datetime('now','localtime')))''')

    # Add motivo_cancelamento to vendas
    if 'motivo_cancelamento' not in cols_vendas:
        conn.execute("ALTER TABLE vendas ADD COLUMN motivo_cancelamento TEXT")

def run_setup_wizard():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if we already have basic config
    has_config = cur.execute("SELECT COUNT(*) FROM config").fetchone()[0]
    if has_config > 0:
        conn.close()
        return

    print("\n" + "="*50)
    print("   ASSISTENTE DE CONFIGURACAO INICIAL")
    print("="*50)
    print("Bem-vindo ao GestaoLoja! Por favor, informe os dados da sua loja:")
    
    shop_name = input("Nome da Loja: ").strip() or "Minha Loja"
    shop_addr = input("Endereco: ").strip() or "Endereco nao cadastrado"
    shop_wpp = input("WhatsApp: ").strip() or "(00) 00000-0000"
    shop_insta = input("Instagram: ").strip() or "@sualoja"
    
    configs = [
        ('shop_name', shop_name),
        ('shop_address', shop_addr),
        ('shop_whatsapp', shop_wpp),
        ('shop_instagram', shop_insta)
    ]
    
    for k, v in configs:
        cur.execute("INSERT OR REPLACE INTO config(chave, valor) VALUES(?,?)", (k, v))
        
    conn.commit()
    conn.close()
    print("\n[OK] Configuracoes salvas com sucesso!")
    print("="*50 + "\n")




# ── Helpers ────────────────────────────────────────────────────────────────
def rows_to_list(rows):
    return [dict(r) for r in rows]

def next_number(prefix, table, col):
    db = get_db()
    n = (db.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()['c'] or 0) + 1
    return f"{prefix}{str(n).zfill(6)}"

def get_user_permissions(user_id):
    db = get_db()
    return [r['modulo'] for r in db.execute(
        "SELECT modulo FROM usuario_permissoes WHERE usuario_id=?", (user_id,)).fetchall()]

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'error':'unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def require_module(*modules):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('user_id'):
                return jsonify({'error':'unauthorized'}), 401
            user_perms = session.get('permissions', [])
            if session.get('papel') == 'admin' or any(m in user_perms for m in modules):
                return f(*args, **kwargs)
            return jsonify({'error':'forbidden', 'message': f"Sem permissão: {', '.join(str(m) for m in modules)}"}), 403
        return decorated
    return decorator

# ── API Config ─────────────────────────────────────────────────────────────
@app.route('/api/config', methods=['GET'])
@require_auth
def api_get_config():
    db = get_db()
    rows = db.execute("SELECT chave, valor FROM config").fetchall()
    return jsonify({r['chave']: r['valor'] for r in rows})

@app.route('/api/config', methods=['POST'])
@require_auth
def api_save_config():
    if session.get('papel') != 'admin':
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    db = get_db()
    data = request.json
    for k, v in data.items():
        db.execute("INSERT OR REPLACE INTO config(chave, valor) VALUES(?,?)", (k, v))
    db.commit()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════
@app.route('/login')
def login_page():
    if session.get('user_id'): return redirect('/')
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    d = request.json or {}
    login = (d.get('login') or '').strip()
    senha = d.get('senha') or ''
    if not login or not senha:
        return jsonify({'ok': False, 'message': 'Preencha login e senha'}), 400
    db = get_db()
    user = db.execute(
        "SELECT * FROM usuarios WHERE login=? AND senha_hash=? AND ativo=1",
        (login, hash_pw(senha))).fetchone()
    if not user:
        return jsonify({'ok': False, 'message': 'Login ou senha incorretos'}), 401
    perms = get_user_permissions(user['id'])
    session['user_id']    = user['id']
    session['user_nome']  = user['nome']
    session['papel']      = user['papel']
    session['permissions']= perms
    return jsonify({'ok': True, 'nome': user['nome'], 'papel': user['papel'], 'permissions': perms})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/auth/me')
def api_me():
    uid = session.get('user_id')
    if not uid: return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'id': uid,
                    'nome': session.get('user_nome'),
                    'papel': session.get('papel'),
                    'permissions': session.get('permissions', [])})

@app.route('/api/auth/change_password', methods=['POST'])
@require_auth
def api_change_password():
    d = request.json or {}
    uid = session['user_id']
    db = get_db()
    user = db.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
    if user['senha_hash'] != hash_pw(d.get('senha_atual','')):
        return jsonify({'ok': False, 'message': 'Senha atual incorreta'}), 400
    nova = d.get('nova_senha','')
    if len(nova) < 4:
        return jsonify({'ok': False, 'message': 'Nova senha: mínimo 4 caracteres'}), 400
    db.execute("UPDATE usuarios SET senha_hash=? WHERE id=?", (hash_pw(nova), uid))
    db.commit()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════
@app.route('/')
@require_auth
def index():
    return render_template('index.html')

# ══════════════════════════════════════════════════════════════════════════
# API – USUARIOS
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/usuarios', methods=['GET'])
@require_auth
@require_module('usuarios')
def api_usuarios_list():
    db = get_db()
    users = rows_to_list(db.execute(
        "SELECT id,nome,login,papel,ativo,criado_em FROM usuarios WHERE ativo=1 ORDER BY nome").fetchall())
    for u in users:
        u['permissoes'] = [r['modulo'] for r in db.execute(
            "SELECT modulo FROM usuario_permissoes WHERE usuario_id=?", (u['id'],)).fetchall()]
    return jsonify(users)

@app.route('/api/usuarios', methods=['POST'])
@require_auth
@require_module('usuarios')
def api_usuario_create():
    db = get_db()
    d = request.json or {}
    login = (d.get('login') or '').strip()
    if not login or not d.get('nome') or not d.get('senha'):
        return jsonify({'ok': False, 'message': 'Nome, login e senha são obrigatórios'}), 400
    if db.execute("SELECT id FROM usuarios WHERE login=?", (login,)).fetchone():
        return jsonify({'ok': False, 'message': 'Login já existe'}), 400
    cur = db.execute("INSERT INTO usuarios(nome,login,senha_hash,papel) VALUES(?,?,?,?)",
                     (d['nome'], login, hash_pw(d['senha']), d.get('papel','operador')))
    uid = cur.lastrowid
    perms = ALL_MODULES if d.get('papel') == 'admin' else d.get('permissoes', [])
    for m in perms:
        db.execute("INSERT OR IGNORE INTO usuario_permissoes(usuario_id,modulo) VALUES(?,?)", (uid, m))
    db.commit()
    return jsonify({'ok': True, 'id': uid})

@app.route('/api/usuarios/<int:uid>', methods=['PUT'])
@require_auth
@require_module('usuarios')
def api_usuario_update(uid):
    db = get_db()
    d = request.json or {}
    admins = db.execute("SELECT COUNT(*) as c FROM usuarios WHERE papel='admin' AND ativo=1").fetchone()['c']
    target = db.execute("SELECT papel FROM usuarios WHERE id=?", (uid,)).fetchone()
    if target and target['papel']=='admin' and d.get('papel')!='admin' and admins<=1:
        return jsonify({'ok': False, 'message': 'Não é possível remover o último administrador'}), 400
    db.execute("UPDATE usuarios SET nome=?,login=?,papel=?,ativo=? WHERE id=?",
               (d['nome'], d['login'], d.get('papel','operador'), d.get('ativo',1), uid))
    if d.get('senha'):
        if len(d['senha']) < 4:
            return jsonify({'ok': False, 'message': 'Senha: mínimo 4 caracteres'}), 400
        db.execute("UPDATE usuarios SET senha_hash=? WHERE id=?", (hash_pw(d['senha']), uid))
    db.execute("DELETE FROM usuario_permissoes WHERE usuario_id=?", (uid,))
    perms = ALL_MODULES if d.get('papel') == 'admin' else d.get('permissoes', [])
    for m in perms:
        db.execute("INSERT OR IGNORE INTO usuario_permissoes(usuario_id,modulo) VALUES(?,?)", (uid, m))
    db.commit()
    if uid == session['user_id']:
        session['user_nome']   = d['nome']
        session['papel']       = d.get('papel','operador')
        session['permissions'] = perms
    return jsonify({'ok': True})

@app.route('/api/usuarios/<int:uid>', methods=['DELETE'])
@require_auth
@require_module('usuarios')
def api_usuario_delete(uid):
    if uid == session['user_id']:
        return jsonify({'ok': False, 'message': 'Não pode excluir o próprio usuário'}), 400
    db = get_db()
    admins = db.execute("SELECT COUNT(*) as c FROM usuarios WHERE papel='admin' AND ativo=1").fetchone()['c']
    target = db.execute("SELECT papel FROM usuarios WHERE id=?", (uid,)).fetchone()
    if target and target['papel']=='admin' and admins<=1:
        return jsonify({'ok': False, 'message': 'Não é possível remover o último administrador'}), 400
    db.execute("UPDATE usuarios SET ativo=0, login=login || '_del_' || id WHERE id=?", (uid,))
    db.commit()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════════════════════
# API – Dashboard
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/dashboard')
@require_auth
@require_module('dashboard')
def api_dashboard():
    db = get_db()
    hoje = date.today().isoformat()
    mes_ini = date.today().replace(day=1).isoformat()
    v_hoje  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE date(criado_em)=?", (hoje,)).fetchone()['t']
    v_mes   = db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE date(criado_em)>=?", (mes_ini,)).fetchone()['t']
    v_count = db.execute("SELECT COUNT(*) as c FROM vendas WHERE date(criado_em)>=?", (mes_ini,)).fetchone()['c']
    os_ab   = db.execute("SELECT COUNT(*) as c FROM ordens_servico WHERE status NOT IN ('CONCLUIDA','CANCELADA')").fetchone()['c']
    os_mes  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM ordens_servico WHERE date(criado_em)>=? AND status='CONCLUIDA'", (mes_ini,)).fetchone()['t']
    desp    = db.execute("SELECT COALESCE(SUM(valor),0) as t FROM despesas WHERE date(data)>=?", (mes_ini,)).fetchone()['t']
    prod_bx = db.execute("SELECT COUNT(*) as c FROM produtos WHERE estoque<=estoque_minimo AND ativo=1").fetchone()['c']
    receita = v_mes + os_mes
    v7d = rows_to_list(db.execute(
        "SELECT date(criado_em) as dia,COALESCE(SUM(total),0) as total FROM vendas WHERE date(criado_em)>=date('now','-6 days') GROUP BY dia ORDER BY dia").fetchall())
    top = rows_to_list(db.execute(
        "SELECT p.nome,SUM(vi.quantidade) as qtd,SUM(vi.subtotal) as total FROM venda_itens vi JOIN produtos p ON p.id=vi.produto_id GROUP BY vi.produto_id ORDER BY qtd DESC LIMIT 5").fetchall())
    return jsonify({'vendas_hoje':v_hoje,'vendas_mes':v_mes,'vendas_count':v_count,
                    'os_abertas':os_ab,'os_mes':os_mes,'despesas_mes':desp,
                    'receita_mes':receita,'lucro_mes':receita-desp,
                    'prod_estoque_baixo':prod_bx,'vendas_7d':v7d,'top_produtos':top})

# ══════════════════════════════════════════════════════════════════════════
# API – Categorias
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/categorias')
@require_auth
def api_categorias():
    return jsonify(rows_to_list(get_db().execute("SELECT * FROM categorias ORDER BY nome").fetchall()))

# ══════════════════════════════════════════════════════════════════════════
# API – Produtos
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/produtos', methods=['GET'])
@require_auth
@require_module('produtos', 'pdv', 'vendas')
def api_produtos_list():
    db=get_db(); q=request.args.get('q',''); cat=request.args.get('categoria',''); baixo=request.args.get('estoque_baixo','')
    sql="SELECT p.*,c.nome as categoria_nome FROM produtos p LEFT JOIN categorias c ON c.id=p.categoria_id WHERE p.ativo=1"; params=[]
    if q: sql+=" AND (p.nome LIKE ? OR p.codigo LIKE ?)"; params+=[f'%{q}%']*2
    if cat: sql+=" AND p.categoria_id=?"; params.append(cat)
    if baixo: sql+=" AND p.estoque<=p.estoque_minimo"
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY p.nome',params).fetchall()))

@app.route('/api/produtos', methods=['POST'])
@require_auth
@require_module('produtos')
def api_produto_create():
    db=get_db(); d=request.json
    db.execute("INSERT INTO produtos(codigo,nome,descricao,categoria_id,preco_custo,preco_venda,estoque,estoque_minimo,unidade) VALUES(?,?,?,?,?,?,?,?,?)",
               (d.get('codigo'),d['nome'],d.get('descricao'),d.get('categoria_id'),d.get('preco_custo',0),d.get('preco_venda',0),d.get('estoque',0),d.get('estoque_minimo',0),d.get('unidade','UN')))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/produtos/<int:pid>', methods=['PUT'])
@require_auth
@require_module('produtos')
def api_produto_update(pid):
    db=get_db(); d=request.json
    db.execute("UPDATE produtos SET codigo=?,nome=?,descricao=?,categoria_id=?,preco_custo=?,preco_venda=?,estoque=?,estoque_minimo=?,unidade=? WHERE id=?",
               (d.get('codigo'),d['nome'],d.get('descricao'),d.get('categoria_id'),d.get('preco_custo',0),d.get('preco_venda',0),d.get('estoque',0),d.get('estoque_minimo',0),d.get('unidade','UN'),pid))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/produtos/<int:pid>', methods=['DELETE'])
@require_auth
@require_module('produtos')
def api_produto_delete(pid):
    db=get_db(); db.execute("UPDATE produtos SET ativo=0 WHERE id=?",(pid,)); db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Clientes
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/clientes', methods=['GET'])
@require_auth
@require_module('clientes', 'pdv', 'vendas')
def api_clientes_list():
    db=get_db(); q=request.args.get('q','')
    sql="SELECT * FROM clientes WHERE 1=1"; params=[]
    if q: sql+=" AND (nome LIKE ? OR cpf_cnpj LIKE ? OR telefone LIKE ?)"; params+=[f'%{q}%']*3
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY nome',params).fetchall()))

@app.route('/api/clientes', methods=['POST'])
@require_auth
@require_module('clientes')
def api_cliente_create():
    db=get_db(); d=request.json
    db.execute("INSERT INTO clientes(nome,cpf_cnpj,telefone,email,endereco) VALUES(?,?,?,?,?)",
               (d['nome'],d.get('cpf_cnpj'),d.get('telefone'),d.get('email'),d.get('endereco'))); db.commit(); return jsonify({'ok':True})

@app.route('/api/clientes/<int:cid>', methods=['PUT'])
@require_auth
@require_module('clientes')
def api_cliente_update(cid):
    db=get_db(); d=request.json
    db.execute("UPDATE clientes SET nome=?,cpf_cnpj=?,telefone=?,email=?,endereco=? WHERE id=?",
               (d['nome'],d.get('cpf_cnpj'),d.get('telefone'),d.get('email'),d.get('endereco'),cid)); db.commit(); return jsonify({'ok':True})

@app.route('/api/clientes/<int:cid>', methods=['DELETE'])
@require_auth
@require_module('clientes')
def api_cliente_delete(cid):
    db=get_db(); db.execute("DELETE FROM clientes WHERE id=?",(cid,)); db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Vendas
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/vendas', methods=['GET'])
@require_auth
@require_module('vendas')
def api_vendas_list():
    db=get_db(); di=request.args.get('data_ini',''); df=request.args.get('data_fim','')
    status=request.args.get('status',''); q=request.args.get('q','')
    sql="SELECT * FROM vendas WHERE 1=1"; params=[]
    if di: sql+=" AND date(criado_em)>=?"; params.append(di)
    if df: sql+=" AND date(criado_em)<=?"; params.append(df)
    if status: sql+=" AND status=?"; params.append(status)
    if q: sql+=" AND (numero LIKE ? OR cliente_nome LIKE ?)"; params+=[f'%{q}%']*2
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY criado_em DESC LIMIT 200',params).fetchall()))

@app.route('/api/vendas', methods=['POST'])
@require_auth
@require_module('pdv')
def api_venda_create():
    db=get_db(); d=request.json; numero=next_number('VND','vendas','numero')
    cur=db.execute("INSERT INTO vendas(numero,cliente_id,cliente_nome,vendedor_id,vendedor_nome,subtotal,desconto,total,forma_pagamento,status,observacao) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (numero,d.get('cliente_id'),d.get('cliente_nome',''),d.get('vendedor_id'),d.get('vendedor_nome',''),d.get('subtotal',0),d.get('desconto',0),d.get('total',0),d.get('forma_pagamento','DINHEIRO'),d.get('status','CONCLUIDA'),d.get('observacao','')))
    vid=cur.lastrowid
    for it in d.get('itens',[]):
        db.execute("INSERT INTO venda_itens(venda_id,produto_id,produto_nome,quantidade,preco_unitario,desconto,subtotal) VALUES(?,?,?,?,?,?,?)",
                   (vid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it.get('desconto',0),it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?",(it['quantidade'],it['produto_id']))
    db.commit(); return jsonify({'ok':True,'numero':numero,'id':vid})

@app.route('/api/vendas/<int:vid>', methods=['GET'])
@require_auth
@require_module('vendas')
def api_venda_get(vid):
    db=get_db()
    v=db.execute("SELECT * FROM vendas WHERE id=?",(vid,)).fetchone()
    return jsonify({'venda':dict(v),'itens':rows_to_list(db.execute("SELECT * FROM venda_itens WHERE venda_id=?",(vid,)).fetchall())})

@app.route('/api/vendas/<int:vid>/cancelar', methods=['POST'])
@require_auth
@require_module('vendas')
def api_venda_cancelar(vid):
    db=get_db(); d=request.json or {}
    motivo = d.get('motivo', '')
    db.execute("UPDATE vendas SET status='CANCELADA', motivo_cancelamento=? WHERE id=?",(motivo, vid))
    for it in db.execute("SELECT * FROM venda_itens WHERE venda_id=?",(vid,)).fetchall():
        if it['produto_id']: db.execute("UPDATE produtos SET estoque=estoque+? WHERE id=?",(it['quantidade'],it['produto_id']))
    db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – OS
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/os', methods=['GET'])
@require_auth
@require_module('os')
def api_os_list():
    db=get_db(); status=request.args.get('status',''); q=request.args.get('q','')
    di=request.args.get('data_ini',''); df=request.args.get('data_fim','')
    sql="SELECT * FROM ordens_servico WHERE 1=1"; params=[]
    if status: sql+=" AND status=?"; params.append(status)
    if q: sql+=" AND (numero LIKE ? OR cliente_nome LIKE ? OR equipamento LIKE ?)"; params+=[f'%{q}%']*3
    if di: sql+=" AND date(criado_em)>=?"; params.append(di)
    if df: sql+=" AND date(criado_em)<=?"; params.append(df)
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY criado_em DESC LIMIT 200',params).fetchall()))

@app.route('/api/os', methods=['POST'])
@require_auth
@require_module('os')
def api_os_create():
    db=get_db(); d=request.json; numero=next_number('OS','ordens_servico','numero')
    
    # Suporte para novo cliente inline
    cid = d.get('cliente_id')
    cnome = d.get('cliente_nome','')
    if d.get('novo_cliente'):
        nc = d['novo_cliente']
        cur_c = db.execute("INSERT INTO clientes(nome,cpf_cnpj,telefone) VALUES(?,?,?)",
                           (nc['nome'], nc.get('cpf_cnpj',''), nc.get('telefone','')))
        cid = cur_c.lastrowid
        cnome = nc['nome']

    cur=db.execute("INSERT INTO ordens_servico(numero,cliente_id,cliente_nome,equipamento,problema,tecnico,status,prioridade,previsao,valor_servico,valor_pecas,desconto,total,forma_pagamento,observacao,checklist,senha_padrao,senha_pin,cliente_cpf,cliente_telefone) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (numero,cid,cnome,d.get('equipamento',''),d.get('problema',''),d.get('tecnico',''),d.get('status','ABERTA'),d.get('prioridade','NORMAL'),d.get('previsao'),d.get('valor_servico',0),d.get('valor_pecas',0),d.get('desconto',0),d.get('total',0),d.get('forma_pagamento','DINHEIRO'),d.get('observacao',''),d.get('checklist',''),d.get('senha_padrao',''),d.get('senha_pin',''),d.get('cliente_cpf',''),d.get('cliente_telefone','')))
    oid=cur.lastrowid
    for it in d.get('itens',[]):
        db.execute("INSERT INTO os_itens(os_id,produto_id,produto_nome,quantidade,preco_unitario,subtotal) VALUES(?,?,?,?,?,?)",
                   (oid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?",(it['quantidade'],it['produto_id']))
    db.commit(); return jsonify({'ok':True,'numero':numero,'id':oid})

@app.route('/api/os/<int:oid>', methods=['GET'])
@require_auth
@require_module('os')
def api_os_get(oid):
    db=get_db()
    o=db.execute("SELECT * FROM ordens_servico WHERE id=?",(oid,)).fetchone()
    return jsonify({'os':dict(o),'itens':rows_to_list(db.execute("SELECT * FROM os_itens WHERE os_id=?",(oid,)).fetchall())})

@app.route('/api/os/<int:oid>', methods=['PUT'])
@require_auth
@require_module('os')
def api_os_update(oid):
    db=get_db(); d=request.json
    db.execute("UPDATE ordens_servico SET cliente_id=?, cliente_nome=?, equipamento=?, problema=?, diagnostico=?, solucao=?, tecnico=?, status=?, prioridade=?, previsao=?, valor_servico=?, valor_pecas=?, desconto=?, total=?, forma_pagamento=?, observacao=?, checklist=?, senha_padrao=?, senha_pin=?, cliente_cpf=?, cliente_telefone=?, atualizado_em=(datetime('now','localtime')) WHERE id=?",
               (d.get('cliente_id'), d.get('cliente_nome'), d.get('equipamento',''), d.get('problema',''), d.get('diagnostico',''), d.get('solucao',''), d.get('tecnico',''), d.get('status','ABERTA'), d.get('prioridade','NORMAL'), d.get('previsao'), d.get('valor_servico',0), d.get('valor_pecas',0), d.get('desconto',0), d.get('total',0), d.get('forma_pagamento','DINHEIRO'), d.get('observacao',''), d.get('checklist',''), d.get('senha_padrao',''), d.get('senha_pin',''), d.get('cliente_cpf',''), d.get('cliente_telefone',''), oid))
    db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Financeiro
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/despesas', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_despesas_list():
    db=get_db(); di=request.args.get('data_ini',''); df=request.args.get('data_fim',''); cat=request.args.get('categoria','')
    sql="SELECT * FROM despesas WHERE 1=1"; params=[]
    if di: sql+=" AND date(data)>=?"; params.append(di)
    if df: sql+=" AND date(data)<=?"; params.append(df)
    if cat: sql+=" AND categoria=?"; params.append(cat)
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY data DESC LIMIT 200',params).fetchall()))

@app.route('/api/despesas', methods=['POST'])
@require_auth
@require_module('financeiro')
def api_despesa_create():
    db=get_db(); d=request.json
    db.execute("INSERT INTO despesas(descricao,categoria,valor,data,forma_pagamento,observacao) VALUES(?,?,?,?,?,?)",
               (d['descricao'],d.get('categoria','GERAL'),d['valor'],d['data'],d.get('forma_pagamento','DINHEIRO'),d.get('observacao','')))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/despesas/<int:did>', methods=['DELETE'])
@require_auth
@require_module('financeiro')
def api_despesa_delete(did):
    db=get_db(); db.execute("DELETE FROM despesas WHERE id=?",(did,)); db.commit(); return jsonify({'ok':True})

@app.route('/api/compras', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_compras_list():
    db=get_db(); di=request.args.get('data_ini',''); df=request.args.get('data_fim','')
    sql="SELECT * FROM compras WHERE 1=1"; params=[]
    if di: sql+=" AND date(data)>=?"; params.append(di)
    if df: sql+=" AND date(data)<=?"; params.append(df)
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY data DESC LIMIT 200',params).fetchall()))

@app.route('/api/compras', methods=['POST'])
@require_auth
@require_module('financeiro')
def api_compra_create():
    db=get_db(); d=request.json
    cur=db.execute("INSERT INTO compras(numero_nota,fornecedor,total,data,observacao) VALUES(?,?,?,?,?)",
                   (d.get('numero_nota',''),d.get('fornecedor',''),d.get('total',0),d['data'],d.get('observacao','')))
    cid=cur.lastrowid
    for it in d.get('itens',[]):
        db.execute("INSERT INTO compra_itens(compra_id,produto_id,produto_nome,quantidade,preco_unitario,subtotal) VALUES(?,?,?,?,?,?)",
                   (cid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque+?,preco_custo=? WHERE id=?",(it['quantidade'],it['preco_unitario'],it['produto_id']))
    db.commit(); return jsonify({'ok':True,'id':cid})

# ══════════════════════════════════════════════════════════════════════════
# API – Vendedores
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/vendedores', methods=['GET'])
@require_auth
def api_vendedores_list():
    db=get_db()
    return jsonify(rows_to_list(db.execute("SELECT * FROM vendedores WHERE ativo=1 ORDER BY nome").fetchall()))

@app.route('/api/vendedores', methods=['POST'])
@require_auth
@require_module('settings')
def api_vendedor_create():
    db=get_db(); d=request.json
    db.execute("INSERT INTO vendedores(nome) VALUES(?)", (d['nome'],))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/vendedores/<int:vid>', methods=['PUT'])
@require_auth
@require_module('settings')
def api_vendedor_update(vid):
    db=get_db(); d=request.json
    db.execute("UPDATE vendedores SET nome=?, ativo=? WHERE id=?",
               (d['nome'], d.get('ativo', 1), vid))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/vendedores/<int:vid>', methods=['DELETE'])
@require_auth
@require_module('settings')
def api_vendedor_delete(vid):
    db=get_db(); db.execute("UPDATE vendedores SET ativo=0 WHERE id=?", (vid,))
    db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Contas a Receber
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/contas_receber', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_contas_receber_list():
    db=get_db()
    status=request.args.get('status','')
    cliente_id=request.args.get('cliente_id','')
    di=request.args.get('data_ini','')
    df=request.args.get('data_fim','')
    
    sql="""SELECT cr.*, c.nome as cliente_nome, 
           (SELECT COALESCE(SUM(valor_pago), 0) FROM recebimentos WHERE conta_id=cr.id) as total_recebido
           FROM contas_receber cr 
           LEFT JOIN clientes c ON c.id=cr.cliente_id 
           WHERE 1=1"""
    params=[]
    if status: sql+=" AND cr.status=?"; params.append(status)
    if cliente_id: sql+=" AND cr.cliente_id=?"; params.append(cliente_id)
    if di: sql+=" AND date(cr.data_vencimento)>=?"; params.append(di)
    if df: sql+=" AND date(cr.data_vencimento)<=?"; params.append(df)
    
    contas = rows_to_list(db.execute(sql+' ORDER BY cr.data_vencimento ASC LIMIT 500', params).fetchall())
    
    hoje = date.today().isoformat()
    for c in contas:
        if c['status'] != 'PAGA' and c['data_vencimento'] < hoje:
            c['atrasada'] = True
        else:
            c['atrasada'] = False
            
    return jsonify(contas)

@app.route('/api/contas_receber', methods=['POST'])
@require_auth
@require_module('financeiro')
def api_contas_receber_create():
    db=get_db(); d=request.json
    cliente_id = d.get('cliente_id')
    
    if not cliente_id and d.get('novo_cliente'):
        nc = d['novo_cliente']
        cur_c = db.execute("INSERT INTO clientes(nome,cpf_cnpj,telefone) VALUES(?,?,?)",
                           (nc['nome'], nc.get('cpf_cnpj',''), nc.get('telefone','')))
        cliente_id = cur_c.lastrowid
        
    cur=db.execute("INSERT INTO contas_receber(cliente_id, descricao, valor_total, data_vencimento, status) VALUES(?,?,?,?,?)",
                   (cliente_id, d['descricao'], d['valor_total'], d['data_vencimento'], 'PENDENTE'))
    db.commit()
    return jsonify({'ok':True, 'id': cur.lastrowid})

@app.route('/api/contas_receber/<int:cid>', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_contas_receber_get(cid):
    db=get_db()
    c = db.execute('''SELECT cr.*, cl.nome as cliente_nome 
                      FROM contas_receber cr 
                      LEFT JOIN clientes cl ON cl.id=cr.cliente_id 
                      WHERE cr.id=?''', (cid,)).fetchone()
    if not c: return jsonify({'ok': False, 'error': 'Not found'}), 404
    
    recebimentos = rows_to_list(db.execute("SELECT * FROM recebimentos WHERE conta_id=? ORDER BY data_pagamento ASC", (cid,)).fetchall())
    total_recebido = sum(r['valor_pago'] for r in recebimentos)
    
    conta_dict = dict(c)
    conta_dict['total_recebido'] = total_recebido
    return jsonify({'conta': conta_dict, 'recebimentos': recebimentos})

@app.route('/api/contas_receber/<int:cid>/recebimento', methods=['POST'])
@require_auth
@require_module('financeiro')
def api_contas_receber_pay(cid):
    db=get_db(); d=request.json
    valor_pago = float(d['valor_pago'])
    
    conta = db.execute("SELECT * FROM contas_receber WHERE id=?", (cid,)).fetchone()
    if not conta: return jsonify({'ok': False, 'error': 'Not found'}), 404
        
    db.execute("INSERT INTO recebimentos(conta_id, valor_pago, data_pagamento, forma_pagamento) VALUES(?,?,?,?)",
               (cid, valor_pago, d['data_pagamento'], d.get('forma_pagamento', 'DINHEIRO')))
               
    total_recebido = db.execute("SELECT COALESCE(SUM(valor_pago), 0) as t FROM recebimentos WHERE conta_id=?", (cid,)).fetchone()['t']
    
    novo_status = 'PARCIAL'
    if total_recebido >= conta['valor_total']: novo_status = 'PAGA'
        
    db.execute("UPDATE contas_receber SET status=?, atualizado_em=(datetime('now','localtime')) WHERE id=?", (novo_status, cid))
    db.commit()
    return jsonify({'ok':True, 'novo_status': novo_status, 'total_recebido': total_recebido})

@app.route('/api/contas_receber/<int:cid>', methods=['DELETE'])
@require_auth
@require_module('financeiro')
def api_contas_receber_delete(cid):
    db=get_db()
    db.execute("DELETE FROM contas_receber WHERE id=?", (cid,))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/contas_receber/dashboard', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_contas_receber_dashboard():
    db=get_db()
    hoje = date.today().isoformat()
    mes_ini = date.today().replace(day=1).isoformat()
    
    pendentes = db.execute('''
        SELECT SUM(valor_total - (SELECT COALESCE(SUM(valor_pago),0) FROM recebimentos WHERE conta_id=cr.id)) as t 
        FROM contas_receber cr WHERE cr.status != 'PAGA'
    ''').fetchone()['t'] or 0
    
    vencido = db.execute('''
        SELECT SUM(valor_total - (SELECT COALESCE(SUM(valor_pago),0) FROM recebimentos WHERE conta_id=cr.id)) as t 
        FROM contas_receber cr WHERE cr.status != 'PAGA' AND date(cr.data_vencimento) < ?
    ''', (hoje,)).fetchone()['t'] or 0
    
    recebido_hoje = db.execute("SELECT COALESCE(SUM(valor_pago),0) as t FROM recebimentos WHERE date(data_pagamento) = ?", (hoje,)).fetchone()['t'] or 0
    recebido_mes = db.execute("SELECT COALESCE(SUM(valor_pago),0) as t FROM recebimentos WHERE date(data_pagamento) >= ?", (mes_ini,)).fetchone()['t'] or 0
    
    return jsonify({
        'total_a_receber': pendentes,
        'vencido': vencido,
        'recebido_hoje': recebido_hoje,
        'recebido_mes': recebido_mes
    })

# ══════════════════════════════════════════════════════════════════════════
# API – Relatórios
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/relatorios/vendas')
@require_auth
@require_module('relatorios')
def rel_vendas():
    db=get_db()
    di=request.args.get('data_ini',date.today().replace(day=1).isoformat())
    df=request.args.get('data_fim',date.today().isoformat())
    ag=request.args.get('agrupamento','dia')
    vid=request.args.get('vendedor_id','')
    
    where = "status='CONCLUIDA' AND date(criado_em) BETWEEN ? AND ?"
    params = [di, df]
    if vid:
        where += " AND vendedor_id = ?"
        params.append(int(vid))
        
    where_itens = "v.status='CONCLUIDA' AND date(v.criado_em) BETWEEN ? AND ?"
    params_itens = [di, df]
    if vid:
        where_itens += " AND v.vendedor_id = ?"
        params_itens.append(int(vid))

    fmt2 = {"mes":"strftime('%Y-%m',criado_em)","semana":"strftime('%Y-W%W',criado_em)"}.get(ag,"date(criado_em)")
    resumo=rows_to_list(db.execute(f"SELECT {fmt2} as periodo,COUNT(*) as qtd_vendas,SUM(total) as total,SUM(desconto) as desconto,AVG(total) as ticket_medio FROM vendas WHERE {where} GROUP BY periodo ORDER BY periodo", params).fetchall())
    formas=rows_to_list(db.execute(f"SELECT forma_pagamento,COUNT(*) as qtd,SUM(total) as total FROM vendas WHERE {where} GROUP BY forma_pagamento", params).fetchall())
    top=rows_to_list(db.execute(f"SELECT vi.produto_nome,SUM(vi.quantidade) as qtd,SUM(vi.subtotal) as total FROM venda_itens vi JOIN vendas v ON v.id=vi.venda_id WHERE {where_itens} GROUP BY vi.produto_nome ORDER BY total DESC LIMIT 20", params_itens).fetchall())
    totais=dict(db.execute(f"SELECT COUNT(*) as qtd,COALESCE(SUM(total),0) as total,COALESCE(SUM(desconto),0) as desconto FROM vendas WHERE {where}", params).fetchone())
    return jsonify({'resumo':resumo,'formas_pagamento':formas,'top_produtos':top,'totais':totais})

@app.route('/api/relatorios/financeiro')
@require_auth
@require_module('relatorios')
def rel_financeiro():
    db=get_db()
    di=request.args.get('data_ini',date.today().replace(day=1).isoformat())
    df=request.args.get('data_fim',date.today().isoformat())
    rv=db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE status='CONCLUIDA' AND date(criado_em) BETWEEN ? AND ?",(di,df)).fetchone()['t']
    ros=db.execute("SELECT COALESCE(SUM(total),0) as t FROM ordens_servico WHERE status='CONCLUIDA' AND date(criado_em) BETWEEN ? AND ?",(di,df)).fetchone()['t']
    desp=db.execute("SELECT COALESCE(SUM(valor),0) as t FROM despesas WHERE date(data) BETWEEN ? AND ?",(di,df)).fetchone()['t']
    comp=db.execute("SELECT COALESCE(SUM(total),0) as t FROM compras WHERE date(data) BETWEEN ? AND ?",(di,df)).fetchone()['t']
    cat_d=rows_to_list(db.execute("SELECT categoria,SUM(valor) as total FROM despesas WHERE date(data) BETWEEN ? AND ? GROUP BY categoria ORDER BY total DESC",(di,df)).fetchall())
    return jsonify({'receita_vendas':rv,'receita_os':ros,'total_receitas':rv+ros,'total_despesas':desp,'total_compras':comp,'lucro_bruto':rv+ros-desp,'categorias_despesas':cat_d,'evolucao_mensal':[]})

@app.route('/api/relatorios/estoque')
@require_auth
@require_module('relatorios')
def rel_estoque():
    db=get_db()
    rows=db.execute("SELECT p.*,c.nome as categoria_nome,(p.estoque*p.preco_custo) as valor_estoque FROM produtos p LEFT JOIN categorias c ON c.id=p.categoria_id WHERE p.ativo=1 ORDER BY p.nome").fetchall()
    total_val=sum(r['valor_estoque'] or 0 for r in rows)
    return jsonify({'produtos':rows_to_list(rows),'valor_total_estoque':total_val,'produtos_estoque_baixo':[dict(r) for r in rows if r['estoque']<=r['estoque_minimo']]})

# ══════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    db_existed = os.path.exists(DB_PATH)
    init_db()
    if not db_existed:
        run_setup_wizard()
    port = 5678
    print(f"🚀 GestãoLoja em http://localhost:{port}")
    print(f"   Admin: admin / admin123")
    threading.Timer(1.2, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
