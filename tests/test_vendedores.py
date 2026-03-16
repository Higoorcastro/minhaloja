import requests
import json
import time

BASE_URL = 'http://localhost:5678'
session = requests.Session()

def print_res(res):
    try:
        print(f"[{res.status_code}] {res.json()}")
    except:
        print(f"[{res.status_code}] {res.text[:100]}")

print("1. Logging in as admin...")
r = session.post(f"{BASE_URL}/api/auth/login", json={"login": "admin", "senha": "admin123"})
print_res(r)

print("\n2. Creating a salesperson...")
r = session.post(f"{BASE_URL}/api/vendedores", json={"nome": "João Vendedor Script"})
print_res(r)

print("\n3. Listing salespeople...")
r = session.get(f"{BASE_URL}/api/vendedores")
print_res(r)
vendedores = r.json()
vendedor_id = vendedores[-1]['id'] if vendedores else None
vendedor_nome = vendedores[-1]['nome'] if vendedores else None
print(f"Selected Vendedor: ID={vendedor_id}, Nome={vendedor_nome}")

print("\n4. Getting products to sell...")
r = session.get(f"{BASE_URL}/api/produtos")
produtos = r.json()
produto_id = produtos[0]['id'] if produtos else None
produto_nome = produtos[0]['nome'] if produtos else None
print(f"Selected Produto: ID={produto_id}, Nome={produto_nome}")

print("\n5. Creating a sale with salesperson...")
venda_payload = {
    "cliente_id": None,
    "cliente_nome": "Consumidor Final",
    "vendedor_id": vendedor_id,
    "vendedor_nome": vendedor_nome,
    "subtotal": 50.0,
    "desconto": 0,
    "total": 50.0,
    "forma_pagamento": "PIX",
    "observacao": "Venda de teste via script",
    "itens": [
        {
            "produto_id": produto_id,
            "produto_nome": produto_nome or "Produto Teste",
            "quantidade": 1,
            "preco_unitario": 50.0,
            "subtotal": 50.0
        }
    ]
}
r = session.post(f"{BASE_URL}/api/vendas", json=venda_payload)
print_res(r)
venda_res = r.json()
venda_id = venda_res.get('id')

print(f"\n6. Fetching specific sale details (ID={venda_id})...")
if venda_id:
    r = session.get(f"{BASE_URL}/api/vendas/{venda_id}")
    print_res(r)
else:
    print("Could not fetch sale details, creation failed.")

print("\n7. Listing sales history...")
r = session.get(f"{BASE_URL}/api/vendas?status=CONCLUIDA")
sales = r.json()
latest_sale = sales[0] if sales else None
print(f"Latest sale in history list: {json.dumps(latest_sale)}")
