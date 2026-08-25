import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Union

os.environ["TF_USE_LEGACY_KERAS"] = "1"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

MINIMUM_AGE = 18

class BiometricCaptureError(Exception):
    """Erro ao capturar imagem da webcam local."""


class AgeAnalysisError(Exception):
    """Erro ao processar a imagem com o modelo de visão computacional."""


@dataclass
class AgeClaim:
    """
    Alegação etária, para ser assinada 
    digitalmente pelo módulo `crypto_did.py`.
    """

    did_subject: Optional[str]
    is_adult: bool
    estimated_age: int
    minimum_age_threshold: int
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    method: str = "deepface-local-inference"

    def to_dict(self) -> dict:
        return {
            "did_subject": self.did_subject,
            "claim": "is_adult",
            "value": self.is_adult,
            "estimated_age": self.estimated_age,
            "minimum_age_threshold": self.minimum_age_threshold,
            "issued_at": self.issued_at,
            "method": self.method,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class BiometricVerifier:
    """
    Orquestra a captura de webcam e a inferência etária local via DeepFace.
    """

    def __init__(
        self,
        minimum_age: int = MINIMUM_AGE,
        detector_backend: str = "opencv",
    ):
        self.minimum_age = minimum_age
        self.detector_backend = detector_backend

    def capture_frame(self, camera_index: int = 0, warmup_frames: int = 5):
        """
        Captura um único frame da webcam local usando OpenCV.
        """
        import cv2  # import local: só é necessário quando de fato há captura de webcam

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise BiometricCaptureError(f"Não foi possível acessar a câmera (índice {camera_index}).")

        try:
            frame = None

            for _ in range(max(warmup_frames, 1)):
                ok, frame = cap.read()
                if not ok:
                    raise BiometricCaptureError("Falha ao ler frame da webcam.")
            return frame
        finally:
            cap.release()

    def _run_inference(self, image: Union["object", str]) -> int:
        """
        Executa a estimativa de idade localmente via DeepFace.
        """
        from deepface import DeepFace

        try:
            result = DeepFace.analyze(
                img_path=image,
                actions=["age"],
                detector_backend=self.detector_backend,
                enforce_detection=True,
                silent=True,
            )
        except ValueError as exc:
            raise AgeAnalysisError(
                "Nenhum rosto detectado na imagem capturada. Tente novamente com melhor iluminação."
            ) from exc
        except Exception as exc:
            raise AgeAnalysisError(f"Falha ao executar a inferência de idade: {exc}") from exc
        finally:
            del image

        if isinstance(result, list):
            result = result[0]

        return int(result["age"])

    def _build_claim(self, estimated_age: int, did_subject: Optional[str]) -> AgeClaim:
        is_adult = estimated_age >= self.minimum_age
        logger.info(
            f"Idade estimada: {estimated_age} anos | "
            f"Maior de idade: {is_adult}"
        )
        return AgeClaim(
            did_subject=did_subject,
            is_adult=is_adult,
            estimated_age=estimated_age,
            minimum_age_threshold=self.minimum_age,
        )

    def verify_age(self, did_subject: Optional[str] = None, camera_index: int = 0) -> AgeClaim:
        logger.info("Iniciando captura de imagem para verificação etária...")
        frame = self.capture_frame(camera_index=camera_index)

        logger.info("Executando inferência de idade 100%% local (DeepFace)...")
        try:
            estimated_age = self._run_inference(frame)
        finally:
            frame = None

        return self._build_claim(estimated_age, did_subject)

    def verify_age_from_image(self, image_path: str, did_subject: Optional[str] = None) -> AgeClaim:
        estimated_age = self._run_inference(image_path)
        return self._build_claim(estimated_age, did_subject)

    def verify_age_from_array(self, image_array, did_subject: Optional[str] = None) -> AgeClaim:
        """
        Recebe um array numpy, executa a inferência local e descarta a imagem.
        """
        logger.info("Executando inferência de idade 100%% local a partir do array em memória...")
        try:
            estimated_age = self._run_inference(image_array)
        finally:
            image_array = None

        return self._build_claim(estimated_age, did_subject)
