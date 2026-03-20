import sys
import os

# Add superadmin to path so imports inside superadmin/app.py work
sys.path.insert(0, os.path.join(os.getcwd(), 'superadmin'))

from superadmin.app import app, db, Tenant, TenantUsuario, Plano, hash_pw

def seed():
    with app.app_context():
        print("🌱 Iniciando seeding no contexto do Flask...")
        
        # 1. Criar Plano
        plano = db.session.query(Plano).first()
        if not plano:
            print("Creating plan...")
            plano = Plano(
                nome='Premium', 
                preco_mensal=99.9, 
                max_usuarios=10, 
                modulos='dashboard,pdv,vendas,os,produtos,clientes,financeiro,relatorios,settings',
                ativo=True
            )
            db.session.add(plano)
            db.session.commit()
            print(f"Plan created with ID: {plano.id}")
        else:
            print(f"Plan already exists: {plano.nome}")
        
        # 2. Criar Tenant
        t = db.session.query(Tenant).filter_by(nome='Loja Modelo').first()
        if not t:
            print("Creating tenant...")
            t = Tenant(nome='Loja Modelo', plano_id=plano.id, status='ATIVO')
            db.session.add(t)
            db.session.commit()
            print(f"Tenant created with ID: {t.id}")
        else:
            print(f"Tenant already exists: {t.nome}")
        
        # 3. Criar Usuário
        u = db.session.query(TenantUsuario).filter_by(login='loja@centercell.com.br').first()
        password_hash = hash_pw('123456') # Define password hash once
        if not u:
            print("Creating user...")
            u = TenantUsuario(
                tenant_id=t.id, 
                nome='Administrador', 
                login='loja@centercell.com.br', 
                senha_hash=password_hash, 
                papel='admin',
                ativo=True
            )
            db.session.add(u)
            db.session.commit()
            print(f"User created with ID: {u.id}")
        else:
            u.senha_hash = password_hash
            db.session.commit()
            print(f"Updated password for user: {u.login}")
        
        print("✅ Seeding concluído com sucesso!")

if __name__ == '__main__':
    try:
        seed()
    except Exception as e:
        print(f"❌ Erro no seeding: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
