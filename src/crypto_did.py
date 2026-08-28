import json
import base64
import hashlib
import logging
import os
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class CryptoDID:
    """
    Orquestra a criação de Identidades Autossoberanas (US01) e a 
    assinatura de consentimentos e alegações (US03/US06) de forma 100% local.
    """

    KDF_ITERATIONS = 480_000

    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.did = None
        self.public_key_b64 = None

    def generate_identity(self) -> dict:
        """
        Gera um par de chaves Ed25519 e um DID (Decentralized Identifier)
        sem depender de servidores de terceiros ou formulários web.
        """
        logger.info("Gerando novo par de chaves criptográficas Ed25519...")
        
        # Geração da chave privada
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

        # Extração da chave pública em formato Raw
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        self.public_key_b64 = base64.b64encode(pub_bytes).decode('utf-8')

        # Derivação do DID a partir do hash da chave pública
        pub_hash = hashlib.sha256(pub_bytes).hexdigest()[:16]
        self.did = f"did:poc:{pub_hash}"

        logger.info(f"Identidade Autossoberana estabelecida. DID: {self.did}")

        return {
            "did": self.did,
            "public_key": self.public_key_b64
        }

    @staticmethod
    def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    def save_keystore(self, password: str, path: str) -> None:
        """
        Persiste a identidade atual (chave privada incluída) em disco,
        criptografada com a senha informada.
        """
        if not self.private_key:
            raise ValueError("Identidade não inicializada. Execute generate_identity() primeiro.")
        if not password:
            raise ValueError("Uma senha é obrigatória para proteger o keystore local.")

        priv_bytes = self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        salt = os.urandom(16)
        key = self._derive_key(password, salt, self.KDF_ITERATIONS)
        encrypted_private_key = Fernet(key).encrypt(priv_bytes)

        keystore = {
            "version": 1,
            "did": self.did,
            "public_key": self.public_key_b64,
            "kdf": "pbkdf2_sha256",
            "kdf_iterations": self.KDF_ITERATIONS,
            "salt": base64.b64encode(salt).decode("utf-8"),
            "encrypted_private_key": encrypted_private_key.decode("utf-8"),
        }

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(keystore, f, indent=2)

        logger.info(f"Keystore criptografado salvo em '{path}'. DID: {self.did}")

    @classmethod
    def load_keystore(cls, password: str, path: str) -> "CryptoDID":
        """
        Restaura uma identidade previamente salva com save_keystore(), a
        partir da senha correta.
        """
        with open(path, "r", encoding="utf-8") as f:
            keystore = json.load(f)

        salt = base64.b64decode(keystore["salt"])
        iterations = keystore.get("kdf_iterations", cls.KDF_ITERATIONS)
        key = cls._derive_key(password, salt, iterations)

        try:
            priv_bytes = Fernet(key).decrypt(keystore["encrypted_private_key"].encode("utf-8"))
        except InvalidToken:
            raise ValueError("Senha incorreta ou arquivo de keystore corrompido.")

        instance = cls()
        instance.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
        instance.public_key = instance.private_key.public_key()
        instance.public_key_b64 = keystore["public_key"]
        instance.did = keystore["did"]

        logger.info(f"Identidade restaurada do keystore local. DID: {instance.did}")
        return instance

    @staticmethod
    def keystore_exists(path: str) -> bool:
        return os.path.isfile(path)

    def sign_payload(self, payload: dict) -> str:
        """
        Gera uma assinatura digital a partir de um dicionário (ex: AgeClaim 
        ou payload de consentimento do RAG) usando a chave privada.
        """
        if not self.private_key:
            raise ValueError("Identidade não inicializada. Execute generate_identity() primeiro.")

        # Serialização rigorosa para garantir consistência no hash/assinatura
        payload_bytes = json.dumps(
            payload, 
            sort_keys=True, 
            separators=(',', ':')
        ).encode('utf-8')
        
        signature = self.private_key.sign(payload_bytes)
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def verify_signature(public_key_b64: str, payload: dict, signature_b64: str) -> bool:
        """
        Valida se o payload foi assinado pelo dono da chave pública.
        Usado pelo SecureRAG para validar o termo de consentimento.
        """
        try:
            # Reconstrução da chave pública a partir da string em base64
            pub_bytes = base64.b64decode(public_key_b64)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

            # Decodificação da assinatura e preparação do payload
            signature = base64.b64decode(signature_b64)
            payload_bytes = json.dumps(
                payload, 
                sort_keys=True, 
                separators=(',', ':')
            ).encode('utf-8')

            # Validação criptográfica
            public_key.verify(signature, payload_bytes)
            return True
            
        except InvalidSignature:
            logger.warning("Bloqueio de Segurança: Assinatura inválida. Dados adulterados ou chave incorreta.")
            return False
        except Exception as exc:
            logger.error(f"Erro interno ao verificar a assinatura: {exc}")
            return False
