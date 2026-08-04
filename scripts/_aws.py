"""
Helper compartido por las demos: crea clientes boto3 apuntando a LocalStack.

No hay secretos hardcodeados: las credenciales y el endpoint se leen del
entorno (con defaults sensatos para LocalStack, que ignora el valor real
de las credenciales pero exige que existan).
"""
from __future__ import annotations

import os

import boto3
from dotenv import load_dotenv

load_dotenv()

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = os.getenv("AWS_REGION", "us-east-1")


def client(service_name: str):
    """Cliente boto3 contra LocalStack (o contra AWS real si se apunta el endpoint)."""
    kwargs = {"region_name": REGION}
    # Sólo forzamos endpoint + credenciales fake si estamos contra LocalStack.
    if "localhost" in ENDPOINT_URL or "localstack" in ENDPOINT_URL:
        kwargs.update(
            endpoint_url=ENDPOINT_URL,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        )
    return boto3.client(service_name, **kwargs)


def resource(service_name: str):
    kwargs = {"region_name": REGION}
    if "localhost" in ENDPOINT_URL or "localstack" in ENDPOINT_URL:
        kwargs.update(
            endpoint_url=ENDPOINT_URL,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        )
    return boto3.resource(service_name, **kwargs)


def project_root():
    import pathlib

    return pathlib.Path(__file__).resolve().parent.parent


def local_state_dir():
    """Carpeta para compartir IDs generados entre scripts (no se commitea)."""
    p = project_root() / ".local"
    p.mkdir(exist_ok=True)
    return p
