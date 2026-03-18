import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
import hashlib
import bcrypt
import secrets
from datetime import datetime, date
from functools import wraps
from flask import (Flask, render_template, request, jsonify, g,
                   session, redirect)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

import traceback
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

DB_URL = os.getenv('DB_URL')
if not DB_URL:
    raise RuntimeError('FATAL: DB_URL environment variable not set. Refusing to start.')

app = Flask(__name__,
            template_folder=resource_path('templates'),
            static_folder=data_path('static'))

_secret = os.getenv('SECRET_KEY')
if not _secret:
    raise RuntimeError('FATAL: SECRET_KEY environment variable not set. Refusing to start.')
app.secret_key = _secret
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Ativar SESSION_COOKIE_SECURE=true no .env apenas se o Nginx tiver HTTPS configurado
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

# Rate Limiter (armazenado em memória; para produção multi-worker use Redis)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
    storage_uri='memory://'
)

ALL_MODULES = ['dashboard','pdv','vendas','os','produtos',
               'clientes','financeiro','receber','relatorios','settings']


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
        try:
            raw_db = psycopg2.connect(DB_URL, cursor_factory=DictCursor, connect_timeout=5)
            raw_db.autocommit = False
            g.db = PostgresWrapper(raw_db)
        except Exception as e:
            print(f"!!! CRITICAL: Database connection failed: {e}")
            raise e
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def hash_pw(pw):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_pw(plain, stored_hash):
    """Verify password, supports bcrypt and legacy SHA-256 (auto-migrates)."""
    try:
        if bcrypt.checkpw(plain.encode('utf-8'), stored_hash.encode('utf-8')):
            return True
    except Exception:
        pass
    legacy = hashlib.sha256(plain.encode()).hexdigest()
    if secrets.compare_digest(legacy, stored_hash):
        return True, 'migrate'
    return False

def init_db():
    print("📋 Tentando inicializar tabelas...")
    try:
        print(f"🔗 Conectando ao DB: {DB_URL[:20]}...")
        raw_db = psycopg2.connect(DB_URL, cursor_factory=DictCursor, connect_timeout=5)
        print("✅ Conexão estabelecida.")
        raw_db.autocommit = True
    except Exception as e:
        print(f"!!! Error in init_db connection: {e}")
        return

    try:
        cur = raw_db.cursor()
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
            maquininha_id INTEGER,
            num_parcelas INTEGER DEFAULT 1,
            taxa_valor DECIMAL(10,2) DEFAULT 0,
            valor_liquido DECIMAL(10,2) DEFAULT 0,
            criado_em TIMESTAMP DEFAULT NOW(),
            UNIQUE(tenant_id, numero)
        );
        CREATE TABLE IF NOT EXISTS maquininhas (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            taxa_debito DECIMAL(5,2) DEFAULT 0,
            taxa_credito_1x DECIMAL(5,2) DEFAULT 0,
            taxa_credito_2x DECIMAL(5,2) DEFAULT 0,
            taxa_credito_3x DECIMAL(5,2) DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT NOW()
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
        CREATE TABLE IF NOT EXISTS pagamento_taxas (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            taxa DECIMAL(5,2) DEFAULT 0,
            UNIQUE(tenant_id, nome)
        );
        CREATE TABLE IF NOT EXISTS contas (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            tipo TEXT DEFAULT 'banco',
            saldo DECIMAL(10,2) DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
            conta_id INTEGER NOT NULL REFERENCES contas(id),
            tipo TEXT NOT NULL,
            valor DECIMAL(10,2) NOT NULL,
            descricao TEXT,
            referencia_tipo TEXT,
            referencia_id INTEGER,
            conta_destino_id INTEGER REFERENCES contas(id),
            criado_em TIMESTAMP DEFAULT NOW()
        );
        """)

        # Migração: adiciona coluna permissoes se não existir
        cur.execute("ALTER TABLE tenant_usuarios ADD COLUMN IF NOT EXISTS permissoes TEXT DEFAULT '';")
        
        # Migração: maquininhas e taxas em vendas
        cur.execute("ALTER TABLE vendas ADD COLUMN IF NOT EXISTS maquininha_id INTEGER;")
        cur.execute("ALTER TABLE vendas ADD COLUMN IF NOT EXISTS num_parcelas INTEGER DEFAULT 1;")
        cur.execute("ALTER TABLE vendas ADD COLUMN IF NOT EXISTS taxa_valor DECIMAL(10,2) DEFAULT 0;")
        cur.execute("ALTER TABLE vendas ADD COLUMN IF NOT EXISTS valor_liquido DECIMAL(10,2) DEFAULT 0;")

        # Migração: novas colunas em maquininhas
        cur.execute("ALTER TABLE maquininhas ADD COLUMN IF NOT EXISTS taxa_credito_1x DECIMAL(5,2) DEFAULT 0;")
        cur.execute("ALTER TABLE maquininhas ADD COLUMN IF NOT EXISTS taxa_credito_2x DECIMAL(5,2) DEFAULT 0;")
        cur.execute("ALTER TABLE maquininhas ADD COLUMN IF NOT EXISTS taxa_credito_3x DECIMAL(5,2) DEFAULT 0;")
        
        # Migração: garante que o login seja único globalmente
        try:
            # Reverte para constraint por tenant, que é mais seguro para multi-tenant
            cur.execute("DROP INDEX IF EXISTS idx_tenant_usuarios_login_global;")
            cur.execute("ALTER TABLE tenant_usuarios ADD CONSTRAINT tenant_usuarios_tenant_id_login_key UNIQUE (tenant_id, login);")
        except Exception as e:
            # Se já existir a constraint, o psql dará erro, mas podemos ignorar se o objetivo for garantir que ela esteja lá
            if 'already exists' not in str(e).lower():
                print(f"⚠️ Aviso na migração de constraints: {e}")
        
        # Migração: contas nas despesas e compras
        cur.execute("ALTER TABLE despesas ADD COLUMN IF NOT EXISTS conta_id INTEGER REFERENCES contas(id);")
        cur.execute("ALTER TABLE compras ADD COLUMN IF NOT EXISTS conta_id INTEGER REFERENCES contas(id);")
        
        # Migração: cria conta Caixa para tenants que ainda não têm nenhuma
        cur.execute("""
            INSERT INTO contas (tenant_id, nome, tipo, saldo)
            SELECT id, 'Caixa', 'caixa', 0 FROM tenants
            WHERE id NOT IN (SELECT DISTINCT tenant_id FROM contas WHERE tenant_id IS NOT NULL)
        """)

        raw_db.commit()
        print("✅ Banco de dados inicializado com sucesso.")
    except Exception as e:
        print(f"!!! Error executing init_db SQL: {e}")
    finally:
        raw_db.close()

# Nenhuma db_migrate() ou run_setup_wizard() necessária no modelo SaaS, 
# pois isso é gerido pelo Painel do Superadmin agora.

# ── Security Headers ───────────────────────────────────────────────────────
@app.after_request
def add_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    resp.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.tailwindcss.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data: blob: *; "
        "connect-src 'self';"
    )
    return resp

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler to return JSON instead of HTML on error."""
    # Se for um erro HTTP padrão (404, 403, 401), deixa o Flask tratar normalmente
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e

    tb = traceback.format_exc()
    print(f"❌ ERROR DETECTED: {e}")
    print(tb)
    return jsonify({
        'ok': False,
        'error': str(e),
        'traceback': tb if os.getenv('FLASK_ENV') == 'development' else None
    }), 500

# ── Helpers ────────────────────────────────────────────────────────────────
def rows_to_list(rows):
    return [dict(r) for r in rows]

# Allowed table names for next_number to prevent SQL injection
_ALLOWED_SEQUENCE_TABLES = frozenset({'vendas', 'ordens_servico', 'compras'})

def next_number(prefix, table, col):
    if table not in _ALLOWED_SEQUENCE_TABLES:
        raise ValueError(f'Invalid table name: {table}')
    db = get_db()
    tenant_id = session.get('tenant_id')
    n = (db.execute(f"SELECT COUNT(*) as c FROM {table} WHERE tenant_id=%s", (tenant_id,)).fetchone()['c'] or 0) + 1
    return f"{prefix}{str(n).zfill(6)}"

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

@app.route('/api/config', methods=['GET'])
@require_auth
def api_get_config():
    db = get_db()
    tid = session.get('tenant_id')
    rows = db.execute("SELECT chave, valor FROM config WHERE tenant_id=?", (tid,)).fetchall()
    return jsonify({r['chave']: r['valor'] for r in rows})

@app.route('/api/debug_db', methods=['GET'])
def api_debug_db():
    db=get_db()
    res = {}
    try:
        # This function is for debugging purposes, it should not be exposed in production
        # and should not contain sensitive logic.
        # The original snippet provided for this function was malformed and seemed to
        # contain code from api_save_config.
        # For now, returning a placeholder.
        return jsonify({'ok': True, 'message': 'Debug endpoint reached. Implement debug logic here.'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

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

@app.route('/api/config/logo', methods=['POST'])
@require_auth
def api_upload_logo():
    if session.get('papel') != 'admin':
        return jsonify({'ok': False, 'error': 'Acesso negado'}), 403
    
    if 'logo' not in request.files:
        return jsonify({'ok': False, 'message': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'ok': False, 'message': 'Nome de arquivo inválido'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        return jsonify({'ok': False, 'message': 'Formato não suportado: use JPG, PNG ou WEBP'}), 400
        
    tenant_id = session.get('tenant_id')
    filename = f"logo_{tenant_id}_{int(datetime.now().timestamp())}{ext}"
    upload_path = os.path.join('static', 'uploads', 'logos')
    os.makedirs(upload_path, exist_ok=True)
    
    full_path = os.path.join(upload_path, filename)
    file.save(full_path)
    
    logo_url = f"/static/uploads/logos/{filename}"
    db = get_db()
    db.execute("INSERT INTO config (tenant_id, chave, valor) VALUES (?, 'shop_logo', ?) "
               "ON CONFLICT (tenant_id, chave) DO UPDATE SET valor = EXCLUDED.valor", 
               (tenant_id, logo_url))
    db.commit()
    return jsonify({'ok': True, 'logo_url': logo_url})

# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════
@app.route('/login')
def login_page():
    if session.get('user_id'): return redirect('/')
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    d = request.json or {}
    login = str(d.get('login') or '').strip().lower()
    senha = str(d.get('senha') or '')
    if not login or not senha or len(login) > 100 or len(senha) > 200:
        return jsonify({'ok': False, 'message': 'Credenciais inválidas'}), 400
    
    login = login.lower()
    # Permitimos login por email ou por username simples (higor)
    # Se contiver @ e ., tratamos como email, mas permitimos passar sem se o usuário já existir no banco.
    db = get_db()

    user = db.execute(
        "SELECT * FROM tenant_usuarios WHERE login=? AND ativo=True",
        (login,)).fetchone()

    if not user:
        return jsonify({'ok': False, 'message': 'Login ou senha incorretos'}), 401

    result = verify_pw(senha, user['senha_hash'])
    if not result:
        return jsonify({'ok': False, 'message': 'Login ou senha incorretos'}), 401

    # Migração transparente de SHA-256 para bcrypt
    if isinstance(result, tuple) and result[1] == 'migrate':
        db.execute("UPDATE tenant_usuarios SET senha_hash=? WHERE id=?",
                   (hash_pw(senha), user['id']))
        db.commit()

    tenant = db.execute("SELECT status FROM tenants WHERE id=?", (user['tenant_id'],)).fetchone()
    if not tenant or tenant['status'] != 'ATIVO':
        return jsonify({'ok': False, 'message': 'Loja bloqueada. Contate o administrador.'}), 403

    # Carrega permissões reais: admin tem tudo, operador tem apenas o que foi configurado
    if user['papel'] == 'admin':
        perms = ALL_MODULES
    else:
        raw = (user.get('permissoes') or '')
        perms = [p for p in raw.split(',') if p.strip()] if raw else []

    session.clear()
    session['user_id']     = user['id']
    session['tenant_id']   = user['tenant_id']
    session['user_nome']   = user['nome']
    session['papel']       = user['papel']
    session['permissions'] = perms
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
                    'tenant_id': session.get('tenant_id'),
                    'nome': session.get('user_nome'),
                    'papel': session.get('papel'),
                    'permissions': session.get('permissions', [])})

@app.route('/api/auth/change_password', methods=['POST'])
@require_auth
@limiter.limit('5 per minute')
def api_change_password():
    d = request.json or {}
    uid = session['user_id']
    tid = session['tenant_id']
    db = get_db()
    user = db.execute("SELECT * FROM tenant_usuarios WHERE id=? AND tenant_id=?", (uid, tid)).fetchone()
    if not user:
        return jsonify({'ok': False, 'message': 'Usuário não encontrado'}), 404
    if not verify_pw(d.get('senha_atual', ''), user['senha_hash']):
        return jsonify({'ok': False, 'message': 'Senha atual incorreta'}), 400
    nova = d.get('nova_senha', '')
    if len(nova) < 8:
        return jsonify({'ok': False, 'message': 'Nova senha: mínimo 8 caracteres'}), 400
    db.execute("UPDATE tenant_usuarios SET senha_hash=? WHERE id=? AND tenant_id=?", (hash_pw(nova), uid, tid))
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
# API – PLANO INFO (usado pelo frontend para montar grid de permissões)
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/plano/info')
@require_auth
def api_plano_info():
    db = get_db()
    tid = session['tenant_id']
    row = db.execute("""
        SELECT p.max_usuarios, p.modulos,
               COUNT(tu.id) as total_usuarios
        FROM tenants t
        JOIN planos p ON p.id = t.plano_id
        LEFT JOIN tenant_usuarios tu ON tu.tenant_id = t.id AND tu.ativo = True
        WHERE t.id = ?
        GROUP BY p.max_usuarios, p.modulos
    """, (tid,)).fetchone()
    if not row:
        # Plano não configurado — retorna tudo liberado
        return jsonify({'max_usuarios': 999, 'modulos': ALL_MODULES, 'total_usuarios': 0})
    modulos_plano = [m.strip() for m in (row['modulos'] or '').split(',') if m.strip()]
    return jsonify({
        'max_usuarios': row['max_usuarios'],
        'modulos': modulos_plano,
        'total_usuarios': row['total_usuarios']
    })

# ══════════════════════════════════════════════════════════════════════════
# API – USUARIOS
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/usuarios', methods=['GET'])
@require_auth
@require_module('settings')
def api_usuarios_list():
    db = get_db()
    tid = session.get('tenant_id')
    users = rows_to_list(db.execute(
        "SELECT id,nome,login,papel,ativo,permissoes,criado_em FROM tenant_usuarios WHERE tenant_id=? ORDER BY nome", (tid,)).fetchall())
    # Converte string CSV de permissoes para lista
    for u in users:
        raw = u.get('permissoes') or ''
        u['permissoes'] = [p for p in raw.split(',') if p.strip()] if raw else []
    return jsonify(users)

def _get_plano_info(db, tid):
    """Retorna (max_usuarios, modulos_lista, total_ativos) do tenant."""
    row = db.execute("""
        SELECT p.max_usuarios, p.modulos,
               COUNT(tu.id) as total_usuarios
        FROM tenants t
        JOIN planos p ON p.id = t.plano_id
        LEFT JOIN tenant_usuarios tu ON tu.tenant_id = t.id AND tu.ativo = True
        WHERE t.id = ?
        GROUP BY p.max_usuarios, p.modulos
    """, (tid,)).fetchone()
    if not row:
        return 999, ALL_MODULES, 0
    modulos = [m.strip() for m in (row['modulos'] or '').split(',') if m.strip()]
    return row['max_usuarios'], modulos, row['total_usuarios']

def _validar_permissoes(perms_enviadas, modulos_plano, papel):
    """Filtra permissões enviadas pelo frontend para apenas os módulos válidos do sistema. Admin não precisa."""
    if papel == 'admin':
        return ''
    validas = [p for p in perms_enviadas if p in ALL_MODULES]
    return ','.join(validas)

@app.route('/api/usuarios', methods=['POST'])
@require_auth
@require_module('settings')
def api_usuario_create():
    db = get_db()
    d = request.json or {}
    login = str(d.get('login') or '').strip()
    nome = str(d.get('nome') or '').strip()
    tid = session['tenant_id']

    if not login or not nome or not d.get('senha'):
        return jsonify({'ok': False, 'message': 'Nome, e-mail e senha são obrigatórios'}), 400
    if len(d['senha']) < 8:
        return jsonify({'ok': False, 'message': 'Senha: mínimo 8 caracteres'}), 400

    # Verifica limite de usuários do plano
    max_u, modulos_plano, total_u = _get_plano_info(db, tid)
    if total_u >= max_u:
        return jsonify({'ok': False, 'message': f'Limite de {max_u} usuários atingido para o seu plano'}), 403

    login = login.lower()
    if '@' not in login or '.' not in login:
        return jsonify({'ok': False, 'message': 'O login deve ser um e-mail válido'}), 400

    if db.execute("SELECT id FROM tenant_usuarios WHERE login=?", (login,)).fetchone():
        return jsonify({'ok': False, 'message': 'Este e-mail já está sendo usado no sistema'}), 400

    papel = d.get('papel', 'operador')
    perms_str = _validar_permissoes(d.get('permissoes', []), modulos_plano, papel)

    cur = db.execute(
        "INSERT INTO tenant_usuarios (tenant_id,nome,login,senha_hash,papel,ativo,permissoes) VALUES(?,?,?,?,?,True,?) RETURNING id",
        (tid, nome, login, hash_pw(d['senha']), papel, perms_str))
    uid = cur.fetchone()['id']
    db.commit()
    return jsonify({'ok': True, 'id': uid})

@app.route('/api/usuarios/<int:uid>', methods=['PUT'])
@require_auth
@require_module('settings')
def api_usuario_update(uid):
    db = get_db()
    d = request.json or {}
    tid = session['tenant_id']

    admins = db.execute("SELECT COUNT(*) as c FROM tenant_usuarios WHERE tenant_id=? AND papel='admin' AND ativo=True", (tid,)).fetchone()['c']
    target = db.execute("SELECT papel FROM tenant_usuarios WHERE tenant_id=? AND id=?", (tid, uid)).fetchone()
    if not target:
        return jsonify({'ok': False, 'message': 'Usuário não encontrado'}), 404
    if target['papel'] == 'admin' and d.get('papel') != 'admin' and admins <= 1:
        return jsonify({'ok': False, 'message': 'Não é possível remover o último administrador da loja'}), 400

    ativo = True if str(d.get('ativo', True)) in ['1', 'True', 'true'] else False
    papel = d.get('papel', 'operador')
    _, modulos_plano, _ = _get_plano_info(db, tid)
    perms_str = _validar_permissoes(d.get('permissoes', []), modulos_plano, papel)

    login = str(d.get('login') or '').strip().lower()
    if login:
        if '@' not in login or '.' not in login:
            return jsonify({'ok': False, 'message': 'O login deve ser um e-mail válido'}), 400
        existe = db.execute("SELECT id FROM tenant_usuarios WHERE login=? AND id != ?", (login, uid)).fetchone()
        if existe:
            return jsonify({'ok': False, 'message': 'Este e-mail já está sendo usado no sistema'}), 400

    db.execute("UPDATE tenant_usuarios SET nome=?,login=?,papel=?,ativo=?,permissoes=? WHERE tenant_id=? AND id=?",
               (d['nome'], login, papel, ativo, perms_str, tid, uid))

    if d.get('senha'):
        senha_str = str(d['senha'])
        if len(senha_str) < 8:
            return jsonify({'ok': False, 'message': 'Senha: mínimo 8 caracteres'}), 400
        db.execute("UPDATE tenant_usuarios SET senha_hash=? WHERE tenant_id=? AND id=?", (hash_pw(d['senha']), tid, uid))

    db.commit()
    if uid == session['user_id']:
        session['user_nome'] = d['nome']
        session['papel'] = papel
        if papel != 'admin':
            session['permissions'] = [p for p in perms_str.split(',') if p]
        else:
            session['permissions'] = ALL_MODULES
    return jsonify({'ok': True})

@app.route('/api/usuarios/<int:uid>', methods=['DELETE'])
@require_auth
@require_module('settings')
def api_usuario_delete(uid):
    if uid == session['user_id']:
        return jsonify({'ok': False, 'message': 'Não pode excluir o próprio usuário'}), 400
    db = get_db()
    tid = session['tenant_id']
    admins = db.execute("SELECT COUNT(*) as c FROM tenant_usuarios WHERE tenant_id=? AND papel='admin' AND ativo=True", (tid,)).fetchone()['c']
    target = db.execute("SELECT papel FROM tenant_usuarios WHERE tenant_id=? AND id=?", (tid, uid)).fetchone()
    if target and target['papel'] == 'admin' and admins <= 1:
        return jsonify({'ok': False, 'message': 'Não é possível remover o último administrador da loja'}), 400
    db.execute("DELETE FROM tenant_usuarios WHERE tenant_id=? AND id=?", (tid, uid))
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
    v_hoje  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE tenant_id=? AND DATE(criado_em)=DATE(?)", (tid, hoje)).fetchone()['t']
    v_mes   = db.execute("SELECT COALESCE(SUM(total),0) as t FROM vendas WHERE tenant_id=? AND DATE(criado_em)>=DATE(?)", (tid, mes_ini)).fetchone()['t']
    v_count = db.execute("SELECT COUNT(*) as c FROM vendas WHERE tenant_id=? AND DATE(criado_em)>=DATE(?)", (tid, mes_ini)).fetchone()['c']
    os_ab   = db.execute("SELECT COUNT(*) as c FROM ordens_servico WHERE tenant_id=? AND status NOT IN ('CONCLUIDA','CANCELADA')", (tid,)).fetchone()['c']
    os_mes  = db.execute("SELECT COALESCE(SUM(total),0) as t FROM ordens_servico WHERE tenant_id=? AND DATE(criado_em)>=DATE(?) AND status='CONCLUIDA'", (tid, mes_ini)).fetchone()['t']
    desp    = db.execute("SELECT COALESCE(SUM(valor),0) as t FROM despesas WHERE tenant_id=? AND DATE(data)>=DATE(?)", (tid, mes_ini)).fetchone()['t']
    prod_bx = db.execute("SELECT COUNT(*) as c FROM produtos WHERE tenant_id=? AND estoque<=estoque_minimo AND ativo=1", (tid,)).fetchone()['c']
    receita = v_mes + os_mes
    v7d = rows_to_list(db.execute(
        "SELECT DATE(criado_em)::text as dia,COALESCE(SUM(total),0) as total FROM vendas WHERE tenant_id=? AND criado_em >= (CURRENT_DATE - INTERVAL '6 days') GROUP BY DATE(criado_em) ORDER BY dia", (tid,)).fetchall())
    top = rows_to_list(db.execute(
        "SELECT p.nome,SUM(vi.quantidade) as qtd,SUM(vi.subtotal) as total FROM venda_itens vi JOIN produtos p ON p.id=vi.produto_id WHERE p.tenant_id=? GROUP BY p.nome ORDER BY qtd DESC LIMIT 5", (tid,)).fetchall())
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
    db = get_db()
    d = request.json
    numero = next_number('VND', 'vendas', 'numero')
    tid = session['tenant_id']
    
    forma_pgto = d.get('forma_pagamento', 'DINHEIRO')
    total = float(d.get('total', 0))
    maquininha_id = d.get('maquininha_id')
    num_parcelas = int(d.get('num_parcelas', 1))
    taxa_valor = 0
    valor_liquido = total

    if maquininha_id and 'CARTÃO' in forma_pgto.upper():
        maq = db.execute("SELECT * FROM maquininhas WHERE tenant_id=? AND id=?", (tid, maquininha_id)).fetchone()
        if maq:
            taxa_perc = 0
            if 'DÉBITO' in forma_pgto.upper():
                taxa_perc = float(maq['taxa_debito'] or 0)
            elif 'CRÉDITO' in forma_pgto.upper():
                if num_parcelas <= 1:
                    taxa_perc = float(maq['taxa_credito_1x'] or 0)
                elif num_parcelas == 2:
                    taxa_perc = float(maq['taxa_credito_2x'] or 0)
                else:
                    taxa_perc = float(maq['taxa_credito_3x'] or 0)
            
            taxa_valor = round(total * (taxa_perc / 100), 2)
            valor_liquido = total - taxa_valor

    cur = db.execute(
        "INSERT INTO vendas(tenant_id,numero,cliente_id,cliente_nome,vendedor_id,vendedor_nome,subtotal,desconto,total,forma_pagamento,status,observacao,maquininha_id,num_parcelas,taxa_valor,valor_liquido) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
        (tid, numero, d.get('cliente_id'), d.get('cliente_nome', ''), d.get('vendedor_id'), d.get('vendedor_nome', ''), 
         d.get('subtotal', 0), d.get('desconto', 0), total, forma_pgto, d.get('status', 'CONCLUIDA'), d.get('observacao', ''),
         maquininha_id, num_parcelas, taxa_valor, valor_liquido)
    )
    vid = cur.fetchone()['id']
    for it in d.get('itens', []):
        db.execute("INSERT INTO venda_itens(venda_id,produto_id,produto_nome,quantidade,preco_unitario,desconto,subtotal) VALUES(?,?,?,?,?,?,?)",
                   (vid, it.get('produto_id'), it['produto_nome'], it['quantidade'], it['preco_unitario'], it.get('desconto', 0), it['subtotal']))
        if it.get('produto_id'):
            db.execute("UPDATE produtos SET estoque=estoque-? WHERE tenant_id=? AND id=?", (it['quantidade'], tid, it['produto_id']))
    # Creditar valor na conta Caixa
    if d.get('status', 'CONCLUIDA') == 'CONCLUIDA' and total > 0:
        caixa_id = _get_caixa_id(db, tid)
        _movimentar(db, tid, caixa_id, 'entrada', total, f'Venda #{numero}', 'venda', vid)
    db.commit()
    return jsonify({'ok': True, 'numero': numero, 'id': vid})

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
    venda = db.execute("SELECT * FROM vendas WHERE tenant_id=? AND id=?", (tid, vid)).fetchone()
    for it in db.execute("SELECT vi.* FROM venda_itens vi JOIN vendas v ON v.id=vi.venda_id WHERE v.tenant_id=? AND v.id=?",(tid, vid,)).fetchall():
        if it['produto_id']: db.execute("UPDATE produtos SET estoque=estoque+? WHERE tenant_id=? AND id=?",(it['quantidade'],tid,it['produto_id']))
    # Reverter valor do caixa no cancelamento
    if venda and float(venda['total']) > 0:
        caixa_id = _get_caixa_id(db, tid)
        saldo_row = db.execute("SELECT saldo FROM contas WHERE id=? AND tenant_id=?", (caixa_id, tid)).fetchone()
        val_cancel = min(float(venda['total']), float(saldo_row['saldo'])) if saldo_row else 0
        if val_cancel > 0:
            db.execute("INSERT INTO movimentacoes(tenant_id,conta_id,tipo,valor,descricao,referencia_tipo,referencia_id) VALUES(?,?,?,?,?,?,?)",
                       (tid, caixa_id, 'saida', val_cancel, f'Cancelamento Venda #{venda["numero"]}', 'venda', vid))
            db.execute("UPDATE contas SET saldo=saldo-? WHERE id=? AND tenant_id=?", (val_cancel, caixa_id, tid))
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
    conta_id = d.get('conta_id')
    valor = float(d.get('valor', 0))
    if not conta_id:
        return jsonify({'ok':False,'error':'Selecione a conta de saída'}), 400
    if valor <= 0:
        return jsonify({'ok':False,'error':'Valor deve ser maior que zero'}), 400
    # Validate balance first
    err = _movimentar.__doc__  # just to check function exists - actual call below
    saldo_row = db.execute("SELECT saldo FROM contas WHERE id=? AND tenant_id=?", (conta_id, tid)).fetchone()
    if not saldo_row or float(saldo_row['saldo']) < valor:
        return jsonify({'ok':False,'error':'Saldo insuficiente na conta selecionada'}), 400
    cur = db.execute("INSERT INTO despesas(tenant_id,descricao,categoria,valor,data,forma_pagamento,observacao,conta_id) VALUES(?,?,?,?,?,?,?,?) RETURNING id",
               (tid,d['descricao'],d.get('categoria','GERAL'),valor,d['data'],d.get('forma_pagamento','DINHEIRO'),d.get('observacao',''),conta_id))
    did = cur.fetchone()['id']
    db.execute("INSERT INTO movimentacoes(tenant_id,conta_id,tipo,valor,descricao,referencia_tipo,referencia_id) VALUES(?,?,?,?,?,?,?)",
               (tid, conta_id, 'saida', valor, f'Despesa: {d["descricao"]}', 'despesa', did))
    db.execute("UPDATE contas SET saldo=saldo-? WHERE id=? AND tenant_id=?", (valor, conta_id, tid))
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
    total = float(d.get('total', 0))
    conta_id = d.get('conta_id')
    if not conta_id:
        return jsonify({'ok':False,'error':'Selecione a conta de saída'}), 400
    saldo_row = db.execute("SELECT saldo FROM contas WHERE id=? AND tenant_id=?", (conta_id, tid)).fetchone()
    if not saldo_row or float(saldo_row['saldo']) < total:
        return jsonify({'ok':False,'error':'Saldo insuficiente na conta selecionada'}), 400
    cur=db.execute("INSERT INTO compras(tenant_id,numero_nota,fornecedor,total,data,observacao,conta_id) VALUES(?,?,?,?,?,?,?) RETURNING id",
                   (tid,d.get('numero_nota',''),d.get('fornecedor',''),total,d['data'],d.get('observacao',''),conta_id))
    cid=cur.fetchone()['id']
    for it in d.get('itens',[]):
        db.execute("INSERT INTO compra_itens(compra_id,produto_id,produto_nome,quantidade,preco_unitario,subtotal) VALUES(?,?,?,?,?,?)",
                   (cid,it.get('produto_id'),it['produto_nome'],it['quantidade'],it['preco_unitario'],it['subtotal']))
        if it.get('produto_id'): db.execute("UPDATE produtos SET estoque=estoque+?,preco_custo=? WHERE tenant_id=? AND id=?",(it['quantidade'],it['preco_unitario'],tid,it['produto_id']))
    db.execute("INSERT INTO movimentacoes(tenant_id,conta_id,tipo,valor,descricao,referencia_tipo,referencia_id) VALUES(?,?,?,?,?,?,?)",
               (tid, conta_id, 'saida', total, f'Compra #{cid} - {d.get("fornecedor","")}', 'compra', cid))
    db.execute("UPDATE contas SET saldo=saldo-? WHERE id=? AND tenant_id=?", (total, conta_id, tid))
    db.commit(); return jsonify({'ok':True,'id':cid})

# ══════════════════════════════════════════════════════════════════════════
# API – Contas Financeiras
# ══════════════════════════════════════════════════════════════════════════
def _get_caixa_id(db, tenant_id):
    row = db.execute("SELECT id FROM contas WHERE tenant_id=? AND tipo='caixa' AND ativo=1 LIMIT 1", (tenant_id,)).fetchone()
    if not row:
        cur = db.execute("INSERT INTO contas(tenant_id,nome,tipo,saldo) VALUES(?,?,?,?) RETURNING id", (tenant_id,'Caixa','caixa',0))
        db.commit()
        return cur.fetchone()['id']
    return row['id']

def _movimentar(db, tenant_id, conta_id, tipo, valor, descricao, ref_tipo=None, ref_id=None, conta_destino_id=None):
    """Record transaction and update balance. Returns error string or None on success."""
    if tipo in ('saida', 'transferencia'):
        saldo_row = db.execute("SELECT saldo FROM contas WHERE id=? AND tenant_id=?", (conta_id, tenant_id)).fetchone()
        if not saldo_row or float(saldo_row['saldo']) < float(valor):
            return 'Saldo insuficiente na conta selecionada'
    db.execute("INSERT INTO movimentacoes(tenant_id,conta_id,tipo,valor,descricao,referencia_tipo,referencia_id,conta_destino_id) VALUES(?,?,?,?,?,?,?,?)",
               (tenant_id, conta_id, tipo, valor, descricao, ref_tipo, ref_id, conta_destino_id))
    if tipo == 'entrada':
        db.execute("UPDATE contas SET saldo=saldo+? WHERE id=? AND tenant_id=?", (valor, conta_id, tenant_id))
    else:
        db.execute("UPDATE contas SET saldo=saldo-? WHERE id=? AND tenant_id=?", (valor, conta_id, tenant_id))
        if tipo == 'transferencia' and conta_destino_id:
            db.execute("UPDATE contas SET saldo=saldo+? WHERE id=? AND tenant_id=?", (valor, conta_destino_id, tenant_id))
    return None

@app.route('/api/contas', methods=['GET'])
@require_auth
def api_contas_list():
    db=get_db(); tid=session['tenant_id']
    return jsonify(rows_to_list(db.execute("SELECT * FROM contas WHERE tenant_id=? AND ativo=1 ORDER BY tipo DESC, nome", (tid,)).fetchall()))

@app.route('/api/contas', methods=['POST'])
@require_auth
@require_module('settings')
def api_conta_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    nome = d.get('nome','').strip()
    if not nome: return jsonify({'ok':False,'error':'Nome é obrigatório'}), 400
    saldo_ini = float(d.get('saldo_inicial', 0))
    cur = db.execute("INSERT INTO contas(tenant_id,nome,tipo,saldo) VALUES(?,?,?,?) RETURNING id", (tid, nome, 'banco', saldo_ini))
    cid = cur.fetchone()['id']
    if saldo_ini > 0:
        db.execute("INSERT INTO movimentacoes(tenant_id,conta_id,tipo,valor,descricao) VALUES(?,?,?,?,?)", (tid, cid, 'entrada', saldo_ini, 'Saldo inicial'))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/contas/<int:cid>', methods=['PUT'])
@require_auth
@require_module('settings')
def api_conta_update(cid):
    db=get_db(); d=request.json; tid=session['tenant_id']
    nome = d.get('nome','').strip()
    if not nome: return jsonify({'ok':False,'error':'Nome é obrigatório'}), 400
    db.execute("UPDATE contas SET nome=? WHERE id=? AND tenant_id=?", (nome, cid, tid))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/contas/<int:cid>', methods=['DELETE'])
@require_auth
@require_module('settings')
def api_conta_delete(cid):
    db=get_db(); tid=session['tenant_id']
    conta = db.execute("SELECT * FROM contas WHERE id=? AND tenant_id=?", (cid, tid)).fetchone()
    if not conta: return jsonify({'ok':False,'error':'Conta não encontrada'}), 404
    if conta['tipo'] == 'caixa': return jsonify({'ok':False,'error':'A conta Caixa não pode ser excluída'}), 400
    if float(conta['saldo']) != 0: return jsonify({'ok':False,'error':f'Conta possui saldo. Transfira o saldo antes de excluir.'}), 400
    db.execute("UPDATE contas SET ativo=0 WHERE id=? AND tenant_id=?", (cid, tid))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/contas/transferir', methods=['POST'])
@require_auth
@require_module('settings')
def api_conta_transferir():
    db=get_db(); d=request.json; tid=session['tenant_id']
    origem_id = d.get('conta_origem_id')
    destino_id = d.get('conta_destino_id')
    valor = float(d.get('valor', 0))
    descricao = d.get('descricao', 'Transferência entre contas')
    if not origem_id or not destino_id: return jsonify({'ok':False,'error':'Selecione as contas de origem e destino'}), 400
    if int(origem_id) == int(destino_id): return jsonify({'ok':False,'error':'Origem e destino devem ser diferentes'}), 400
    if valor <= 0: return jsonify({'ok':False,'error':'Valor deve ser maior que zero'}), 400
    err = _movimentar(db, tid, origem_id, 'transferencia', valor, descricao, 'transferencia', None, destino_id)
    if err: return jsonify({'ok':False,'error':err}), 400
    db.commit(); return jsonify({'ok':True})

@app.route('/api/movimentacoes', methods=['GET'])
@require_auth
def api_movimentacoes_list():
    db=get_db(); tid=session['tenant_id']
    conta_id = request.args.get('conta_id')
    limit = int(request.args.get('limit', 50))
    where = "WHERE m.tenant_id=?"
    params = [tid]
    if conta_id:
        where += " AND m.conta_id=?"
        params.append(conta_id)
    rows = db.execute(f"""SELECT m.*, c.nome as conta_nome, cd.nome as conta_destino_nome
        FROM movimentacoes m
        JOIN contas c ON c.id=m.conta_id
        LEFT JOIN contas cd ON cd.id=m.conta_destino_id
        {where} ORDER BY m.criado_em DESC LIMIT ?""", params + [limit]).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/vendedores', methods=['POST'])
@require_auth
@require_module('settings')
def api_vendedor_create():
    db=get_db(); d=request.json; tid=session['tenant_id']
    ativo_val = int(d.get('ativo', 1))
    db.execute("INSERT INTO vendedores(tenant_id,nome,ativo) VALUES(?,?,?)", (tid, d['nome'], ativo_val))
    db.commit(); return jsonify({'ok':True})

@app.route('/api/vendedores/<int:vid>', methods=['PUT'])
@require_auth
@require_module('settings')
def api_vendedor_update(vid):
    db=get_db(); d=request.json; tid=session['tenant_id']
    ativo_val = bool(int(d.get('ativo', 1)))
    db.execute("UPDATE vendedores SET nome=?, ativo=? WHERE tenant_id=? AND id=?",
               (d['nome'], 1 if ativo_val else 0, tid, vid))
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
# API – Pagamento Config (Taxas)
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/config/pagamentos', methods=['GET'])
@require_auth
@require_module('settings')
def api_pagamentos_config_list():
    db = get_db(); tid = session['tenant_id']
    rows = db.execute("SELECT nome, taxa FROM pagamento_taxas WHERE tenant_id=?", (tid,)).fetchall()
    return jsonify(rows_to_list(rows))

@app.route('/api/config/pagamentos', methods=['POST'])
@require_auth
@require_module('settings')
def api_pagamentos_config_save():
    db = get_db(); tid = session['tenant_id']; d = request.json
    # d deve ser uma lista de objetos {nome, taxa}
    if not isinstance(d, list): return jsonify({'ok': False, 'message': 'Payload inválido'}), 400
    
    for it in d:
        nome = it.get('nome')
        taxa = it.get('taxa', 0)
        db.execute("""
            INSERT INTO pagamento_taxas (tenant_id, nome, taxa) 
            VALUES (?, ?, ?) 
            ON CONFLICT (tenant_id, nome) DO UPDATE SET taxa = EXCLUDED.taxa
        """, (tid, nome, taxa))
    
    db.commit()
    return jsonify({'ok': True})

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
    
    # Resumo temporal (vendas brutas)
    resumo=rows_to_list(db.execute(f"SELECT {fmt2} as periodo,COUNT(*) as qtd_vendas,SUM(total) as total,SUM(desconto) as desconto,AVG(total) as ticket_medio FROM vendas WHERE {where} GROUP BY periodo ORDER BY periodo", params).fetchall())
    
    # Formas de pagamento com calculo de taxas
    formas=rows_to_list(db.execute(f"""
        SELECT 
            v.forma_pagamento,
            COUNT(*) as qtd,
            SUM(v.total) as total,
            SUM(v.total * (1 - COALESCE(pt.taxa, 0) / 100)) as total_liquido,
            SUM(v.total * (COALESCE(pt.taxa, 0) / 100)) as total_taxas
        FROM vendas v
        LEFT JOIN pagamento_taxas pt ON pt.tenant_id = v.tenant_id AND pt.nome = v.forma_pagamento
        WHERE {where_itens}
        GROUP BY v.forma_pagamento
    """, params_itens).fetchall())
    
    top=rows_to_list(db.execute(f"SELECT vi.produto_nome,SUM(vi.quantidade) as qtd,SUM(vi.subtotal) as total FROM venda_itens vi JOIN vendas v ON v.id=vi.venda_id WHERE {where_itens} GROUP BY vi.produto_nome ORDER BY total DESC LIMIT 20", params_itens).fetchall())
    
    totais_raw = db.execute(f"""
        SELECT 
            COUNT(*) as qtd,
            COALESCE(SUM(v.total),0) as total,
            COALESCE(SUM(v.desconto),0) as desconto,
            COALESCE(SUM(v.total * (COALESCE(pt.taxa, 0) / 100)), 0) as total_taxas
        FROM vendas v
        LEFT JOIN pagamento_taxas pt ON pt.tenant_id = v.tenant_id AND pt.nome = v.forma_pagamento
        WHERE {where_itens}
    """, params_itens).fetchone()
    
    totais = dict(totais_raw)
    totais['total_liquido'] = totais['total'] - totais['total_taxas']
    
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
# Inicialização do Banco (Gunicorn-compatible)
# ══════════════════════════════════════════════════════════════════════════
# Rodamos uma tentativa de inicialização no topo; se o banco estiver indisponível
# ou demorar, o app apenas loga o aviso e continua para não travar o worker boot.
# ══════════════════════════════════════════════════════════════════════════
# init_db() removido do top-level para evitar travar o boot do Gunicorn (causa de 504).
# O banco deve ser inicializado manualmente via 'python app.py init' se necessrio.

# ══════════════════════════════════════════════════════════════════════════
# API – Maquininhas
# ══════════════════════════════════════════════════════════════════════════
@app.route('/api/maquininhas', methods=['GET'])
@require_auth
def api_maquininhas_list():
    db = get_db()
    tid = session['tenant_id']
    return jsonify(rows_to_list(db.execute("SELECT * FROM maquininhas WHERE tenant_id=? AND ativo=1 ORDER BY nome", (tid,)).fetchall()))

@app.route('/api/maquininhas', methods=['POST'])
@require_auth
@require_module('settings')
def api_maquininha_create():
    db = get_db()
    d = request.json
    tid = session['tenant_id']
    db.execute("INSERT INTO maquininhas(tenant_id,nome,taxa_debito,taxa_credito_1x,taxa_credito_2x,taxa_credito_3x) VALUES(?,?,?,?,?,?)",
               (tid, d['nome'], d.get('taxa_debito', 0), d.get('taxa_credito_1x', 0), d.get('taxa_credito_2x', 0), d.get('taxa_credito_3x', 0)))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/maquininhas/<int:mid>', methods=['PUT'])
@require_auth
@require_module('settings')
def api_maquininha_update(mid):
    db = get_db()
    d = request.json
    tid = session['tenant_id']
    db.execute("UPDATE maquininhas SET nome=?, taxa_debito=?, taxa_credito_1x=?, taxa_credito_2x=?, taxa_credito_3x=? WHERE tenant_id=? AND id=?",
               (d['nome'], d.get('taxa_debito', 0), d.get('taxa_credito_1x', 0), d.get('taxa_credito_2x', 0), d.get('taxa_credito_3x', 0), tid, mid))
    db.commit()
    return jsonify({'ok': True})

@app.route('/api/maquininhas/<int:mid>', methods=['DELETE'])
@require_auth
@require_module('settings')
def api_maquininha_delete(mid):
    db = get_db()
    tid = session['tenant_id']
    # Desativa em vez de deletar para manter histórico de vendas
    db.execute("UPDATE maquininhas SET ativo=0 WHERE tenant_id=? AND id=?", (tid, mid))
    db.commit()
    return jsonify({'ok': True})

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        print("🛠️ Inicializando Banco de Dados...")
        init_db()
        sys.exit(0)
    
    port = int(os.environ.get('PORT', 5678))
    print(f"🚀 GestãoLoja em http://localhost:{port}")
    # Tenta rodar init_db uma vez antes de subir o dev server
    try:
        init_db()
    except Exception as e:
        print(f"!!! Erro ao inicializar banco: {e}")
    app.run(host='0.0.0.0', port=port, debug=False)
