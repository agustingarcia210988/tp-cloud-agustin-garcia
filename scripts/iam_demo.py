#!/usr/bin/env python3
"""
IAM demo — crea el rol que va a asumir app-01 (EC2) para hablar con S3.

Idempotente: se puede correr N veces, sólo crea lo que falta.
Patrón: primero intentar leer (get_*), crear sólo si NoSuchEntityException.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _aws import client, project_root  # noqa: E402

ROLE_NAME = "pixelhub-app-role"
INLINE_POLICY_NAME = "pixelhub-s3-access"
INSTANCE_PROFILE_NAME = "pixelhub-app-instance-profile"

IAM_DIR = project_root() / "iam"


def ensure_role(iam, role_name: str, trust_policy: dict) -> str:
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        print(f"  = rol ya existe: {role['Arn']}")
        return role["Arn"]
    except iam.exceptions.NoSuchEntityException:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Rol de app-01 (EC2) para leer/escribir imágenes en S3",
        )["Role"]
        print(f"  + rol creado: {role['Arn']}")
        return role["Arn"]


def ensure_inline_policy(iam, role_name: str, policy_name: str, policy_doc: dict) -> None:
    # put_role_policy es upsert: crea o reemplaza. Idempotente por diseño.
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_doc),
    )
    print(f"  = policy '{policy_name}' aplicada a {role_name}")


def ensure_instance_profile(iam, profile_name: str, role_name: str) -> str:
    try:
        profile = iam.get_instance_profile(InstanceProfileName=profile_name)["InstanceProfile"]
        print(f"  = instance profile ya existe: {profile['Arn']}")
    except iam.exceptions.NoSuchEntityException:
        profile = iam.create_instance_profile(InstanceProfileName=profile_name)["InstanceProfile"]
        print(f"  + instance profile creado: {profile['Arn']}")

    attached_roles = [r["RoleName"] for r in profile.get("Roles", [])]
    if role_name not in attached_roles:
        iam.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)
        print(f"  + rol {role_name} agregado al instance profile")
    else:
        print(f"  = rol {role_name} ya estaba en el instance profile")

    return profile["Arn"]


def main() -> None:
    iam = client("iam")

    trust_policy = json.loads((IAM_DIR / "trust_policy.json").read_text())
    s3_policy = json.loads((IAM_DIR / "s3_access_policy.json").read_text())

    print("→ Rol de la aplicación")
    role_arn = ensure_role(iam, ROLE_NAME, trust_policy)

    print("→ Identity policy (privilegio mínimo sobre uploads/*)")
    ensure_inline_policy(iam, ROLE_NAME, INLINE_POLICY_NAME, s3_policy)

    print("→ Instance profile (para asociarlo a la EC2 de app-01)")
    profile_arn = ensure_instance_profile(iam, INSTANCE_PROFILE_NAME, ROLE_NAME)

    print()
    print("Listo:")
    print(f"  role_arn:    {role_arn}")
    print(f"  profile_arn: {profile_arn}")


if __name__ == "__main__":
    main()
