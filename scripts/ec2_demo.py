#!/usr/bin/env python3
"""
EC2 demo — app-01, ahora stateless: arranca con el instance profile del
rol IAM (sin credenciales hardcodeadas) y en la subred con salida a S3
por el Gateway Endpoint.

Depende de haber corrido antes iam_demo.py (instance profile) y
vpc_demo.py (subred). Si falta alguno, avisa en vez de crashear.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _aws import client, local_state_dir  # noqa: E402

INSTANCE_NAME = "app-01"
INSTANCE_PROFILE_NAME = "pixelhub-app-instance-profile"
INSTANCE_TYPE = "t3.micro"
# AMI de referencia (Amazon Linux 2 en us-east-1). LocalStack no valida
# que la AMI exista realmente para este tipo de demo.
DEMO_AMI_ID = "ami-0c101f26f147fa7fd"


def find_existing_instance(ec2, name: str) -> str | None:
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [name]},
            {"Name": "instance-state-name", "Values": ["pending", "running"]},
        ]
    )
    for reservation in resp["Reservations"]:
        for instance in reservation["Instances"]:
            return instance["InstanceId"]
    return None


def ensure_instance(ec2, name: str, subnet_id: str | None, profile_name: str) -> str | None:
    existing = find_existing_instance(ec2, name)
    if existing:
        print(f"  = instancia ya existe: {existing}")
        return existing

    kwargs = dict(
        ImageId=DEMO_AMI_ID,
        InstanceType=INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={"Name": profile_name},
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": name}]}
        ],
    )
    if subnet_id:
        kwargs["SubnetId"] = subnet_id

    try:
        resp = ec2.run_instances(**kwargs)
        instance_id = resp["Instances"][0]["InstanceId"]
        print(f"  + instancia creada: {instance_id}")
        return instance_id
    except Exception as exc:  # noqa: BLE001
        print(f"  ! no se pudo lanzar la instancia en este entorno: {exc}")
        return None


def main() -> None:
    ec2 = client("ec2")

    vpc_state_path = local_state_dir() / "vpc_output.json"
    subnet_id = None
    if vpc_state_path.exists():
        subnet_id = json.loads(vpc_state_path.read_text()).get("subnet_id")
    else:
        print("  ! no se encontró .local/vpc_output.json — corré vpc_demo.py primero")

    print(f"→ Instancia {INSTANCE_NAME} (stateless, sin storage local de imágenes)")
    instance_id = ensure_instance(ec2, INSTANCE_NAME, subnet_id, INSTANCE_PROFILE_NAME)

    print()
    print("Listo:", instance_id or "(no se pudo confirmar en este entorno, ver arriba)")


if __name__ == "__main__":
    main()
