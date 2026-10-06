import requests
import time
import json
import uuid

BASE_URL = 'http://localhost:8000/api/v1'

def get_token(email, password, name):
    # try register
    requests.post(f'{BASE_URL}/auth/register', json={'email': email, 'password': password, 'full_name': name})
    resp = requests.post(f'{BASE_URL}/auth/login', data={'username': email, 'password': password})
    if resp.status_code != 200:
        print(f'Failed to login {email}')
        return None
    return resp.json().get('access_token')

def run_tests():
    print('--- Starting Realistic Validation ---')
    token_a = get_token('user_a_real@example.com', 'Password123!', 'User A')
    token_b = get_token('user_b_real@example.com', 'Password123!', 'User B')
    
    headers_a = {'Authorization': f'Bearer {token_a}'}
    headers_b = {'Authorization': f'Bearer {token_b}'}

    # Upload A
    files_a = {'file': ('contract_A_real.pdf', open('contract_A_real.pdf', 'rb'), 'application/pdf')}
    resp = requests.post(f'{BASE_URL}/contracts/upload', headers=headers_a, files=files_a)
    print('Upload A:', resp.status_code)
    contract_a_id = resp.json().get('id')

    # Upload B
    files_b = {'file': ('contract_B_real.pdf', open('contract_B_real.pdf', 'rb'), 'application/pdf')}
    resp = requests.post(f'{BASE_URL}/contracts/upload', headers=headers_b, files=files_b)
    print('Upload B:', resp.status_code)
    contract_b_id = resp.json().get('id')

    time.sleep(3) # Wait for embeddings

    # 1. Summary (A)
    print('\n-- Summary Agent --')
    resp = requests.post(f'{BASE_URL}/analysis/summarize/{contract_a_id}', headers=headers_a)
    print('Status:', resp.status_code)
    print('Content:', resp.json().get('summary')[:100] if resp.status_code==200 else resp.text)

    # 2. Clauses (A)
    print('\n-- Clause Agent --')
    resp = requests.post(f'{BASE_URL}/analysis/clauses/{contract_a_id}', headers=headers_a)
    print('Status:', resp.status_code)
    clauses = resp.json().get('clauses', [])
    print(f'Extracted {len(clauses)} clauses')
    for c in clauses[:2]:
        print(f'- {c.get("title")}: {str(c.get("content"))[:50]}')

    # 3. Risk (A)
    print('\n-- Risk Agent --')
    resp = requests.post(f'{BASE_URL}/analysis/risk/{contract_a_id}', headers=headers_a)
    print('Status:', resp.status_code)
    risks = resp.json().get('risk_matrix', [])
    print(f'Identified {len(risks)} risks')

    # 4. Compliance (A)
    print('\n-- Compliance Agent --')
    resp = requests.post(f'{BASE_URL}/analysis/compliance/{contract_a_id}', headers=headers_a)
    print('Status:', resp.status_code)
    print('Compliant:', resp.json().get('compliant'))

    # 5. Negotiation (A)
    print('\n-- Negotiation Agent --')
    resp = requests.post(f'{BASE_URL}/analysis/negotiation/{contract_a_id}', headers=headers_a)
    print('Status:', resp.status_code)
    sugg = resp.json().get('negotiation_suggestions', [])
    print(f'Suggestions: {len(sugg)}')

    # 6. Knowledge Graph (A)
    print('\n-- KG Agent --')
    resp = requests.post(f'{BASE_URL}/analysis/knowledge-graph/{contract_a_id}', headers=headers_a)
    print('Status:', resp.status_code)
    if resp.status_code == 200:
        kg = resp.json().get('result', {})
        print(f'Entities: {len(kg.get("entities", []))}')

    # 7. Compare (A and B by User A) - should fail with 403 on B
    print('\n-- Compare Agent (Auth Check) --')
    comp_data = {'contract_a_id': contract_a_id, 'contract_b_id': contract_b_id}
    resp = requests.post(f'{BASE_URL}/analysis/compare', headers=headers_a, json=comp_data)
    print('Compare cross-tenant:', resp.status_code, resp.json() if resp.status_code != 200 else 'FAILED (should be 403)')

    # 8. RAG Chat
    print('\n-- RAG Chat Agent --')
    queries = [
        'What is the contract value?',
        'What is the contract term?',
        'What is the governing law?',
        'What is the late payment interest?',
        'What is Contract B\'s governing law?',
        'What HIPAA requirement exists?'
    ]
    for q in queries:
        resp = requests.post(f'{BASE_URL}/analysis/chat/{contract_a_id}', headers=headers_a, json={'question': q})
        if resp.status_code == 200:
            print(f'Q: {q}\nA: {resp.json().get("answer")}\n')
        else:
            print(f'Q: {q} -> Error {resp.status_code}')

    # 9. Auth Checks
    print('\n-- Auth Isolation Checks --')
    resp = requests.get(f'{BASE_URL}/contracts/{contract_b_id}', headers=headers_a)
    print('User A accessing Contract B:', resp.status_code)
    resp = requests.get(f'{BASE_URL}/contracts/{uuid.uuid4()}', headers=headers_a)
    print('User A accessing random UUID:', resp.status_code)
    resp = requests.get(f'{BASE_URL}/contracts/not-a-uuid', headers=headers_a)
    print('User A accessing invalid UUID:', resp.status_code)

if __name__ == "__main__":
    run_tests()
