import requests

BASE_URL = 'http://localhost:5678'
session = requests.Session()

def print_res(res):
    try:
        print(f"[{res.status_code}] {res.json()}")
    except:
        print(f"[{res.status_code}] {res.text[:100]}")

print("1. Logging in as admin...")
r = session.post(f"{BASE_URL}/api/auth/login", json={"login": "admin", "senha": "admin123"})

print("\n2. Fetching all salespeople...")
r = session.get(f"{BASE_URL}/api/vendedores")
vendedores = r.json()
print(vendedores)

if not vendedores:
    print("No salespeople found. Please run test_vendedores.py first to create some sales.")
    exit(1)

vendedor_id = vendedores[-1]['id']

print("\n3. Fetching reports WITHOUT filter...")
r = session.get(f"{BASE_URL}/api/relatorios/vendas")
unfiltered_totais = r.json()['totais']
print(f"Unfiltered totals: {unfiltered_totais}")

print(f"\n4. Fetching reports WITH filter for vendedor_id={vendedor_id}...")
r = session.get(f"{BASE_URL}/api/relatorios/vendas?vendedor_id={vendedor_id}")
filtered_totais = r.json()['totais']
print(f"Filtered totals: {filtered_totais}")

if filtered_totais['qtd'] <= unfiltered_totais['qtd']:
    print("\nSUCCESS: Filtering seems to work!")
else:
    print("\nERROR: Filtered results shouldn't have more logic than unfiltered.")
    exit(1)

print("\n5. Fetching reports WITH filter for a non-existent vendedor_id=9999...")
r = session.get(f"{BASE_URL}/api/relatorios/vendas?vendedor_id=9999")
none_totais = r.json()['totais']
print(f"Filtered totals (9999): {none_totais}")
if none_totais['qtd'] == 0:
    print("\nSUCCESS: Empty filter returns 0 as expected.")
else:
    print("\nERROR: Expected 0 sales for non-existent salesperson id 9999.")
    exit(1)
