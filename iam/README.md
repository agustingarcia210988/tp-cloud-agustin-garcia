# `iam/` — políticas y trust documents de PixelHub

| Archivo | Tipo | Qué hace |
|---|---|---|
| `trust_policy.json` | Trust policy | Permite que `ec2.amazonaws.com` asuma el rol `pixelhub-app-role` (instance profile de `app-01`) |
| `s3_access_policy.json` | Identity policy | Privilegio mínimo: el rol sólo puede `GetObject`/`PutObject` bajo `uploads/*` en el bucket `pixelhub-images`, `ListBucket` acotado al mismo prefijo, y tiene **deny explícito** de `DeleteObject` (el borrado de imágenes no es una operación de la app — lo maneja el lifecycle a Glacier) |
| `bucket_policy.json` | Resource policy | Autoriza al rol de la app, **deniega cualquier acceso que no venga del VPC Gateway Endpoint** (`aws:sourceVpce`) y **deniega tráfico sin TLS** (`aws:SecureTransport`) |

## Nota sobre `vpce-REPLACE_WITH_REAL_ENDPOINT_ID`

El ID del VPC endpoint no se conoce hasta crearlo (lo genera `scripts/vpc_demo.py`). En un entorno real, este placeholder se reemplaza por el `VpcEndpointId` real antes de aplicar la bucket policy — `scripts/s3_demo.py` lo hace automáticamente leyendo el output de `vpc_demo.py`. LocalStack Community no aplica evaluación completa de condition keys como `aws:sourceVpce`, así que el efecto sólo se puede validar 1:1 contra AWS real o LocalStack Pro; para este proyecto la política se sube igual como evidencia del diseño (deny-by-default fuera del endpoint es el patrón correcto en producción).

## Decisiones de identidad (resumen — ver `docs/architecture.md` y `docs/decisions.md`)

- Los servicios se autentican con **roles asumidos**, no con access keys estáticas.
- El acceso está acotado por **prefijo** (`uploads/*`), no a todo el bucket.
- El acceso está acotado por **origen de red** (VPC endpoint), no por internet.
- Las credenciales del rol son temporales (STS) y se renuevan automáticamente cada pocas horas.
