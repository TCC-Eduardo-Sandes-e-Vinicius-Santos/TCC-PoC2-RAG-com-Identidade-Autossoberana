import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from biometric_verifier import AgeAnalysisError, BiometricCaptureError, BiometricVerifier

if __name__ == "__main__":
    print("--- Teste de Módulo: Verificação Biométrica Etária (US02) ---")
    verifier = BiometricVerifier()
    try:
        claim = verifier.verify_age(did_subject="did:poc:12345")
        print("\nAlegação etária gerada (pronta para assinatura em crypto_did.py):\n")
        print(claim.to_json())
    except (BiometricCaptureError, AgeAnalysisError) as exc:
        print(f"Erro na verificação: {exc}")
