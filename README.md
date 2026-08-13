# PixelHub — Migración de Galería de Imágenes a S3

Proyecto integrador de Cloud Computing (AWS), ITBA — a partir del [starter del curso](https://github.com/maxflorentin/proyecto-final-starter).

> Agustín Garcia — proyecto individual

## El caso

PixelHub es una empresa ficticia con un catálogo de fotos de producto para tiendas online. Tienen un solo servidor (`app-01`, EC2) que guarda las imágenes que suben los clientes directo en su disco local y las sirve desde ahí. El problema de siempre: si el disco se llena, se corrompe o el servidor se cae, se pierden las imágenes, y si algún día quieren escalar el servidor tienen que arrastrar el disco entero con él.

Decidí migrar sólo el storage a S3 — no toda la app — dejando el cómputo como está. Es la opción "un componente" que da la consigna, y en este caso coincide casi textual con uno de los ejemplos: sacar las fotos del disco del servidor y servirlas desde S3 con acceso controlado por rol.

## Servicios usados

| Servicio | Para qué |
|---|---|
| S3 | Guarda las imágenes: bucket versionado, con lifecycle a Glacier para lo que ya nadie mira |
| IAM | Rol de instancia con permisos mínimos para `app-01`, sin access keys |
| VPC (Gateway Endpoint) | Ruta privada hacia S3 sin salir a internet |
| EC2 | `app-01`, que ahora no tiene storage local — quedó stateless |

Son 4, el mínimo que pide la consigna. El porqué de cada uno está en `docs/decisions.md`.

## Cómo correrlo

Hace falta Docker, Docker Compose y Python 3.11+ (y `pip install -r requirements.txt` antes de lo que sigue).

```bash
make up      # levanta LocalStack y crea toda la infraestructura
make test    # corre los tests
make down    # apaga LocalStack
```

Si no tenés `make` a mano (Windows sin WSL/Git Bash con make instalado), es lo mismo que corre el `Makefile` por dentro:

```bash
docker compose up -d
python scripts/iam_demo.py
python scripts/vpc_demo.py
python scripts/s3_demo.py
python scripts/ec2_demo.py
pytest -v
```

Los scripts se pueden correr más de una vez sin que rompan nada: antes de crear algo, primero se fijan si ya existe. Lo probé corriendo la secuencia completa dos veces contra LocalStack real.

Cada push corre los tests solo en GitHub Actions (`.github/workflows/ci.yml`) — no necesita Docker porque están mockeados con `moto`.

## Estructura del repo

```
.
├── README.md
├── Makefile                # up · test · down
├── compose.yaml            # LocalStack
├── requirements.txt
├── .github/workflows/ci.yml # corre los tests en cada push
├── docs/
│   ├── architecture.md     # componentes, puntos de falla, identidad
│   ├── architecture.drawio # diagrama editable (app.diagrams.net)
│   ├── decisions.md        # decisiones de diseño, formato ADR
│   ├── gantt.md             # cronograma de la migración
│   ├── gantt.png
│   ├── gantt.csv
│   └── costs.md            # estimación mensual
├── iam/
│   ├── trust_policy.json
│   ├── s3_access_policy.json
│   ├── bucket_policy.json
│   └── README.md
├── scripts/
│   ├── iam_demo.py
│   ├── s3_demo.py
│   ├── vpc_demo.py
│   ├── ec2_demo.py
│   └── README.md
└── tests/
    └── test_infra.py
```

## Sobre los costos

`docs/costs.md` tiene el desglose mensual y el link a la estimación cargada en calculator.aws. El dato interesante: el 80% del costo es transfer out a internet, no el storage — porque `app-01` todavía sirve las imágenes directo al navegador sin CDN. Si el tráfico creciera, ahí es donde convendría poner CloudFront antes que optimizar S3.

## Qué falta

Subir a mano los dos PNG (`docs/architecture.png` y `docs/gantt.png`) — son binarios y no entran bien por el flujo que vengo usando para pushear, así que quedan para arrastrar directo por la web de GitHub.

> Nota para Windows: si te tira `UnicodeEncodeError` corriendo los scripts, es la consola en codepage cp1252 que no banca las flechas (`→`) de los prints. Se soluciona corriendo con `PYTHONUTF8=1` antes (`set PYTHONUTF8=1` en cmd). En Linux o Mac no pasa, la consola ya es UTF-8.
