import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
import hashlib
import secrets
import threading
import webbrowser
from datetime import datetime, date
from functools import wraps
from flask import (Flask, render_template, request, jsonify, g,
                   session, redirect)
from dotenv import load_dotenv

load_dotenv()

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

DB_URL = os.getenv('DB_URL', 'postgresql://postgres:hzqegUOcjhT1oqw0Gxfn4F3oQh1u1JdJ@localhost:5432/minhaloja_db')

app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=data_path('static'))
app.secret_key = os.getenv('SECRET_KEY', 'gestao-loja-secret-key-2024-xK9pL')

ALL_MODULES = ['dashboard','pdv','vendas','os','produtos',
               'clientes','financeiro','relatorios','usuarios', 'settings']

# ── Database ───────────────────────────────────────────────────────────────
class PostgresWrapper:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        # Transforma o placeholder do sqlite '?' para postgres '%s'
        q = query.replace('?', '%s')
        cur = self.conn.cursor()
        if params is not None:
            cur.execute(q, params)
        else:
            cur.execute(q)
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def get_db():
    if 'db' not in g:
        raw_db = psycopg2.connect(DB_URL, cursor_factory=DictCursor)
        raw_db.autocommit = False
        g.db = PostgresWrapper(raw_db)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # We omit 'usuarios' table because we will use 'tenant_usuarios' from superadmin instead
    # However, since this original app still depends on 'config' and standard modules,
    # we inject 'tenant_id' inside the legacy tables.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS config (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        chave TEXT NOT NULL,
        valor TEXT,
        UNIQUE(tenant_id, chave)
    );
    CREATE TABLE IF NOT EXISTS categorias (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        UNIQUE(tenant_id, nome)
    );
    CREATE TABLE IF NOT EXISTS produtos (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        codigo TEXT,
        nome TEXT NOT NULL,
        descricao TEXT,
        categoria_id INTEGER REFERENCES categorias(id),
        preco_custo DECIMAL(10,2) DEFAULT 0,
        preco_venda DECIMAL(10,2) DEFAULT 0,
        estoque DECIMAL DEFAULT 0,
        estoque_minimo DECIMAL DEFAULT 0,
        unidade TEXT DEFAULT 'UN',
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT NOW(),
        UNIQUE(tenant_id, codigo)
    );
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        cpf_cnpj TEXT,
        telefone TEXT,
        email TEXT,
        endereco TEXT,
        criado_em TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS vendedores (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS vendas (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        numero TEXT,
        cliente_id INTEGER REFERENCES clientes(id),
        cliente_nome TEXT,
        vendedor_id INTEGER REFERENCES vendedores(id),
        vendedor_nome TEXT,
        subtotal DECIMAL(10,2) DEFAULT 0,
        desconto DECIMAL(10,2) DEFAULT 0,
        total DECIMAL(10,2) DEFAULT 0,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        status TEXT DEFAULT 'CONCLUIDA',
        observacao TEXT,
        motivo_cancelamento TEXT,
        criado_em TIMESTAMP DEFAULT NOW(),
        UNIQUE(tenant_id, numero)
    );
    CREATE TABLE IF NOT EXISTS venda_itens (
        id SERIAL PRIMARY KEY,
        venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
        produto_id INTEGER REFERENCES produtos(id),
        produto_nome TEXT,
        quantidade DECIMAL(10,2) NOT NULL,
        preco_unitario DECIMAL(10,2) NOT NULL,
        desconto DECIMAL(10,2) DEFAULT 0,
        subtotal DECIMAL(10,2) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ordens_servico (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        numero TEXT,
        cliente_id INTEGER REFERENCES clientes(id),
        cliente_nome TEXT,
        cliente_cpf TEXT,
        cliente_telefone TEXT,
        equipamento TEXT,
        problema TEXT,
        diagnostico TEXT,
        solucao TEXT,
        tecnico TEXT,
        status TEXT DEFAULT 'ABERTA',
        prioridade TEXT DEFAULT 'NORMAL',
        previsao TEXT,
        valor_servico DECIMAL(10,2) DEFAULT 0,
        valor_pecas DECIMAL(10,2) DEFAULT 0,
        desconto DECIMAL(10,2) DEFAULT 0,
        total DECIMAL(10,2) DEFAULT 0,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        observacao TEXT,
        checklist TEXT,
        senha_padrao TEXT,
        senha_pin TEXT,
        criado_em TIMESTAMP DEFAULT NOW(),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        UNIQUE(tenant_id, numero)
    );
    CREATE TABLE IF NOT EXISTS os_itens (
        id SERIAL PRIMARY KEY,
        os_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
        produto_id INTEGER REFERENCES produtos(id),
        produto_nome TEXT,
        quantidade DECIMAL(10,2) NOT NULL,
        preco_unitario DECIMAL(10,2) NOT NULL,
        subtotal DECIMAL(10,2) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS despesas (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        descricao TEXT NOT NULL,
        categoria TEXT DEFAULT 'GERAL',
        valor DECIMAL(10,2) NOT NULL,
        data DATE NOT NULL,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        observacao TEXT,
        criado_em TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS compras (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        numero_nota TEXT,
        fornecedor TEXT,
        total DECIMAL(10,2) DEFAULT 0,
        data DATE NOT NULL,
        observacao TEXT,
        criado_em TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS compra_itens (
        id SERIAL PRIMARY KEY,
        compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
        produto_id INTEGER REFERENCES produtos(id),
        produto_nome TEXT,
        quantidade DECIMAL(10,2) NOT NULL,
        preco_unitario DECIMAL(10,2) NOT NULL,
        subtotal DECIMAL(10,2) NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contas_receber (
        id SERIAL PRIMARY KEY,
        tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
        cliente_id INTEGER REFERENCES clientes(id),
        descricao TEXT NOT NULL,
        valor_total DECIMAL(10,2) NOT NULL,
        data_vencimento DATE NOT NULL,
        status TEXT DEFAULT 'PENDENTE',
        criado_em TIMESTAMP DEFAULT NOW(),
        atualizado_em TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS recebimentos (
        id SERIAL PRIMARY KEY,
        conta_id INTEGER NOT NULL REFERENCES contas_receber(id) ON DELETE CASCADE,
        valor_pago DECIMAL(10,2) NOT NULL,
        data_pagamento DATE NOT NULL,
        forma_pagamento TEXT DEFAULT 'DINHEIRO',
        criado_em TIMESTAMP DEFAULT NOW()
    );
    """)
    conn.commit()

    # We do NOT run sqlite migrations like 'db_migrate(conn)' or seed static categories here.
    # Seed categories can be done dynamically when creating a tenant inside the superadmin.
    conn.close()

# Nenhuma db_migrate() ou run_setup_wizard() necessária no modelo SaaS, 
# pois isso é gerido pelo Painel do Superadmin agora.# ── Helpers ────────────────────────────────────────────────────────────────
def rows_to_list(rows):
    return [dict(r) for r in rows]

def next_number(prefix, table, col):
    db = get_db()
    tenant_id = session.get('tenant_id')
    n = (db.execute(f"SELECT COUNT(*) as c FROM {table} WHERE tenant_id=%s", (tenant_id,)).fetchone()['c'] or 0) + 1
    return f"{prefix}{str(n).zfill(6)}"

def get_user_permissions(user_id):
    # No SQL superadmin original model, permissions are defined by the global role.
    # Because we migrated to `tenant_usuarios`, we will simplify it relying on their 'papel'.
    return ALL_MODULES

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('tenant_id') or not session.get('user_id'):
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
    tenant_id = session.get('tenant_id')
    for k, v in data.items():
        db.execute("INSERT INTO config (tenant_id, chave, valor) VALUES (?, ?, ?) ON CONFLICT (tenant_id, chave) DO UPDATE SET valor = EXCLUDED.valor", 
                   (tenant_id, k, v))
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
    
    # Busca agora em tenant_usuarios global do painel
    user = db.execute(
        "SELECT * FROM tenant_usuarios WHERE login=? AND senha_hash=? AND ativo=True",
        (login, hash_pw(senha))).fetchone()
        
    if not user:
        return jsonify({'ok': False, 'message': 'Login ou senha incorretos ou acessos desativados'}), 401
    
    # Checa também se o tenant dele está ativo
    tenant = db.execute("SELECT status FROM tenants WHERE id=?", (user['tenant_id'],)).fetchone()
    if not tenant or tenant['status'] != 'ATIVO':
        return jsonify({'ok': False, 'message': 'Sua loja está bloqueada no sistema. Contate o administrador.'}), 403
        
    session['user_id']    = user['id']
    session['tenant_id']  = user['tenant_id'] # Guardando o núcleo da loja
    session['user_nome']  = user['nome']
    session['papel']      = user['papel']
    session['permissions']= ALL_MODULES
    return jsonify({'ok': True, 'nome': user['nome'], 'papel': user['papel'], 'permissions': ALL_MODULES})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/auth/me')
def api_me():
    uid = session.get('user_id')
    if not uid: return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'id': uid,
                    'tenant_id': session.get('tenant_id'),
                    'nome': session.get('user_nome'),
                    'papel': session.get('papel'),
                    'permissions': ALL_MODULES})

@app.route('/api/auth/change_password', methods=['POST'])
@require_auth
def api_change_password():
    d = request.json or {}
    uid = session['user_id']
    tid = session['tenant_id']
    db = get_db()
    user = db.execute("SELECT * FROM tenant_usuarios WHERE id=? AND tenant_id=?", (uid, tid)).fetchone()
    if user['senha_hash'] != hash_pw(d.get('senha_atual','')):
        return jsonify({'ok': False, 'message': 'Senha atual incorreta'}), 400
    nova = d.get('nova_senha','')
    if len(nova) < 4:
        return jsonify({'ok': False, 'message': 'Nova senha: mínimo 4 caracteres'}), 400
    db.execute("UPDATE tenant_usuarios SET senha_hash=? WHERE id=?", (hash_pw(nova), uid))
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
    tid = session.get('tenant_id')
    users = rows_to_list(db.execute(
        "SELECT id,nome,login,papel,ativo,criado_em FROM tenant_usuarios WHERE tenant_id=? AND ativo=True ORDER BY nome", (tid,)).fetchall())
    # Fakes permissions that frontend expects to render properly
    for u in users:
        u['permissoes'] = ALL_MODULES
    return jsonify(users)

@app.route('/api/usuarios', methods=['POST'])
@require_auth
@require_module('usuarios')
def api_usuario_create():
    db = get_db()
    d = request.json or {}
    login = (d.get('login') or '').strip()
    tid = session['tenant_id']
    if not login or not d.get('nome') or not d.get('senha'):
        return jsonify({'ok': False, 'message': 'Nome, login e senha são obrigatórios'}), 400
    if db.execute("SELECT id FROM tenant_usuarios WHERE tenant_id=? AND login=?", (tid, login)).fetchone():
        return jsonify({'ok': False, 'message': 'Login já existe na loja'}), 400
    cur = db.execute("INSERT INTO tenant_usuarios (tenant_id,nome,login,senha_hash,papel) VALUES(?,?,?,?,?) RETURNING id",
                     (tid, d['nome'], login, hash_pw(d['senha']), d.get('papel','operador')))
    uid = cur.fetchone()['id']
    db.commit()
    return jsonify({'ok': True, 'id': uid})

@app.route('/api/usuarios/<int:uid>', methods=['PUT'])
@require_auth
@require_module('usuarios')
def api_usuario_update(uid):
    db = get_db()
    d = request.json or {}
    tid = session['tenant_id']
    admins = db.execute("SELECT COUNT(*) as c FROM tenant_usuarios WHERE tenant_id=? AND papel='admin' AND ativo=True", (tid,)).fetchone()['c']
    target = db.execute("SELECT papel FROM tenant_usuarios WHERE tenant_id=? AND id=?", (tid, uid)).fetchone()
    if target and target['papel']=='admin' and d.get('papel')!='admin' and admins<=1:
        return jsonify({'ok': False, 'message': 'Não é possível remover o último administrador da loja'}), 400
    
    ativo = True if str(d.get('ativo', 1)) in ['1', 'True', 'true'] else False
    db.execute("UPDATE tenant_usuarios SET nome=?,login=?,papel=?,ativo=? WHERE tenant_id=? AND id=?",
               (d['nome'], d['login'], d.get('papel','operador'), ativo, tid, uid))
    if d.get('senha'):
        if len(d['senha']) < 4:
            return jsonify({'ok': False, 'message': 'Senha: mínimo 4 caracteres'}), 400
        db.execute("UPDATE tenant_usuarios SET senha_hash=? WHERE tenant_id=? AND id=?", (hash_pw(d['senha']), tid, uid))
    db.commit()
    if uid == session['user_id']:
        session['user_nome']   = d['nome']
        session['papel']       = d.get('papel','operador')
    return jsonify({'ok': True})

@app.route('/api/usuarios/<int:uid>', methods=['DELETE'])
@require_auth
@require_module('usuarios')
def api_usuario_delete(uid):
    if uid == session['user_id']:
        return jsonify({'ok': False, 'message': 'Não pode excluir o próprio usuário'}), 400
    db = get_db()
    tid = session['tenant_id']
    admins = db.execute("SELECT COUNT(*) as c FROM tenant_usuarios WHERE tenant_id=? AND papel='admin' AND ativo=True", (tid,)).fetchone()['c']
    target = db.execute("SELECT papel FROM tenant_usuarios WHERE tenant_id=? AND id=?", (tid, uid)).fetchone()
    if target and target['papel']=='admin' and admins<=1:
        return jsonify({'ok': False, 'message': 'Não é possível remover o último administrador da loja'}), 400
    db.execute("UPDATE tenant_usuarios SET ativo=False, login=login || '_del_' || id::text WHERE tenant_id=? AND id=?", (tid, uid))
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
    tid = session['tenant_id']
    hoje = date.today().isoformat()
    mes_ini = date.today().replace(day=1).isoformat()
    v_hoje  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE tenant_id=? AND date(criado_em)=?", (tid, hoje)).fetchone()['t']
    v_mes   = db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE tenant_id=? AND date(criado_em)>=?", (tid, mes_ini)).fetchone()['t']
    v_count = db.execute("SELECT COUNT(*) as c FROM vendas WHERE tenant_id=? AND date(criado_em)>=?", (tid, mes_ini)).fetchone()['c']
    os_ab   = db.execute("SELECT COUNT(*) as c FROM ordens_servico WHERE tenant_id=? AND status NOT IN ('CONCLUIDA','CANCELADA')", (tid,)).fetchone()['c']
    os_mes  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM ordens_servico WHERE tenant_id=? AND date(criado_em)>=? AND status='CONCLUIDA'", (tid, mes_ini)).fetchone()['t']
    desp    = db.execute("SELECT COALESCE(SUM(valor),0) as t FROM despesas WHERE tenant_id=? AND date(data)>=?", (tid, mes_ini)).fetchone()['t']
    prod_bx = db.execute("SELECT COUNT(*) as c FROM produtos WHERE tenant_id=? AND estoque<=estoque_minimo AND ativo=1", (tid,)).fetchone()['c']
    receita = v_mes + os_mes
    v7d = rows_to_list(db.execute(
        "SELECT date(criado_em) as dia,COALESCE(SUM(total),0) as total FROM vendas WHERE tenant_id=? AND date(criado_em)>=date('now','-6 days') GROUP BY dia ORDER BY dia", (tid,)).fetchall())
    top = rows_to_list(db.execute(
        "SELECT p.nome,SUM(vi.quantidade) as qtd,SUM(vi.subtotal) as total FROM venda_itens vi JOIN produtos p ON p.id=vi.produto_id WHERE p.tenant_id=? GROUP BY vi.produto_id ORDER BY qtd DESC LIMIT 5", (tid,)).fetchall())
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
    tid = session['tenant_id']
    return jsonify(rows_to_list(get_db().execute("SELECT * FROM categorias WHERE tenant_id=? ORDER BY nome", (tid,)).fetchall()))

# ══════════════════════════════════════════════════════════════════════════
# API – Produtos
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/produtos', methods=['GET'])
@require_auth
@require_module('produtos', 'pdv', 'vendas')
def api_produtos_list():
    db=get_db(); q=request.args.get('q',''); cat=request.args.get('categoria',''); baixo=request.args.get('estoque_baixo','')
    tid=session['tenant_id']
    sql="SELECT p.*,c.nome as categoria_nome FROM produtos p LEFT JOIN categorias c ON c.id=p.categoria_id WHERE p.tenant_id=? AND p.ativo=1"; params=[tid]
    if q: sql+=" AND (p.nome LIKE ? OR p.codigo LIKE ?)"; params+=[f'%{q}%']*2
    if cat: sql+=" AND p.categoria_id=?"; params.append(cat)
    if baixo: sql+=" AND p.estoque<=p.estoque_minimo"
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY p.nome',params).fetchall()))

@app.route('/api/produtos', methods=['POST'])
@require_auth
@require_module('produtos')
def api_produto_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("INSERT INTO produtos(tenant_id,codigo,nome,descricao,categoria_id,preco_custo,preco_venda,estoque,estoque_minimo,unidade) VALUES(?,?,?,?,?,?,?,?,?,?)",
               (tid,d.get('codigo'),d['nome'],d.get('descricao'),d.get('categoria_id'),d.get('preco_custo',0),d.get('preco_venda',0),d.get('estoque',0),d.get('estoque_minimo',0),d.get('unidade','UN')))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/produtos/<int:pid>', methods=['PUT'])
@require_auth
@require_module('produtos')
def api_produto_update(pid):
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("UPDATE produtos SET codigo=?,nome=?,descricao=?,categoria_id=?,preco_custo=?,preco_venda=?,estoque=?,estoque_minimo=?,unidade=? WHERE tenant_id=? AND id=?",
               (d.get('codigo'),d['nome'],d.get('descricao'),d.get('categoria_id'),d.get('preco_custo',0),d.get('preco_venda',0),d.get('estoque',0),d.get('estoque_minimo',0),d.get('unidade','UN'),tid,pid))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/produtos/<int:pid>', methods=['DELETE'])
@require_auth
@require_module('produtos')
def api_produto_delete(pid):
    db=get_db(); tid=session['tenant_id']
    db.execute("UPDATE produtos SET ativo=0 WHERE tenant_id=? AND id=?",(tid,pid)); db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Clientes
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/clientes', methods=['GET'])
@require_auth
@require_module('clientes', 'pdv', 'vendas')
def api_clientes_list():
    db=get_db(); q=request.args.get('q',''); tid=session['tenant_id']
    sql="SELECT * FROM clientes WHERE tenant_id=?"; params=[tid]
    if q: sql+=" AND (nome LIKE ? OR cpf_cnpj LIKE ? OR telefone LIKE ?)"; params+=[f'%{q}%']*3
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY nome',params).fetchall()))

@app.route('/api/clientes', methods=['POST'])
@require_auth
@require_module('clientes')
def api_cliente_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("INSERT INTO clientes(tenant_id,nome,cpf_cnpj,telefone,email,endereco) VALUES(?,?,?,?,?,?)",
               (tid,d['nome'],d.get('cpf_cnpj'),d.get('telefone'),d.get('email'),d.get('endereco'))); db.commit(); return jsonify({'ok':True})

@app.route('/api/clientes/<int:cid>', methods=['PUT'])
@require_auth
@require_module('clientes')
def api_cliente_update(cid):
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("UPDATE clientes SET nome=?,cpf_cnpj=?,telefone=?,email=?,endereco=? WHERE tenant_id=? AND id=?",
               (d['nome'],d.get('cpf_cnpj'),d.get('telefone'),d.get('email'),d.get('endereco'),tid,cid)); db.commit(); return jsonify({'ok':True})

@app.route('/api/clientes/<int:cid>', methods=['DELETE'])
@require_auth
@require_module('clientes')
def api_cliente_delete(cid):
    db=get_db(); tid=session['tenant_id']
    db.execute("DELETE FROM clientes WHERE tenant_id=? AND id=?",(tid,cid)); db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Vendas
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/vendas', methods=['GET'])
@require_auth
@require_module('vendas')
def api_vendas_list():
    db=get_db(); di=request.args.get('data_ini',''); df=request.args.get('data_fim','')
    status=request.args.get('status',''); q=request.args.get('q','')
    tid=session['tenant_id']
    sql="SELECT * FROM vendas WHERE tenant_id=?"; params=[tid]
    if di: sql+=" AND date(criado_em)>=?"; params.append(di)
    if df: sql+=" AND date(criado_em)<=?"; params.append(df)
    if status: sql+=" AND status=?"; params.append(status)
    if q: sql+=" AND (numero LIKE ? OR cliente_nome LIKE ?)"; params+=[f'%{q}%']*2
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY criado_em DESC LIMIT 200',params).fetchall()))

@app.route('/api/vendas', methods=['POST'])
@require_auth
@require_module('pdv')
def api_venda_create():
    db=get_db(); d=request.json; numero=next_number('VND','vendas','numero'); tid=session['tenant_id']
    cur=db.execute("INSERT INTO vendas(tenant_id,numero,cliente_id,cliente_nome,vendedor_id,vendedor_nome,subtotal,desconto,total,forma_pagamento,status,observacao) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
                   (tid,numero,d.get('cliente_id'),d.get('cliente_nome',''),d.get('vendedor_id'),d.get('vendedor_nome',''),d.get('subtotal',0),d.get('desconto',0),d.get('total',0),d.get('forma_pagamento','DINHEIRO'),d.get('status','CONCLUIDA'),d.get('observacao','')))
    vid=cur.fetchone()['id']
    for it in d.get('itens',[]):
        db.execute("INSERT INTO venda_itens(venda_id,produto_id,produto_nome,quantidade,preco_unitario,desconto,subtotal) VALUES(?,?,?,?,?,?,?)",
                   (vid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it.get('desconto',0),it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque-? WHERE tenant_id=? AND id=?",(it['quantidade'],tid,it['produto_id']))
    db.commit(); return jsonify({'ok':True,'numero':numero,'id':vid})

@app.route('/api/vendas/<int:vid>', methods=['GET'])
@require_auth
@require_module('vendas')
def api_venda_get(vid):
    db=get_db(); tid=session['tenant_id']
    v=db.execute("SELECT * FROM vendas WHERE tenant_id=? AND id=?",(tid,vid)).fetchone()
    if not v: return jsonify({'error':'Not found'}), 404
    return jsonify({'venda':dict(v),'itens':rows_to_list(db.execute("SELECT * FROM venda_itens WHERE venda_id=?",(vid,)).fetchall())})

@app.route('/api/vendas/<int:vid>/cancelar', methods=['POST'])
@require_auth
@require_module('vendas')
def api_venda_cancelar(vid):
    db=get_db(); d=request.json or {}; tid=session['tenant_id']
    motivo = d.get('motivo', '')
    
    # Valida existencia do tenant filter no update
    db.execute("UPDATE vendas SET status='CANCELADA', motivo_cancelamento=? WHERE tenant_id=? AND id=?",(motivo, tid, vid))
    for it in db.execute("SELECT vi.* FROM venda_itens vi JOIN vendas v ON v.id=vi.venda_id WHERE v.tenant_id=? AND v.id=?",(tid, vid,)).fetchall():
        if it['produto_id']: db.execute("UPDATE produtos SET estoque=estoque+? WHERE tenant_id=? AND id=?",(it['quantidade'],tid,it['produto_id']))
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
    tid=session['tenant_id']
    sql="SELECT * FROM ordens_servico WHERE tenant_id=?"; params=[tid]
    if status: sql+=" AND status=?"; params.append(status)
    if q: sql+=" AND (numero LIKE ? OR cliente_nome LIKE ? OR equipamento LIKE ?)"; params+=[f'%{q}%']*3
    if di: sql+=" AND date(criado_em)>=?"; params.append(di)
    if df: sql+=" AND date(criado_em)<=?"; params.append(df)
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY criado_em DESC LIMIT 200',params).fetchall()))

@app.route('/api/os', methods=['POST'])
@require_auth
@require_module('os')
def api_os_create():
    db=get_db(); d=request.json; numero=next_number('OS','ordens_servico','numero'); tid=session['tenant_id']
    
    # Suporte para novo cliente inline
    cid = d.get('cliente_id')
    cnome = d.get('cliente_nome','')
    if d.get('novo_cliente'):
        nc = d['novo_cliente']
        cur_c = db.execute("INSERT INTO clientes(tenant_id,nome,cpf_cnpj,telefone) VALUES(?,?,?,?) RETURNING id",
                           (tid, nc['nome'], nc.get('cpf_cnpj',''), nc.get('telefone','')))
        cid = cur_c.fetchone()['id']
        cnome = nc['nome']

    cur=db.execute("INSERT INTO ordens_servico(tenant_id,numero,cliente_id,cliente_nome,equipamento,problema,tecnico,status,prioridade,previsao,valor_servico,valor_pecas,desconto,total,forma_pagamento,observacao,checklist,senha_padrao,senha_pin,cliente_cpf,cliente_telefone) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
                   (tid,numero,cid,cnome,d.get('equipamento',''),d.get('problema',''),d.get('tecnico',''),d.get('status','ABERTA'),d.get('prioridade','NORMAL'),d.get('previsao'),d.get('valor_servico',0),d.get('valor_pecas',0),d.get('desconto',0),d.get('total',0),d.get('forma_pagamento','DINHEIRO'),d.get('observacao',''),d.get('checklist',''),d.get('senha_padrao',''),d.get('senha_pin',''),d.get('cliente_cpf',''),d.get('cliente_telefone','')))
    oid=cur.fetchone()['id']
    for it in d.get('itens',[]):
        db.execute("INSERT INTO os_itens(os_id,produto_id,produto_nome,quantidade,preco_unitario,subtotal) VALUES(?,?,?,?,?,?)",
                   (oid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque-? WHERE tenant_id=? AND id=?",(it['quantidade'],tid,it['produto_id']))
    db.commit(); return jsonify({'ok':True,'numero':numero,'id':oid})

@app.route('/api/os/<int:oid>', methods=['GET'])
@require_auth
@require_module('os')
def api_os_get(oid):
    db=get_db(); tid=session['tenant_id']
    o=db.execute("SELECT * FROM ordens_servico WHERE tenant_id=? AND id=?",(tid,oid)).fetchone()
    if not o: return jsonify({'error':'Not found'}), 404
    return jsonify({'os':dict(o),'itens':rows_to_list(db.execute("SELECT * FROM os_itens WHERE os_id=?",(oid,)).fetchall())})

@app.route('/api/os/<int:oid>', methods=['PUT'])
@require_auth
@require_module('os')
def api_os_update(oid):
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("UPDATE ordens_servico SET cliente_id=?, cliente_nome=?, equipamento=?, problema=?, diagnostico=?, solucao=?, tecnico=?, status=?, prioridade=?, previsao=?, valor_servico=?, valor_pecas=?, desconto=?, total=?, forma_pagamento=?, observacao=?, checklist=?, senha_padrao=?, senha_pin=?, cliente_cpf=?, cliente_telefone=?, atualizado_em=(NOW()) WHERE tenant_id=? AND id=?",
               (d.get('cliente_id'), d.get('cliente_nome'), d.get('equipamento',''), d.get('problema',''), d.get('diagnostico',''), d.get('solucao',''), d.get('tecnico',''), d.get('status','ABERTA'), d.get('prioridade','NORMAL'), d.get('previsao'), d.get('valor_servico',0), d.get('valor_pecas',0), d.get('desconto',0), d.get('total',0), d.get('forma_pagamento','DINHEIRO'), d.get('observacao',''), d.get('checklist',''), d.get('senha_padrao',''), d.get('senha_pin',''), d.get('cliente_cpf',''), d.get('cliente_telefone',''), tid, oid))
    db.commit(); return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════════════════════
# API – Financeiro
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/despesas', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_despesas_list():
    db=get_db(); di=request.args.get('data_ini',''); df=request.args.get('data_fim',''); cat=request.args.get('categoria','')
    tid=session['tenant_id']
    sql="SELECT * FROM despesas WHERE tenant_id=?"; params=[tid]
    if di: sql+=" AND date(data)>=?"; params.append(di)
    if df: sql+=" AND date(data)<=?"; params.append(df)
    if cat: sql+=" AND categoria=?"; params.append(cat)
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY data DESC LIMIT 200',params).fetchall()))

@app.route('/api/despesas', methods=['POST'])
@require_auth
@require_module('financeiro')
def api_despesa_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("INSERT INTO despesas(tenant_id,descricao,categoria,valor,data,forma_pagamento,observacao) VALUES(?,?,?,?,?,?,?)",
               (tid,d['descricao'],d.get('categoria','GERAL'),d['valor'],d['data'],d.get('forma_pagamento','DINHEIRO'),d.get('observacao','')))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/despesas/<int:did>', methods=['DELETE'])
@require_auth
@require_module('financeiro')
def api_despesa_delete(did):
    db=get_db(); tid=session['tenant_id']
    db.execute("DELETE FROM despesas WHERE tenant_id=? AND id=?",(tid,did)); db.commit(); return jsonify({'ok':True})

@app.route('/api/compras', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_compras_list():
    db=get_db(); di=request.args.get('data_ini',''); df=request.args.get('data_fim','')
    tid=session['tenant_id']
    sql="SELECT * FROM compras WHERE tenant_id=?"; params=[tid]
    if di: sql+=" AND date(data)>=?"; params.append(di)
    if df: sql+=" AND date(data)<=?"; params.append(df)
    return jsonify(rows_to_list(db.execute(sql+' ORDER BY data DESC LIMIT 200',params).fetchall()))

@app.route('/api/compras', methods=['POST'])
@require_auth
@require_module('financeiro')
def api_compra_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    cur=db.execute("INSERT INTO compras(tenant_id,numero_nota,fornecedor,total,data,observacao) VALUES(?,?,?,?,?,?) RETURNING id",
                   (tid,d.get('numero_nota',''),d.get('fornecedor',''),d.get('total',0),d['data'],d.get('observacao','')))
    cid=cur.fetchone()['id']
    for it in d.get('itens',[]):
        db.execute("INSERT INTO compra_itens(compra_id,produto_id,produto_nome,quantidade,preco_unitario,subtotal) VALUES(?,?,?,?,?,?)",
                   (cid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque+?,preco_custo=? WHERE tenant_id=? AND id=?",(it['quantidade'],it['preco_unitario'],tid,it['produto_id']))
    db.commit(); return jsonify({'ok':True,'id':cid})

# ══════════════════════════════════════════════════════════════════════════
# API – Vendedores
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/vendedores', methods=['GET'])
@require_auth
def api_vendedores_list():
    db=get_db(); tid=session['tenant_id']
    return jsonify(rows_to_list(db.execute("SELECT * FROM vendedores WHERE tenant_id=? AND ativo=1 ORDER BY nome", (tid,)).fetchall()))

@app.route('/api/vendedores', methods=['POST'])
@require_auth
@require_module('settings')
def api_vendedor_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("INSERT INTO vendedores(tenant_id,nome) VALUES(?,?)", (tid,d['nome']))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/vendedores/<int:vid>', methods=['PUT'])
@require_auth
@require_module('settings')
def api_vendedor_update(vid):
    db=get_db(); d=request.json; tid=session['tenant_id']
    db.execute("UPDATE vendedores SET nome=?, ativo=? WHERE tenant_id=? AND id=?",
               (d['nome'], d.get('ativo', 1), tid, vid))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/vendedores/<int:vid>', methods=['DELETE'])
@require_auth
@require_module('settings')
def api_vendedor_delete(vid):
    db=get_db(); tid=session['tenant_id']
    db.execute("UPDATE vendedores SET ativo=0 WHERE tenant_id=? AND id=?", (tid, vid))
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
    tid = session['tenant_id']
    
    sql="""SELECT cr.*, c.nome as cliente_nome, 
           (SELECT COALESCE(SUM(valor_pago), 0) FROM recebimentos WHERE conta_id=cr.id) as total_recebido
           FROM contas_receber cr 
           LEFT JOIN clientes c ON c.id=cr.cliente_id 
           WHERE cr.tenant_id=?"""
    params=[tid]
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
    db=get_db(); d=request.json; tid=session['tenant_id']
    cliente_id = d.get('cliente_id')
    
    if not cliente_id and d.get('novo_cliente'):
        nc = d['novo_cliente']
        cur_c = db.execute("INSERT INTO clientes(tenant_id,nome,cpf_cnpj,telefone) VALUES(?,?,?,?) RETURNING id",
                           (tid, nc['nome'], nc.get('cpf_cnpj',''), nc.get('telefone','')))
        cliente_id = cur_c.fetchone()['id']
        
    cur=db.execute("INSERT INTO contas_receber(tenant_id, cliente_id, descricao, valor_total, data_vencimento, status) VALUES(?,?,?,?,?,?) RETURNING id",
                   (tid, cliente_id, d['descricao'], d['valor_total'], d['data_vencimento'], 'PENDENTE'))
    db.commit()
    return jsonify({'ok':True, 'id': cur.fetchone()['id']})

@app.route('/api/contas_receber/<int:cid>', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_contas_receber_get(cid):
    db=get_db(); tid=session['tenant_id']
    c = db.execute('''SELECT cr.*, cl.nome as cliente_nome 
                      FROM contas_receber cr 
                      LEFT JOIN clientes cl ON cl.id=cr.cliente_id 
                      WHERE cr.tenant_id=? AND cr.id=?''', (tid, cid)).fetchone()
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
    db=get_db(); d=request.json; tid=session['tenant_id']
    valor_pago = float(d['valor_pago'])
    
    conta = db.execute("SELECT * FROM contas_receber WHERE tenant_id=? AND id=?", (tid, cid)).fetchone()
    if not conta: return jsonify({'ok': False, 'error': 'Not found'}), 404
        
    db.execute("INSERT INTO recebimentos(conta_id, valor_pago, data_pagamento, forma_pagamento) VALUES(?,?,?,?)",
               (cid, valor_pago, d['data_pagamento'], d.get('forma_pagamento', 'DINHEIRO')))
               
    total_recebido = db.execute("SELECT COALESCE(SUM(valor_pago), 0) as t FROM recebimentos WHERE conta_id=?", (cid,)).fetchone()['t']
    
    novo_status = 'PARCIAL'
    if total_recebido >= conta['valor_total']: novo_status = 'PAGA'
        
    db.execute("UPDATE contas_receber SET status=?, atualizado_em=(NOW()) WHERE id=? AND tenant_id=?", (novo_status, cid, tid))
    db.commit()
    return jsonify({'ok':True, 'novo_status': novo_status, 'total_recebido': total_recebido})

@app.route('/api/contas_receber/<int:cid>', methods=['DELETE'])
@require_auth
@require_module('financeiro')
def api_contas_receber_delete(cid):
    db=get_db(); tid=session['tenant_id']
    db.execute("DELETE FROM contas_receber WHERE tenant_id=? AND id=?", (tid, cid))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/contas_receber/dashboard', methods=['GET'])
@require_auth
@require_module('financeiro')
def api_contas_receber_dashboard():
    db=get_db(); tid=session['tenant_id']
    hoje = date.today().isoformat()
    mes_ini = date.today().replace(day=1).isoformat()
    
    pendentes = db.execute('''
        SELECT SUM(valor_total - (SELECT COALESCE(SUM(valor_pago),0) FROM recebimentos WHERE conta_id=cr.id)) as t 
        FROM contas_receber cr WHERE cr.tenant_id=? AND cr.status != 'PAGA'
    ''', (tid,)).fetchone()['t'] or 0
    
    vencido = db.execute('''
        SELECT SUM(valor_total - (SELECT COALESCE(SUM(valor_pago),0) FROM recebimentos WHERE conta_id=cr.id)) as t 
        FROM contas_receber cr WHERE cr.tenant_id=? AND cr.status != 'PAGA' AND date(cr.data_vencimento) < ?
    ''', (tid, hoje)).fetchone()['t'] or 0
    
    # Received joins with contas_receber to check tenant
    recebido_hoje = db.execute('''
        SELECT COALESCE(SUM(r.valor_pago),0) as t 
        FROM recebimentos r JOIN contas_receber cr ON cr.id=r.conta_id 
        WHERE cr.tenant_id=? AND date(r.data_pagamento) = ?
    ''', (tid, hoje)).fetchone()['t'] or 0
    
    recebido_mes = db.execute('''
        SELECT COALESCE(SUM(r.valor_pago),0) as t 
        FROM recebimentos r JOIN contas_receber cr ON cr.id=r.conta_id 
        WHERE cr.tenant_id=? AND date(r.data_pagamento) >= ?
    ''', (tid, mes_ini)).fetchone()['t'] or 0
    
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
    db=get_db(); tid=session['tenant_id']
    di=request.args.get('data_ini',date.today().replace(day=1).isoformat())
    df=request.args.get('data_fim',date.today().isoformat())
    ag=request.args.get('agrupamento','dia')
    vid=request.args.get('vendedor_id','')
    
    where = "tenant_id=? AND status='CONCLUIDA' AND date(criado_em) BETWEEN ? AND ?"
    params = [tid, di, df]
    if vid:
        where += " AND vendedor_id = ?"
        params.append(int(vid))
        
    where_itens = "v.tenant_id=? AND v.status='CONCLUIDA' AND date(v.criado_em) BETWEEN ? AND ?"
    params_itens = [tid, di, df]
    if vid:
        where_itens += " AND v.vendedor_id = ?"
        params_itens.append(int(vid))

    fmt2 = {"mes":"to_char(criado_em, 'YYYY-MM')","semana":"to_char(criado_em, 'IYYY-IW')"}.get(ag,"date(criado_em)::text")
    resumo=rows_to_list(db.execute(f"SELECT {fmt2} as periodo,COUNT(*) as qtd_vendas,SUM(total) as total,SUM(desconto) as desconto,AVG(total) as ticket_medio FROM vendas WHERE {where} GROUP BY periodo ORDER BY periodo", params).fetchall())
    formas=rows_to_list(db.execute(f"SELECT forma_pagamento,COUNT(*) as qtd,SUM(total) as total FROM vendas WHERE {where} GROUP BY forma_pagamento", params).fetchall())
    top=rows_to_list(db.execute(f"SELECT vi.produto_nome,SUM(vi.quantidade) as qtd,SUM(vi.subtotal) as total FROM venda_itens vi JOIN vendas v ON v.id=vi.venda_id WHERE {where_itens} GROUP BY vi.produto_nome ORDER BY total DESC LIMIT 20", params_itens).fetchall())
    totais=dict(db.execute(f"SELECT COUNT(*) as qtd,COALESCE(SUM(total),0) as total,COALESCE(SUM(desconto),0) as desconto FROM vendas WHERE {where}", params).fetchone())
    return jsonify({'resumo':resumo,'formas_pagamento':formas,'top_produtos':top,'totais':totais})

@app.route('/api/relatorios/financeiro')
@require_auth
@require_module('relatorios')
def rel_financeiro():
    db=get_db(); tid=session['tenant_id']
    di=request.args.get('data_ini',date.today().replace(day=1).isoformat())
    df=request.args.get('data_fim',date.today().isoformat())
    rv=db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE tenant_id=? AND status='CONCLUIDA' AND date(criado_em) BETWEEN ? AND ?",(tid,di,df)).fetchone()['t']
    ros=db.execute("SELECT COALESCE(SUM(total),0) as t FROM ordens_servico WHERE tenant_id=? AND status='CONCLUIDA' AND date(criado_em) BETWEEN ? AND ?",(tid,di,df)).fetchone()['t']
    desp=db.execute("SELECT COALESCE(SUM(valor),0) as t FROM despesas WHERE tenant_id=? AND date(data) BETWEEN ? AND ?",(tid,di,df)).fetchone()['t']
    comp=db.execute("SELECT COALESCE(SUM(total),0) as t FROM compras WHERE tenant_id=? AND date(data) BETWEEN ? AND ?",(tid,di,df)).fetchone()['t']
    cat_d=rows_to_list(db.execute("SELECT categoria,SUM(valor) as total FROM despesas WHERE tenant_id=? AND date(data) BETWEEN ? AND ? GROUP BY categoria ORDER BY total DESC",(tid,di,df)).fetchall())
    return jsonify({'receita_vendas':rv,'receita_os':ros,'total_receitas':rv+ros,'total_despesas':desp,'total_compras':comp,'lucro_bruto':rv+ros-desp,'categorias_despesas':cat_d,'evolucao_mensal':[]})

@app.route('/api/relatorios/estoque')
@require_auth
@require_module('relatorios')
def rel_estoque():
    db=get_db(); tid=session['tenant_id']
    rows=db.execute("SELECT p.*,c.nome as categoria_nome,(p.estoque*p.preco_custo) as valor_estoque FROM produtos p LEFT JOIN categorias c ON c.id=p.categoria_id WHERE p.tenant_id=? AND p.ativo=1 ORDER BY p.nome", (tid,)).fetchall()
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
