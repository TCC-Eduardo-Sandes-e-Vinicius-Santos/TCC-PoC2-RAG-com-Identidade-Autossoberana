import sys
import os
import json
import base64

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from biometric_verifier import BiometricVerifier, BiometricCaptureError, AgeAnalysisError


def main() -> int:
    did_subject = sys.argv[1] if len(sys.argv) > 1 else None

    raw_b64 = sys.stdin.read().strip()
    if not raw_b64:
        print(json.dumps({"ok": False, "error": "Nenhuma imagem recebida pelo processo de verificação."}))
        return 1

    try:
        import cv2
        import numpy as np

        image_bytes = base64.b64decode(raw_b64)
        image_array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

        if image_array is None:
            print(json.dumps({"ok": False, "error": "Não foi possível decodificar a imagem recebida."}))
            return 1

        verifier = BiometricVerifier()
        claim = verifier.verify_age_from_array(image_array=image_array, did_subject=did_subject)
        print(json.dumps({"ok": True, "claim": claim.to_dict()}))
        return 0

    except (BiometricCaptureError, AgeAnalysisError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    except Exception as exc:  # failsafe falha inesperada não deve travar o processo pai
        print(json.dumps({"ok": False, "error": f"Falha inesperada no worker biométrico: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
