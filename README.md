# PixelHub — Migración de Galería de Imágenes a S3

Proyecto integrador del módulo Cloud Computing (ITBA) — a partir del [starter del curso](https://github.com/maxflorentin/proyecto-final-starter).

> **Integrantes:** Agustín Garcia (proyecto individual)

## El caso

**PixelHub** es una empresa ficticia que ofrece un catálogo de fotos de producto para tiendas online. Hoy, su único servidor de aplicación (`app-01`, EC2) guarda las imágenes subidas por los clientes en el disco local (EBS) y las sirve directamente desde ahí. Es el típico "storage acoplado al cómputo": si el disco se llena, se corrompe o el servidor se cae, se pierden las imágenes; y para escalar el servidor hay que migrar el disco entero.

**Alcance de este proyecto (componente, no migración completa):** mover únicamente el storage de imágenes del disco local de `app-01` a **S3**, dejando el cómputo (EC2) donde está. Es la migración de referencia de la consigna: *"Un componente: Galería de imágenes → S3 — una app saca las fotos del disco del servidor y las sirve desde S3, con acceso controlado por rol."*

## Servicios AWS usados (4, cumple el mínimo de la consigna)

| Servicio | Rol en la arquitectura |
|---|---|
| **S3** | Storage durable de las imágenes (bucket versionado + lifecycle a Glacier) |
| **IAM** | Rol de instancia con permisos mínimos (least privilege) para `app-01` |
| **VPC (Gateway Endpoint)** | Ruta privada de la subred de `app-01` hacia S3, sin salir a internet |
| **EC2** | Servidor de aplicación que ahora es stateless (no guarda imágenes localmente) |

## Cómo arrancar (LocalStack)

Requisitos: Docker, Docker Compose, Python 3.11+.

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Levantar LocalStack
docker compose up -d

# 3. Correr las demos en orden (son idempotentes — se pueden re-correr)
python scripts/iam_demo.py
python scripts/vpc_demo.py
python scripts/s3_demo.py
python scripts/ec2_demo.py

# 4. Correr los tests unitarios (mockeados con moto, no requieren Docker)
pytest -v
```

Cada script imprime qué recurso creó (o encontró ya existente) y su ARN/ID.

## Estructura del repo

```
.
├── README.md
├── compose.yaml            # LocalStack
├── requirements.txt
├── docs/
│   ├── architecture.md     # componentes, SPOFs, decisiones de identidad
│   ├── architecture.drawio # diagrama editable (abrir en app.diagrams.net)
│   ├── decisions.md        # 5 ADRs
│   ├── gantt.md            # cronograma de migración
│   ├── gantt.png           # diagrama de Gantt
│   ├── gantt.csv           # datos del Gantt (editable)
│   └── costs.md            # estimación mensual (AWS Pricing Calculator)
├── iam/
│   ├── trust_policy.json          # quién puede asumir el rol (EC2)
│   ├── s3_access_policy.json      # identity policy — permisos mínimos sobre el bucket
│   ├── bucket_policy.json         # resource policy — sólo desde el VPC endpoint
│   └── README.md
├── scripts/
│   ├── iam_demo.py
│   ├── s3_demo.py
│   ├── vpc_demo.py
│   ├── ec2_demo.py
│   └── README.md
└── tests/
    └── test_infra.py       # pytest + moto
```

## Checklist del proyecto

- [x] `docs/architecture.md` con diagrama y componentes
- [x] `docs/decisions.md` con 5 decisiones documentadas (ADR)
- [x] `iam/` con los JSON de la solución (trust + identity + bucket policy)
- [x] `scripts/` con 4 demos automatizados (idempotentes)
- [x] `compose.yaml` con LocalStack
- [x] Tests unitarios (`pytest` pasa)
- [x] `docs/gantt.*` — cronograma de migración
- [x] `docs/costs.md` — estimación de costos mensual
- [x] README con integrantes completados (proyecto individual)
- [x] Repo creado a partir del starter y pusheado a GitHub: [agustingarcia210988/tp-cloud-agustin-garcia](https://github.com/agustingarcia210988/tp-cloud-agustin-garcia)
- [x] Corrida real contra LocalStack con Docker (validado end-to-end el 2026-08-04: los 4 scripts corren e idempotentes en un segundo pase, `pytest -v` → 10 passed)
- [x] Estimación cargada en calculator.aws con link guardado en `docs/costs.md` (total oficial: $62.42/mes)

## Próximo paso

1. Subir los dos PNG (`docs/architecture.png`, `docs/gantt.png`) al repo de GitHub — son binarios, se suben a mano ("Add file" → "Upload files").
2. Revisar la rúbrica una vez más antes de entregar (ver `CLAUDE.md`).

> Nota (Windows): si corrés los scripts en una consola con codepage cp1252, vas a ver `UnicodeEncodeError` en los prints con `→`. No es un bug del código — corré con `PYTHONUTF8=1 python scripts/...` (o `set PYTHONUTF8=1` antes). En Linux/Mac no hace falta, la consola ya es UTF-8.
