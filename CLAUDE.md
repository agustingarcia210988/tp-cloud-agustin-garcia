# CLAUDE.md — PixelHub: Migración de Galería de Imágenes a S3

Este archivo es el contexto que necesita cualquier sesión de Claude Code para seguir este proyecto sin que tengas que re-explicarlo. Leelo antes de tocar nada.

## Qué es esto

Proyecto final del módulo Cloud Computing (AWS) del ITBA, a partir del starter `github.com/maxflorentin/proyecto-final-starter`. Es un **proyecto individual** (Agustín Garcia).

Caso: **PixelHub**, empresa ficticia con un catálogo de fotos de producto. Hoy un único EC2 (`app-01`) guarda las imágenes en su disco local (EBS) y las sirve desde ahí — storage acoplado al cómputo, sin redundancia. Alcance elegido: **un componente**, no la migración completa — sacar sólo el storage de imágenes a S3, dejando el resto de la app como está.

Todo corre contra **LocalStack** (no AWS real, no hay cuenta ni credenciales reales en juego).

## Estado actual — YA ESTÁ HECHO, no rehacer

- [x] **Arquitectura decidida**: S3 (bucket versionado + lifecycle a Glacier a 90 días) + IAM Role/instance profile (privilegio mínimo, sin access keys) + VPC Gateway Endpoint (gratis, sin NAT) + EC2 stateless. 4 servicios, cumple el mínimo de la consigna.
- [x] **Diagrama**: `docs/architecture.drawio` (editable en app.diagrams.net) + `docs/architecture.png` (render), antes/después.
- [x] **`docs/architecture.md`**: tabla de componentes, SPOFs identificados y decisiones de identidad.
- [x] **`docs/decisions.md`**: 6 ADRs (alcance, rol IAM vs access keys, VPC endpoint vs NAT, bucket privado vs público, lifecycle a Glacier, estrategia de corte dual-write).
- [x] **`docs/gantt.md` + `gantt.png` + `gantt.csv`**: cronograma de 4 fases (preparación, prueba/dual-write, corte, validación), fechas concretas.
- [x] **`docs/costs.md`**: estimación mensual con precios reales verificados (S3, EC2 t3.micro, transfer out, Glacier, endpoint gratis) — falta cargarla en calculator.aws y pegar el link.
- [x] **`iam/`**: `trust_policy.json`, `s3_access_policy.json` (least privilege, deny explícito de `DeleteObject`), `bucket_policy.json` (deny fuera del VPC endpoint y sin TLS).
- [x] **`scripts/`**: `iam_demo.py`, `vpc_demo.py`, `s3_demo.py`, `ec2_demo.py` — idempotentes, boto3 contra LocalStack vía `scripts/_aws.py`.
- [x] **`tests/test_infra.py`**: 10 tests unitarios con `moto` (mockeado, no requiere Docker). **Ya corridos y pasando.**
- [x] **`compose.yaml`**: LocalStack con `SERVICES=s3,iam,ec2,sts`.
- [x] **Corrida end-to-end contra LocalStack real** (2026-08-04, LocalStack 3.8 vía Docker): los 4 scripts corren en orden, un segundo pase confirma idempotencia (todo "ya existe"), y `pytest -v` da 10/10. El VPC Gateway Endpoint sí se creó en este entorno (a diferencia del gotcha documentado abajo para LocalStack Community). Nota Windows: los prints con `→` rompen en consola cp1252 — correr con `PYTHONUTF8=1`.
- [x] **Repo creado y pusheado a GitHub**: `agustingarcia210988/tp-cloud-agustin-garcia`, a partir de la estructura del starter.

No reabras estas decisiones sin una razón concreta — están documentadas en `docs/decisions.md` con el tradeoff considerado.

## Qué falta (esto sí es trabajo real pendiente)

1. **Cargar `docs/costs.md` en calculator.aws** y pegar el link compartible real (hoy tiene un placeholder).
2. Opcional / mejora: si se quiere subir de nota, agregar un 5º servicio (ej. CloudFront delante del bucket, mencionado como mejora futura en ADR 004) o pasar los scripts de AWS CLI a Terraform (`iac/` — el starter trae providers de ejemplo para LocalStack).

## Cómo correr

```bash
pip install -r requirements.txt
docker compose up -d                 # LocalStack

python scripts/iam_demo.py           # 1. rol + policy + instance profile
python scripts/vpc_demo.py           # 2. VPC + subred + gateway endpoint
python scripts/s3_demo.py            # 3. bucket + versioning + lifecycle + bucket policy
python scripts/ec2_demo.py           # 4. instancia app-01

pytest -v                            # tests unitarios (moto, no requieren Docker)
```

Cada script es idempotente (correrlo dos veces no rompe nada) e imprime qué encontró vs qué creó.

## Convenciones de código (mantenerlas si se agrega algo)

- **Sin secretos hardcodeados**: todo cliente boto3 sale de `scripts/_aws.py::client()`, que lee endpoint/credenciales del entorno.
- **Idempotencia por lectura previa**: `get_*`/`head_*`/`describe_*` primero, crear sólo si no existe (`NoSuchEntityException`, `404`, etc.).
- **Estado compartido entre scripts** en `.local/` (gitignored) — hoy sólo `vpc_demo.py` escribe `.local/vpc_output.json` con IDs que `s3_demo.py` lee para inyectar el VPC endpoint real en la bucket policy.
- **Funciones testeables**: cada `ensure_*` recibe el cliente boto3 como parámetro (no lo crea adentro), así los tests le pueden pasar un cliente mockeado con `moto`.

## Gotchas conocidos de LocalStack

- `vpc_demo.py::ensure_s3_gateway_endpoint` tiene un `try/except` alrededor de `create_vpc_endpoint`: LocalStack Community puede no soportar bien VPC endpoints. Si falla ahí, es un límite conocido del entorno, no un bug — el diseño (y la bucket policy) igual asumen que el endpoint existe, como lo haría en AWS real.
- `iam/bucket_policy.json` tiene el placeholder `vpce-REPLACE_WITH_REAL_ENDPOINT_ID`, que `s3_demo.py` reemplaza automáticamente si encuentra `.local/vpc_output.json`. LocalStack Community tampoco evalúa completo el condition key `aws:sourceVpce` — la policy se sube igual como evidencia del diseño correcto.
- `ec2_demo.py` usa una AMI de referencia (`ami-0c101f26f147fa7fd`) que LocalStack no valida que exista de verdad.

## Rúbrica del curso (para autoevaluarse antes de entregar)

Escala 0–2 por criterio: 0 nulo, 0.5 bajo, 1 en proceso, 1.5 correcto, 2 óptimo ("incluye lo no obvio"). Los criterios son: arquitectura + justificación, código reproducible en LocalStack, Gantt, costos, IAM/identidad, ADRs. Antes de entregar, revisar que cada sección tenga algo del tipo "lo no obvio" — ya están sembrados varios (transfer out en costos, deny de `DeleteObject` en IAM, deny fuera del VPC endpoint en la bucket policy, dual-write en el Gantt).

## Dónde está cada cosa

Ver el árbol completo y el checklist de la consigna en `README.md`.
