import logging
import os

import typer
from OpenSSL import crypto

import app.configs as cfg

cli_app = typer.Typer()

logging.getLogger("passlib").setLevel(logging.ERROR)


@cli_app.command("generate-ssl")
def generate_self_signed_cert():
    """
    Generates self-signed SSL certificates
    """

    if os.path.exists(cfg.CERT_PATH) and os.path.exists(cfg.KEY_PATH):
        print("Self-signed certificates already exist. Skipping generation.")
        return

    print("Generating self-signed SSL certificates...")
    print(f"Certificate path: {cfg.CERT_PATH}")
    print(f"Key path: {cfg.KEY_PATH}")

    # Create a new key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    # Create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "DE"
    cert.get_subject().ST = "dbmate"
    cert.get_subject().L = "dbmate"
    cert.get_subject().O = "dbmate"
    cert.get_subject().OU = "dbmate"
    cert.get_subject().CN = "dbmate"  # Or your domain name
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, "sha256")

    with open(cfg.CERT_PATH, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    with open(cfg.KEY_PATH, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

    print(f"Certificates generated: {cfg.CERT_PATH}, {cfg.KEY_PATH}")


@cli_app.command("export-openapi")
def export_openapi_to_yaml():
    """Export OpenAPI spec in YAML format"""
    import yaml

    from server import app

    openapi_json = app.openapi()
    openapi_yaml = yaml.dump(openapi_json, sort_keys=False)
    with open("openapi.yaml", "w") as f:
        f.write(openapi_yaml)

    print("OpenAPI spec exported to openapi.yaml")


if __name__ == "__main__":
    cli_app()
