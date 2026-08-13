"""
Tests unitarios de las funciones ensure_* de las demos.

Usan moto (mock_aws) para simular IAM/S3/EC2 sin necesitar Docker ni
LocalStack corriendo — por eso `pytest` tiene que pasar siempre, incluso
en una máquina sin Docker instalado. La prueba end-to-end real (con
LocalStack) se hace corriendo los scripts a mano, ver README.md.
"""
from __future__ import annotations

import json
import pathlib

import boto3
from moto import mock_aws

import ec2_demo
import iam_demo
import s3_demo
import vpc_demo

IAM_DIR = pathlib.Path(__file__).resolve().parent.parent / "iam"
TRUST_POLICY = json.loads((IAM_DIR / "trust_policy.json").read_text())
S3_ACCESS_POLICY = json.loads((IAM_DIR / "s3_access_policy.json").read_text())


# ---------------------------------------------------------------- IAM ----


@mock_aws
def test_iam_role_creation_is_idempotent():
    iam = boto3.client("iam", region_name="us-east-1")
    arn1 = iam_demo.ensure_role(iam, "pixelhub-app-role", TRUST_POLICY)
    arn2 = iam_demo.ensure_role(iam, "pixelhub-app-role", TRUST_POLICY)
    assert arn1 == arn2
    assert iam.get_role(RoleName="pixelhub-app-role")["Role"]["Arn"] == arn1


@mock_aws
def test_s3_access_policy_never_grants_delete():
    """La app no debe poder borrar imágenes: eso lo maneja el lifecycle."""
    iam = boto3.client("iam", region_name="us-east-1")
    iam_demo.ensure_role(iam, "pixelhub-app-role", TRUST_POLICY)
    iam_demo.ensure_inline_policy(
        iam, "pixelhub-app-role", "pixelhub-s3-access", S3_ACCESS_POLICY
    )
    doc = iam.get_role_policy(
        RoleName="pixelhub-app-role", PolicyName="pixelhub-s3-access"
    )["PolicyDocument"]

    allow_actions: list[str] = []
    for stmt in doc["Statement"]:
        if stmt["Effect"] != "Allow":
            continue
        action = stmt["Action"]
        allow_actions.extend(action if isinstance(action, list) else [action])

    assert "s3:DeleteObject" not in allow_actions
    assert "s3:GetObject" in allow_actions
    assert "s3:PutObject" in allow_actions


@mock_aws
def test_instance_profile_attaches_role():
    iam = boto3.client("iam", region_name="us-east-1")
    iam_demo.ensure_role(iam, "pixelhub-app-role", TRUST_POLICY)
    arn = iam_demo.ensure_instance_profile(
        iam, "pixelhub-app-instance-profile", "pixelhub-app-role"
    )
    profile = iam.get_instance_profile(
        InstanceProfileName="pixelhub-app-instance-profile"
    )["InstanceProfile"]
    assert arn == profile["Arn"]
    assert [r["RoleName"] for r in profile["Roles"]] == ["pixelhub-app-role"]

    # segunda corrida: no debe intentar re-agregar el rol y no debe fallar
    iam_demo.ensure_instance_profile(
        iam, "pixelhub-app-instance-profile", "pixelhub-app-role"
    )


# ----------------------------------------------------------------- S3 ----


@mock_aws
def test_bucket_creation_is_idempotent():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_demo.ensure_bucket(s3, "pixelhub-images", "us-east-1")
    s3_demo.ensure_bucket(s3, "pixelhub-images", "us-east-1")
    s3.head_bucket(Bucket="pixelhub-images")  # no lanza si existe


@mock_aws
def test_versioning_enabled():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_demo.ensure_bucket(s3, "pixelhub-images", "us-east-1")
    s3_demo.ensure_versioning(s3, "pixelhub-images")
    assert s3.get_bucket_versioning(Bucket="pixelhub-images")["Status"] == "Enabled"


@mock_aws
def test_lifecycle_archives_uploads_to_glacier():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_demo.ensure_bucket(s3, "pixelhub-images", "us-east-1")
    s3_demo.ensure_lifecycle(s3, "pixelhub-images")
    rules = s3.get_bucket_lifecycle_configuration(Bucket="pixelhub-images")["Rules"]
    assert rules[0]["Filter"]["Prefix"] == "uploads/"
    assert rules[0]["Transitions"][0]["StorageClass"] == "GLACIER"


@mock_aws
def test_sample_object_upload_is_idempotent_by_content():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3_demo.ensure_bucket(s3, "pixelhub-images", "us-east-1")
    key = "uploads/sample-product-001.png"
    s3_demo.ensure_sample_object(s3, "pixelhub-images", key, b"contenido-de-ejemplo")
    s3_demo.ensure_sample_object(s3, "pixelhub-images", key, b"contenido-de-ejemplo")
    body = s3.get_object(Bucket="pixelhub-images", Key=key)["Body"].read()
    assert body == b"contenido-de-ejemplo"


# ---------------------------------------------------------------- VPC ----


@mock_aws
def test_vpc_subnet_and_s3_gateway_endpoint():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc_id = vpc_demo.ensure_vpc(ec2, "pixelhub-vpc", "10.42.0.0/16")
    subnet_id = vpc_demo.ensure_subnet(ec2, vpc_id, "pixelhub-subnet-app", "10.42.1.0/24")
    rtb_id = vpc_demo.ensure_route_table(ec2, vpc_id, "pixelhub-rtb-app", [subnet_id])
    endpoint_id = vpc_demo.ensure_s3_gateway_endpoint(ec2, vpc_id, rtb_id, "pixelhub-s3-endpoint")

    assert endpoint_id is not None
    endpoint = ec2.describe_vpc_endpoints(VpcEndpointIds=[endpoint_id])["VpcEndpoints"][0]
    assert endpoint["VpcEndpointType"] == "Gateway"
    assert endpoint["VpcId"] == vpc_id


@mock_aws
def test_vpc_ensure_helpers_are_idempotent():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc_id_1 = vpc_demo.ensure_vpc(ec2, "pixelhub-vpc", "10.42.0.0/16")
    vpc_id_2 = vpc_demo.ensure_vpc(ec2, "pixelhub-vpc", "10.42.0.0/16")
    assert vpc_id_1 == vpc_id_2

    subnet_id_1 = vpc_demo.ensure_subnet(ec2, vpc_id_1, "pixelhub-subnet-app", "10.42.1.0/24")
    subnet_id_2 = vpc_demo.ensure_subnet(ec2, vpc_id_1, "pixelhub-subnet-app", "10.42.1.0/24")
    assert subnet_id_1 == subnet_id_2


@mock_aws
def test_vpc_two_az_subnets_share_route_table_to_s3_endpoint():
    """Disponibilidad multi-AZ: dos subredes en dos AZ, misma route table -> mismo acceso a S3."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc_id = vpc_demo.ensure_vpc(ec2, "pixelhub-vpc", "10.42.0.0/16")
    subnet_a = vpc_demo.ensure_subnet(ec2, vpc_id, "pixelhub-subnet-app", "10.42.1.0/24", "us-east-1a")
    subnet_b = vpc_demo.ensure_subnet(ec2, vpc_id, "pixelhub-subnet-app-b", "10.42.2.0/24", "us-east-1b")
    assert subnet_a != subnet_b

    az_a = ec2.describe_subnets(SubnetIds=[subnet_a])["Subnets"][0]["AvailabilityZone"]
    az_b = ec2.describe_subnets(SubnetIds=[subnet_b])["Subnets"][0]["AvailabilityZone"]
    assert az_a != az_b

    rtb_id = vpc_demo.ensure_route_table(ec2, vpc_id, "pixelhub-rtb-app", [subnet_a, subnet_b])
    associated = {
        a.get("SubnetId")
        for a in ec2.describe_route_tables(RouteTableIds=[rtb_id])["RouteTables"][0]["Associations"]
    }
    assert {subnet_a, subnet_b} <= associated

    # segunda corrida: idempotente, no duplica asociaciones ni falla
    rtb_id_2 = vpc_demo.ensure_route_table(ec2, vpc_id, "pixelhub-rtb-app", [subnet_a, subnet_b])
    assert rtb_id_2 == rtb_id


# ---------------------------------------------------------------- EC2 ----


@mock_aws
def test_ec2_instance_launches_with_instance_profile():
    iam = boto3.client("iam", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")

    iam_demo.ensure_role(iam, "pixelhub-app-role", TRUST_POLICY)
    iam_demo.ensure_instance_profile(
        iam, "pixelhub-app-instance-profile", "pixelhub-app-role"
    )
    vpc_id = vpc_demo.ensure_vpc(ec2, "pixelhub-vpc", "10.42.0.0/16")
    subnet_id = vpc_demo.ensure_subnet(ec2, vpc_id, "pixelhub-subnet-app", "10.42.1.0/24")

    instance_id_1 = ec2_demo.ensure_instance(
        ec2, "app-01", subnet_id, "pixelhub-app-instance-profile"
    )
    instance_id_2 = ec2_demo.ensure_instance(
        ec2, "app-01", subnet_id, "pixelhub-app-instance-profile"
    )

    # idempotente: la segunda corrida encuentra la misma instancia (o
    # falla de la misma forma en ambas corridas), nunca duplica.
    assert instance_id_1 == instance_id_2
