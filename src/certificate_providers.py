import datetime
from abc import ABC, abstractmethod
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from lab_config import config
import os

# Get the directory where compose_providers.py is located
compose_providers_dir = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory of the compose directory
parent_dir = os.path.dirname(compose_providers_dir)

# Create the certs directory inside the parent directory if it doesn't exist
certs_dir = os.path.join(parent_dir, 'certs')
os.makedirs(certs_dir, exist_ok=True)


class CertificateProvider(ABC):
    """
    Abstract class defining the interface for certificate providers.
    """

    @abstractmethod
    def generate_certificates(self, domain: str):
        """
        Generates or retrieves the certificates for the given domain.
        """
        pass

    @abstractmethod
    def get_certificate_paths(self, lab_subdomain: str) -> tuple:
        """
        Returns the paths to the certificate and key files.
        """
        pass


class NoneProvider(CertificateProvider):
    """
    A no-op certificate provider implementation that signifies no SSL/TLS configuration.
    """

    def generate_certificates(self, domain: str):
        """
        No-op implementation.
        """
        pass

    def get_certificate_paths(self, lab_subdomain: str) -> tuple:
        """
        Returns None for both certificate and key paths.
        """
        return None, None


class SelfSignedProvider(CertificateProvider):
    """
    Self-Signed certificate provider implementation that generates wildcard certificates for subdomains.
    """

    def __init__(self):
        """
        Initializes the certificate provider.
        """
        self.cert_dir = certs_dir

    def generate_certificates(self, lab_subdomain: str):
        """
        Generates a self-signed wildcard certificate for the given lab subdomain if it doesn't exist.
        """
        cert_path = os.path.join(self.cert_dir, f"{lab_subdomain}.crt")
        key_path = os.path.join(self.cert_dir, f"{lab_subdomain}.key")
        # Check if the certificate and key files already exist
        if os.path.exists(cert_path) and os.path.exists(key_path):
            return

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Generate self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(x509.NameOID.COMMON_NAME, f"*.{lab_subdomain}.{config['domain']}"),
            x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "OWASP"),
            x509.NameAttribute(x509.NameOID.ORGANIZATIONAL_UNIT_NAME, "SamuraiWTF")
        ])
        cert = (x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
                .sign(private_key, hashes.SHA256(), default_backend()))

        # Write the private key and certificate to files
        with open(key_path, "wb") as key_file:
            key_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_path, "wb") as cert_file:
            cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

    def get_certificate_paths(self, lab_subdomain: str) -> tuple:
        """
        Returns the paths to the wildcard certificate and key files for the given lab subdomain.
        """
        # If the certificate and key files don't exist, generate them
        self.generate_certificates(lab_subdomain)

        cert_path = os.path.join(self.cert_dir, f"{lab_subdomain}.crt")
        key_path = os.path.join(self.cert_dir, f"{lab_subdomain}.key")
        return cert_path, key_path
