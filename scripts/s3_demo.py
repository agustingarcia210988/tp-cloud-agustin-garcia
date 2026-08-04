#!/usr/bin/env python3
"""
S3 demo — el bucket que reemplaza el disco local de app-01.

Cubre: creación idempotente, versionado, lifecycle a Glacier, una
subida de ejemplo (idempotente por head_object) y la bucket policy
que sólo deja pasar tráfico desde el VPC endpoint.
"""
from __future__ import annotations

import json
import pathlib
import sys

from botocore.exceptions import ClientError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _aws import REGION, client, local_state_dir, project_root  # noqa: E402

BUCKET_NAME = "pixelhub-images"
SAMPLE_KEY = "uploads/sample-product-001.png"
IAM_DIR = project_root() / "iam"


def ensure_bucket(s3, bucket_name: str, region: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"  = bucket ya existe: {bucket_name}")
        return
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code not in ("404", "NoSuchBucket"):
            raise

    if region == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    print(f"  + bucket creado: {bucket_name}")


def ensure_versioning(s3, bucket_name: str) -> None:
    status = s3.get_bucket_versioning(Bucket=bucket_name).get("Status")
    if status == "Enabled":
        print("  = versioning ya está habilitado")
        return
    s3.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    print("  + versioning habilitado")


def ensure_lifecycle(s3, bucket_name: str) -> None:
    rule = {
        "ID": "archive-old-uploads-to-glacier",
        "Filter": {"Prefix": "uploads/"},
        "Status": "Enabled",
        "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}],
        "NoncurrentVersionTransitions": [{"NoncurrentDays": 30, "StorageClass": "GLACIER"}],
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
    }
    # put_bucket_lifecycle_configuration reemplaza la config entera -> upsert idempotente.
    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket_name, LifecycleConfiguration={"Rules": [rule]}
    )
    print("  = lifecycle aplicado (uploads/ -> Glacier a los 90 días)")


def ensure_sample_object(s3, bucket_name: str, key: str, content: bytes) -> None:
    try:
        s3.head_object(Bucket=bucket_name, Key=key)
        print(f"  = objeto de ejemplo ya existe: {key}")
        return
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code not in ("404", "NoSuchKey"):
            raise

    s3.put_object(Bucket=bucket_name, Key=key, Body=content, ContentType="image/png")
    print(f"  + objeto de ejemplo subido: {key}")


def apply_bucket_policy(s3, bucket_name: str) -> None:
    policy = json.loads((IAM_DIR / "bucket_policy.json").read_text())

    vpc_state_path = local_state_dir() / "vpc_output.json"
    endpoint_id = None
    if vpc_state_path.exists():
        endpoint_id = json.loads(vpc_state_path.read_text()).get("vpc_endpoint_id")

    if endpoint_id:
        policy = json.loads(
            json.dumps(policy).replace("vpce-REPLACE_WITH_REAL_ENDPOINT_ID", endpoint_id)
        )
        print(f"  bucket policy referencia el VPC endpoint real: {endpoint_id}")
    else:
        print(
            "  ! corré scripts/vpc_demo.py antes para tener el vpc_endpoint_id real; "
            "se sube la policy con el placeholder por ahora"
        )

    try:
        s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
        print("  = bucket policy aplicada")
    except ClientError as exc:
        print(f"  ! no se pudo aplicar la bucket policy en este entorno: {exc}")


def main() -> None:
    s3 = client("s3")

    print("→ Bucket de imágenes")
    ensure_bucket(s3, BUCKET_NAME, REGION)

    print("→ Versionado")
    ensure_versioning(s3, BUCKET_NAME)

    print("→ Lifecycle (archivado a Glacier)")
    ensure_lifecycle(s3, BUCKET_NAME)

    print("→ Objeto de ejemplo")
    ensure_sample_object(s3, BUCKET_NAME, SAMPLE_KEY, b"contenido-de-ejemplo-no-es-un-png-real")

    print("→ Bucket policy (sólo desde el VPC endpoint)")
    apply_bucket_policy(s3, BUCKET_NAME)

    print()
    print(f"Listo: s3://{BUCKET_NAME}/{SAMPLE_KEY}")


if __name__ == "__main__":
    main()
