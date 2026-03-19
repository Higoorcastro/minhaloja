import os
import sys
import hashlib
import bcrypt
import secrets
import traceback
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from models import db, SuperadminUsuario, Plano, Tenant, TenantUsuario, ContatoLead
from auth import require_superadmin

load_dotenv()

app = Flask(__name__)
_secret = os.environ.get('SECRET_KEY')
if not _secret:
    raise RuntimeError('FATAL: SECRET_KEY environment variable not set. Refusing to start.')
app.secret_key = _secret

_db_url = os.environ.get('DB_URL')
if not _db_url:
    raise RuntimeError('FATAL: DB_URL environment variable not set. Refusing to start.')
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[], storage_uri='memory://')

db.init_app(app)

def hash_pw(pw):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_pw(plain, stored_hash):
    """Verify password, supports bcrypt and legacy SHA-256."""
    try:
        if bcrypt.checkpw(plain.encode('utf-8'), stored_hash.encode('utf-8')):
            return True
    except Exception:
        pass
    legacy = hashlib.sha256(plain.encode()).hexdigest()
    if secrets.compare_digest(legacy, stored_hash):
        return True, 'migrate'
    return False

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler to return JSON instead of HTML on error."""
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    tb = traceback.format_exc()
    print(f"!!! Error detected in Superadmin:\n{tb}")
    return jsonify({
        'ok': False,
        'error': str(e),
        'traceback': tb if os.getenv('FLASK_ENV') == 'development' else None
    }), 500

@app.after_request
def add_security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    resp.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self';"
    )
    return resp

# ── Rotas Web Básicas ──────────────────────────────────────────────────────
@app.route('/login')
def login_page():
    if session.get('superadmin_id'):
        return redirect('/')
    return render_template('sa_login.html')

@app.route('/')
@require_superadmin
def dashboard_page():
    return render_template('sa_dashboard.html')

@app.route('/lojas')
@require_superadmin
def lojas_page():
    return render_template('sa_lojas.html')

@app.route('/planos')
@require_superadmin
def planos_page():
    return render_template('sa_planos.html')

@app.route('/usuarios')
@require_superadmin
def usuarios_page():
    return render_template('sa_usuarios.html')

@app.route('/contatos')
@require_superadmin
def contatos_page():
    return render_template('sa_contatos.html')

# ── API Auth ───────────────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    try:
        d = request.json or {}
        login = (d.get('login') or '').strip()
        senha = d.get('senha') or ''
        if not login or not senha or len(login) > 100:
            return jsonify({'ok': False, 'message': 'Credenciais inválidas'}), 400

        user = SuperadminUsuario.query.filter_by(login=login, ativo=True).first()
        if not user:
            return jsonify({'ok': False, 'message': 'Login ou senha incorretos'}), 401

        result = verify_pw(senha, user.senha_hash)
        if not result:
            return jsonify({'ok': False, 'message': 'Login ou senha incorretos'}), 401

        if isinstance(result, tuple) and result[1] == 'migrate':
            user.senha_hash = hash_pw(senha)
            db.session.commit()

        session.clear()
        session['superadmin_id'] = user.id
        session['superadmin_nome'] = user.nome
        return jsonify({'ok': True, 'nome': user.nome})
    except Exception as e:
        raise e

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})

# ── API Dashboard ────────────────────────────────────────────────────────
@app.route('/api/dashboard', methods=['GET'])
@require_superadmin
def api_dashboard():
    total_tenants = Tenant.query.count()
    ativos = Tenant.query.filter_by(status='ATIVO').count()
    suspensos = Tenant.query.filter_by(status='SUSPENSO').count()
    
    # Receita baseada no preço dos planos dos tenants ativos
    tenants_ativos = Tenant.query.filter_by(status='ATIVO').all()
    receita_mensal = sum(t.plano.preco_mensal for t in tenants_ativos if t.plano)

    
    ultimos = Tenant.query.order_by(Tenant.criado_em.desc()).limit(5).all()
    ultimos_json = []
    for u in ultimos:
        ultimos_json.append({
            'nome': u.nome,
            'plano': u.plano.nome if u.plano else 'Sem Plano',
            'status': u.status,
            'criado_em': u.criado_em.strftime('%d/%m/%Y')
        })
        
    return jsonify({
        'total_tenants': total_tenants,
        'ativos': ativos,
        'suspensos': suspensos,
        'receita_mensal': float(receita_mensal),
        'ultimos_tenants': ultimos_json
    })

# ── API Planos ─────────────────────────────────────────────────────────────
@app.route('/api/planos', methods=['GET'])
@require_superadmin
def api_planos_list():
    planos = Plano.query.order_by(Plano.id.asc()).all()
    lista = []
    for p in planos:
        lista.append({
            'id': p.id,
            'nome': p.nome,
            'descricao': p.descricao,
            'preco_mensal': float(p.preco_mensal),
            'max_usuarios': p.max_usuarios,
            'modulos': p.modulos,
            'ativo': p.ativo
        })
    return jsonify(lista)

@app.route('/api/planos', methods=['POST'])
@require_superadmin
def api_plano_create():
    d = request.json or {}
    novo = Plano(
        nome=d.get('nome'),
        descricao=d.get('descricao'),
        preco_mensal=d.get('preco_mensal', 0),
        max_usuarios=d.get('max_usuarios', 5),
        modulos=d.get('modulos', 'dashboard,pdv,vendas,produtos,clientes'),
        ativo=d.get('ativo', 1)
    )
    db.session.add(novo)
    db.session.commit()
    return jsonify({'ok': True, 'id': novo.id})

@app.route('/api/planos/<int:pid>', methods=['PUT', 'DELETE'])
@require_superadmin
def api_plano_update_delete(pid):
    p = Plano.query.get(pid)
    if not p:
        return jsonify({'ok': False, 'message': 'Plano não encontrado'}), 404
        
    if request.method == 'DELETE':
        p.ativo = False
        db.session.commit()
        return jsonify({'ok': True})
        
    d = request.json or {}
    p.nome = d.get('nome', p.nome)
    p.descricao = d.get('descricao', p.descricao)
    p.preco_mensal = d.get('preco_mensal', p.preco_mensal)
    p.max_usuarios = d.get('max_usuarios', p.max_usuarios)
    p.modulos = d.get('modulos', p.modulos)
    if 'ativo' in d:
        p.ativo = d['ativo']
    db.session.commit()
    return jsonify({'ok': True})

# ── API Tenants (Lojas) ──────────────────────────────────────────────────
@app.route('/api/tenants', methods=['GET'])
@require_superadmin
def api_tenants_list():
    tenants = Tenant.query.order_by(Tenant.criado_em.desc()).all()
    lista = []
    for t in tenants:
        lista.append({
            'id': t.id,
            'nome': t.nome,
            'cnpj': t.cnpj,
            'email': t.email,
            'telefone': t.telefone,
            'plano_id': t.plano_id,
            'plano_nome': t.plano.nome if t.plano else None,
            'status': t.status,
            'data_vencimento': t.data_vencimento.isoformat() if t.data_vencimento else None,
            'criado_em': t.criado_em.strftime('%d/%m/%Y')
        })
    return jsonify(lista)

@app.route('/api/tenants', methods=['POST'])
@require_superadmin
def api_tenant_create():
    try:
        d = request.json or {}
        if not d.get('nome'):
            return jsonify({'ok': False, 'message': 'Nome da loja é obrigatório'}), 400
            
        dv = None
        if d.get('data_vencimento'):
            try:
                dv = datetime.strptime(d['data_vencimento'], '%Y-%m-%d').date()
            except:
                pass
                
        # Garante que plano_id seja int ou None para evitar erro de tipo no SQLAlchemy
        pid = d.get('plano_id')
        if pid == "" or pid == "null": pid = None
        if pid is not None:
            try:
                pid = int(pid)
            except:
                pid = None

        novo = Tenant(
            nome=d.get('nome'),
            cnpj=d.get('cnpj'),
            email=d.get('email'),
            telefone=d.get('telefone'),
            plano_id=pid,
            status=d.get('status', 'ATIVO'),
            data_vencimento=dv
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({'ok': True, 'id': novo.id})
    except Exception as e:
        db.session.rollback()
        print(f"ERRO API TENANT CREATE: {str(e)}")
        traceback.print_exc()
        return jsonify({'ok': False, 'message': f"Erro interno: {str(e)}"}), 500

@app.route('/api/tenants/<int:tid>', methods=['PUT', 'DELETE'])
@require_superadmin
def api_tenant_update(tid):
    t = Tenant.query.get(tid)
    if not t:
        return jsonify({'ok': False, 'message': 'Tenant não encontrado'}), 404
        
    if request.method == 'DELETE':
        db.session.delete(t)
        db.session.commit()
        return jsonify({'ok': True})
        
    try:
        d = request.json or {}
        t.nome = d.get('nome', t.nome)
        t.cnpj = d.get('cnpj', t.cnpj)
        t.email = d.get('email', t.email)
        t.telefone = d.get('telefone', t.telefone)
        
        # Garante que plano_id seja int ou None
        pid = d.get('plano_id', t.plano_id)
        if pid == "" or pid == "null": pid = None
        if pid is not None:
            try:
                pid = int(pid)
            except:
                pid = t.plano_id
        t.plano_id = pid
        
        t.status = d.get('status', t.status)
        if 'data_vencimento' in d:
            if d['data_vencimento']:
                try:
                    t.data_vencimento = datetime.strptime(d['data_vencimento'], '%Y-%m-%d').date()
                except:
                    pass
            else:
                t.data_vencimento = None
                
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        print(f"ERRO API TENANT UPDATE: {str(e)}")
        traceback.print_exc()
        return jsonify({'ok': False, 'message': f"Erro interno: {str(e)}"}), 500

# ── API Usuários por Tenant ────────────────────────────────────────────────
@app.route('/api/tenant_usuarios', methods=['GET'])
@require_superadmin
def api_tenant_users_list():
    tid = request.args.get('tenant_id')
    query = TenantUsuario.query
    if tid:
        query = query.filter_by(tenant_id=tid)
    usuarios = query.order_by(TenantUsuario.nome.asc()).all()
    
    lista = []
    for u in usuarios:
        lista.append({
            'id': u.id,
            'tenant_id': u.tenant_id,
            'tenant_nome': u.tenant.nome if u.tenant else '',
            'nome': u.nome,
            'login': u.login,
            'papel': u.papel,
            'ativo': u.ativo
        })
    return jsonify(lista)

@app.route('/api/tenant_usuarios', methods=['POST'])
@require_superadmin
def api_tenant_user_create():
    d = request.json or {}
    if not d.get('tenant_id') or not d.get('nome') or not d.get('login') or not d.get('senha'):
        return jsonify({'ok': False, 'message': 'Faltam campos (tenant_id, nome, login, senha)'}), 400
    
    login = d['login'].strip().lower()
    if '@' not in login or '.' not in login:
        return jsonify({'ok': False, 'message': 'O login deve ser um e-mail válido'}), 400

    existe = TenantUsuario.query.filter_by(login=login).first()
    if existe:
        return jsonify({'ok': False, 'message': 'Este e-mail já está sendo usado por outro usuário'}), 400
        
    novo = TenantUsuario(
        tenant_id=d['tenant_id'],
        nome=d['nome'],
        login=login,
        senha_hash=hash_pw(d['senha']),
        papel=d.get('papel', 'operador'),
        ativo=d.get('ativo', 1)
    )
    db.session.add(novo)
    db.session.commit()
    return jsonify({'ok': True, 'id': novo.id})
    
@app.route('/api/tenant_usuarios/<int:uid>', methods=['PUT', 'DELETE'])
@require_superadmin
def api_tenant_user_update(uid):
    u = TenantUsuario.query.get_or_404(uid)
    
    if request.method == 'DELETE':
        db.session.delete(u)
        db.session.commit()
        return jsonify({'ok': True})
        
    d = request.json or {}
    
    login = d.get('login', '').strip().lower()
    if login:
        if '@' not in login or '.' not in login:
            return jsonify({'ok': False, 'message': 'O login deve ser um e-mail válido'}), 400
            
        existe = TenantUsuario.query.filter(TenantUsuario.login == login, TenantUsuario.id != uid).first()
        if existe:
            return jsonify({'ok': False, 'message': 'Este e-mail já está sendo usado por outro usuário'}), 400
        u.login = login

    if d.get('nome'): u.nome = d['nome']
    if d.get('senha'):
        u.senha_hash = hash_pw(d['senha'])
    u.papel = d.get('papel', u.papel)
    if 'ativo' in d:
        u.ativo = d['ativo']
    db.session.commit()
    return jsonify({'ok': True})

# ── API Contatos (público — recebe leads da landing page) ─────────────────
LANDING_ORIGIN = os.environ.get('LANDING_ORIGIN', '*')

def _cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = LANDING_ORIGIN
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/api/contato', methods=['POST', 'OPTIONS'])
@limiter.limit('5 per hour', methods=['POST'])
def api_contato_create():
    if request.method == 'OPTIONS':
        return _cors_headers(app.make_response(('', 204)))

    try:
        d = request.json or {}

        # Honeypot: campo oculto preenchido = bot
        if d.get('website'):
            return _cors_headers(jsonify({'ok': True}))

        nome = (d.get('nome') or '').strip()
        email = (d.get('email') or '').strip().lower()
        if not nome or not email or '@' not in email:
            return _cors_headers(
                jsonify({'ok': False, 'message': 'Nome e e-mail são obrigatórios'})
            ), 400

        lead = ContatoLead(
            nome=nome,
            email=email,
            telefone=(d.get('telefone') or '').strip() or None,
            empresa=(d.get('empresa') or '').strip() or None,
            plano_interesse=(d.get('plano_interesse') or '').strip() or None,
            mensagem=(d.get('mensagem') or '').strip() or None,
        )
        db.session.add(lead)
        db.session.commit()
        return _cors_headers(jsonify({'ok': True}))
    except Exception as e:
        db.session.rollback()
        return _cors_headers(
            jsonify({'ok': False, 'message': 'Erro interno, tente novamente.'})
        ), 500


@app.route('/api/contatos', methods=['GET'])
@require_superadmin
def api_contatos_list():
    status_filter = request.args.get('status')
    query = ContatoLead.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    leads = query.order_by(ContatoLead.criado_em.desc()).all()
    return jsonify([{
        'id': l.id,
        'nome': l.nome,
        'email': l.email,
        'telefone': l.telefone,
        'empresa': l.empresa,
        'plano_interesse': l.plano_interesse,
        'mensagem': l.mensagem,
        'status': l.status,
        'criado_em': l.criado_em.strftime('%d/%m/%Y %H:%M'),
    } for l in leads])


@app.route('/api/contatos/<int:cid>', methods=['PUT', 'DELETE'])
@require_superadmin
def api_contato_update(cid):
    lead = ContatoLead.query.get_or_404(cid)
    if request.method == 'DELETE':
        db.session.delete(lead)
        db.session.commit()
        return jsonify({'ok': True})
    d = request.json or {}
    if 'status' in d:
        lead.status = d['status']
    db.session.commit()
    return jsonify({'ok': True})


def init_db():
    with app.app_context():
        db.create_all()
        # Admin inicial se não existir
        if not SuperadminUsuario.query.filter_by(login='superadmin').first():
            admin = SuperadminUsuario(nome='Super Administrador', login='superadmin', senha_hash=hash_pw('admin123'))
            db.session.add(admin)
            db.session.commit()

# Inicialização opcional; se falhar (ex: DB não pronto), o Gunicorn prossegue.
# init_db() removido do top-level para evitar 504 Gateway Timeout.
# Inicialize manualmente via CLI se necessrio ou via dev server.

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5679))
    print(f"🚀 Super Admin Panel rodando em http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
