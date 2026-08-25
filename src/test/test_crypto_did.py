import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_did import CryptoDID

if __name__ == "__main__":
    print("--- Teste de Módulo: Criptografia e DID ---")
    
    crypto = CryptoDID()
    identidade = crypto.generate_identity()
    
    print(f"\n[+] DID Criado: {identidade['did']}")
    print(f"[+] Chave Pública: {identidade['public_key']}")
    
    # Simulando o Consentimento do RAG
    payload_consentimento = {"allow_rag": True, "did": identidade['did']}
    assinatura = crypto.sign_payload(payload_consentimento)
    print(f"\n[+] Assinatura do Consentimento:\n{assinatura}")
    
    # Teste de validação
    is_valid = CryptoDID.verify_signature(
        public_key_b64=identidade['public_key'],
        payload=payload_consentimento,
        signature_b64=assinatura
    )
    
    print(f"\n[+] Verificação da Assinatura: {'APROVADA' if is_valid else 'REJEITADA'}")
