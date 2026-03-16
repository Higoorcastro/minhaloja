import sqlite3
import json
from app import app, init_db, db_migrate

def test_api():
    # Setup test DB in memory or just use a test app context
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        # Mock session for require_auth
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_nome'] = 'Admin'
            sess['papel'] = 'admin'
            sess['permissions'] = ['financeiro', 'receber']
            
        print("Testing DB initialization...")
        # create tables
        init_db()

        print("Testing POST /api/contas_receber ...")
        res = client.post('/api/contas_receber', json={
            'novo_cliente': {'nome': 'Test Client', 'cpf_cnpj': '123'},
            'descricao': 'Test Debt',
            'valor_total': 150.00,
            'data_vencimento': '2026-12-31'
        })
        data = json.loads(res.data)
        assert data['ok'] == True
        conta_id = data['id']
        print("=> Created conta_id:", conta_id)

        print("Testing GET /api/contas_receber/dashboard ...")
        res = client.get('/api/contas_receber/dashboard')
        dash = json.loads(res.data)
        assert dash['total_a_receber'] >= 150.0
        print("=> Dashboard OK:", dash)

        print("Testing POST partial payment ...")
        res = client.post(f'/api/contas_receber/{conta_id}/recebimento', json={
            'valor_pago': 50.00,
            'data_pagamento': '2026-03-05',
            'forma_pagamento': 'PIX'
        })
        data = json.loads(res.data)
        assert data['ok'] == True
        assert data['novo_status'] == 'PARCIAL'
        assert data['total_recebido'] == 50.0
        print("=> Partial payment OK")

        print("Testing POST full payment ...")
        res = client.post(f'/api/contas_receber/{conta_id}/recebimento', json={
            'valor_pago': 100.00,
            'data_pagamento': '2026-03-06',
            'forma_pagamento': 'DINHEIRO'
        })
        data = json.loads(res.data)
        assert data['ok'] == True
        assert data['novo_status'] == 'PAGA'
        assert data['total_recebido'] == 150.0
        print("=> Full payment OK")
        
        print("Testing DELETE ...")
        res = client.delete(f'/api/contas_receber/{conta_id}')
        assert json.loads(res.data)['ok'] == True
        print("=> Delete OK")
        
        print("ALL TESTS PASSED!")

if __name__ == '__main__':
    test_api()
