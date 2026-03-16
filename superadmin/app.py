import os
import hashlib
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, session, redirect
from dotenv import load_dotenv

# Importando DB e Modelos
from models import db, SuperadminUsuario, Plano, Tenant, TenantUsuario
from auth import require_superadmin

# Carrega var de ambiente
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-admin-secret-key-deploy-change-later')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgrespassword@localhost:5432/superadmin_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

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

# ── API Auth ───────────────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    d = request.json or {}
    login = (d.get('login') or '').strip()
    senha = d.get('senha') or ''
    if not login or not senha:
        return jsonify({'ok': False, 'message': 'Preencha login e senha'}), 400
    
    user = SuperadminUsuario.query.filter_by(login=login, senha_hash=hash_pw(senha), ativo=True).first()
    if not user:
        return jsonify({'ok': False, 'message': 'Login ou senha incorretos'}), 401
    
    session['superadmin_id'] = user.id
    session['superadmin_nome'] = user.nome
    
    return jsonify({'ok': True, 'nome': user.nome})

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
    tenants_ativos = Tenant.query.filter_by(status='ATIVO').join(Plano).all()
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
        ativo=d.get('ativo', True)
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
    d = request.json or {}
    if not d.get('nome'):
        return jsonify({'ok': False, 'message': 'Nome da loja é obrigatório'}), 400
        
    dv = None
    if d.get('data_vencimento'):
        try:
            dv = datetime.strptime(d['data_vencimento'], '%Y-%m-%d').date()
        except:
            pass
            
    novo = Tenant(
        nome=d.get('nome'),
        cnpj=d.get('cnpj'),
        email=d.get('email'),
        telefone=d.get('telefone'),
        plano_id=d.get('plano_id'),
        status=d.get('status', 'ATIVO'),
        data_vencimento=dv
    )
    db.session.add(novo)
    db.session.commit()
    return jsonify({'ok': True, 'id': novo.id})

@app.route('/api/tenants/<int:tid>', methods=['PUT'])
@require_superadmin
def api_tenant_update(tid):
    t = Tenant.query.get(tid)
    if not t:
        return jsonify({'ok': False, 'message': 'Tenant não encontrado'}), 404
        
    d = request.json or {}
    t.nome = d.get('nome', t.nome)
    t.cnpj = d.get('cnpj', t.cnpj)
    t.email = d.get('email', t.email)
    t.telefone = d.get('telefone', t.telefone)
    t.plano_id = d.get('plano_id', t.plano_id)
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
        
    existe = TenantUsuario.query.filter_by(tenant_id=d['tenant_id'], login=d['login']).first()
    if existe:
        return jsonify({'ok': False, 'message': 'Login já existe nesta loja'}), 400
        
    novo = TenantUsuario(
        tenant_id=d['tenant_id'],
        nome=d['nome'],
        login=d['login'].strip(),
        senha_hash=hash_pw(d['senha']),
        papel=d.get('papel', 'operador'),
        ativo=d.get('ativo', True)
    )
    db.session.add(novo)
    db.session.commit()
    return jsonify({'ok': True, 'id': novo.id})
    
@app.route('/api/tenant_usuarios/<int:uid>', methods=['PUT', 'DELETE'])
@require_superadmin
def api_tenant_user_update(uid):
    u = TenantUsuario.query.get(uid)
    if not u:
        return jsonify({'ok': False, 'message': 'Usuário não encontrado'}), 404
        
    if request.method == 'DELETE':
        u.ativo = False
        db.session.commit()
        return jsonify({'ok': True})
        
    d = request.json or {}
    u.nome = d.get('nome', u.nome)
    if d.get('senha'):
        u.senha_hash = hash_pw(d['senha'])
    u.papel = d.get('papel', u.papel)
    if 'ativo' in d:
        u.ativo = d['ativo']
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

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5679))
    print(f"🚀 Super Admin Panel rodando em http://localhost:{port}")
    app.run(host='0.0.0.1', port=port, debug=True)
