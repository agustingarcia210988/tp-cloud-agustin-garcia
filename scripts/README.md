# `scripts/` — demos automatizados de PixelHub

Orden de ejecución (cada uno depende de que exista lo del anterior, pero
todos son tolerantes si falta algo — avisan en vez de crashear):

```bash
python scripts/iam_demo.py   # 1. rol + policy + instance profile
python scripts/vpc_demo.py   # 2. VPC + 2 subredes (multi-AZ) + route table + gateway endpoint
python scripts/s3_demo.py    # 3. bucket + versioning + lifecycle + bucket policy
python scripts/ec2_demo.py   # 4. instancia app-01 con el instance profile
```

## Convenciones

- **Idempotentes** — se pueden correr dos veces sin romper (patrón: `get_*`/`head_*` primero, crear sólo si falta).
- **Sin secretos hardcodeados** — `_aws.py` lee endpoint y credenciales del entorno (`.env`), con defaults de LocalStack.
- **Auto-documentados** — cada script imprime qué encontró, qué creó y con qué ARN/ID quedó.
- **Estado compartido** — `vpc_demo.py` guarda IDs (VPC, subred, endpoint) en `.local/vpc_output.json` para que `s3_demo.py` y `ec2_demo.py` los reutilicen. Esa carpeta no se commitea.

## `_aws.py`

Helper compartido: `client(service)` y `resource(service)` devuelven clientes boto3 apuntando a `AWS_ENDPOINT_URL` (default `http://localhost:4566`, LocalStack). Contra AWS real, sólo hay que cambiar esa variable de entorno (o no setearla) y usar credenciales reales — el resto del código no cambia.
