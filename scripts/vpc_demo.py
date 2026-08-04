#!/usr/bin/env python3
"""
VPC demo — red aislada para app-01 + Gateway Endpoint privado hacia S3.

Con el endpoint, el tráfico de app-01 a S3 va por el backbone de AWS
(sin NAT Gateway, sin salir a internet, sin costo de endpoint: los
Gateway Endpoints de S3 son gratis).

Idempotente vía find-by-tag: cada ensure_* primero busca por Name tag
antes de crear.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _aws import REGION, client, local_state_dir  # noqa: E402

VPC_NAME = "pixelhub-vpc"
SUBNET_NAME = "pixelhub-subnet-app"
RTB_NAME = "pixelhub-rtb-app"
ENDPOINT_NAME = "pixelhub-s3-endpoint"

VPC_CIDR = "10.42.0.0/16"
SUBNET_CIDR = "10.42.1.0/24"


def _find_by_tag(ec2, describe_fn, list_key, id_key, name: str):
    resp = describe_fn(Filters=[{"Name": "tag:Name", "Values": [name]}])
    items = resp[list_key]
    return items[0][id_key] if items else None


def ensure_vpc(ec2, name: str, cidr: str) -> str:
    vpc_id = _find_by_tag(ec2, ec2.describe_vpcs, "Vpcs", "VpcId", name)
    if vpc_id:
        print(f"  = VPC ya existe: {vpc_id}")
        return vpc_id
    vpc_id = ec2.create_vpc(CidrBlock=cidr)["Vpc"]["VpcId"]
    ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": name}])
    print(f"  + VPC creada: {vpc_id}")
    return vpc_id


def ensure_subnet(ec2, vpc_id: str, name: str, cidr: str) -> str:
    resp = ec2.describe_subnets(
        Filters=[{"Name": "tag:Name", "Values": [name]}, {"Name": "vpc-id", "Values": [vpc_id]}]
    )
    if resp["Subnets"]:
        subnet_id = resp["Subnets"][0]["SubnetId"]
        print(f"  = subred ya existe: {subnet_id}")
        return subnet_id
    subnet_id = ec2.create_subnet(VpcId=vpc_id, CidrBlock=cidr)["Subnet"]["SubnetId"]
    ec2.create_tags(Resources=[subnet_id], Tags=[{"Key": "Name", "Value": name}])
    print(f"  + subred creada: {subnet_id}")
    return subnet_id


def ensure_route_table(ec2, vpc_id: str, name: str, subnet_id: str) -> str:
    resp = ec2.describe_route_tables(
        Filters=[{"Name": "tag:Name", "Values": [name]}, {"Name": "vpc-id", "Values": [vpc_id]}]
    )
    if resp["RouteTables"]:
        rtb_id = resp["RouteTables"][0]["RouteTableId"]
        print(f"  = route table ya existe: {rtb_id}")
    else:
        rtb_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
        ec2.create_tags(Resources=[rtb_id], Tags=[{"Key": "Name", "Value": name}])
        print(f"  + route table creada: {rtb_id}")

    associations = ec2.describe_route_tables(RouteTableIds=[rtb_id])["RouteTables"][0].get(
        "Associations", []
    )
    already_associated = any(a.get("SubnetId") == subnet_id for a in associations)
    if not already_associated:
        ec2.associate_route_table(RouteTableId=rtb_id, SubnetId=subnet_id)
        print(f"  + route table asociada a la subred {subnet_id}")

    return rtb_id


def ensure_s3_gateway_endpoint(ec2, vpc_id: str, rtb_id: str, name: str) -> str | None:
    service_name = f"com.amazonaws.{REGION}.s3"
    resp = ec2.describe_vpc_endpoints(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "service-name", "Values": [service_name]},
        ]
    )
    active = [e for e in resp["VpcEndpoints"] if e["State"] not in ("deleted", "deleting")]
    if active:
        endpoint_id = active[0]["VpcEndpointId"]
        print(f"  = VPC endpoint ya existe: {endpoint_id}")
        return endpoint_id

    try:
        endpoint = ec2.create_vpc_endpoint(
            VpcId=vpc_id,
            ServiceName=service_name,
            RouteTableIds=[rtb_id],
            VpcEndpointType="Gateway",
        )["VpcEndpoint"]
        endpoint_id = endpoint["VpcEndpointId"]
        ec2.create_tags(Resources=[endpoint_id], Tags=[{"Key": "Name", "Value": name}])
        print(f"  + VPC Gateway Endpoint creado: {endpoint_id} (gratis, sin cargo por hora)")
        return endpoint_id
    except Exception as exc:  # noqa: BLE001 — LocalStack Community puede no soportarlo
        print(f"  ! no se pudo crear el VPC endpoint en este entorno LocalStack: {exc}")
        print("    (limitación conocida de LocalStack Community con algunos endpoints de EC2/VPC;")
        print("     el diseño y la bucket policy igual asumen que el endpoint existe)")
        return None


def main() -> None:
    ec2 = client("ec2")

    print("→ VPC de PixelHub")
    vpc_id = ensure_vpc(ec2, VPC_NAME, VPC_CIDR)

    print("→ Subred de app-01")
    subnet_id = ensure_subnet(ec2, vpc_id, SUBNET_NAME, SUBNET_CIDR)

    print("→ Route table")
    rtb_id = ensure_route_table(ec2, vpc_id, RTB_NAME, subnet_id)

    print("→ Gateway Endpoint hacia S3")
    endpoint_id = ensure_s3_gateway_endpoint(ec2, vpc_id, rtb_id, ENDPOINT_NAME)

    state = {
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "route_table_id": rtb_id,
        "vpc_endpoint_id": endpoint_id,
    }
    (local_state_dir() / "vpc_output.json").write_text(json.dumps(state, indent=2))

    print()
    print("Listo:", json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
