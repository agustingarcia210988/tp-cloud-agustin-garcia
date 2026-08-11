# Costos — PixelHub: Galería de imágenes → S3

Estimación mensual en **us-east-1**, para cargarla en el [AWS Pricing Calculator](https://calculator.aws). Los precios de esta tabla están verificados (ver fuentes al final); igual, **el número que vale para la entrega es el que arme la calculadora oficial** — esto es la base para no adivinar los supuestos al cargarla.

## Supuestos de uso (completar/ajustar con datos reales de PixelHub si los tienen)

- Catálogo histórico a migrar: ~50.000 imágenes, 2 MB promedio → **~100 GB** iniciales en S3 Standard.
- Crecimiento: ~5.000 imágenes nuevas/mes (2 MB c/u) → ~10 GB/mes nuevos, ~5.000 `PUT`/mes.
- Lecturas: ~2.000.000 `GET`/mes (vistas de producto que piden la imagen).
- `app-01` sirve las imágenes al navegador del cliente final (no hay CDN todavía) — tamaño servido promedio 300 KB → **~572 GB/mes de salida a internet**.
- `app-01`: 1x EC2 `t3.micro`, prendida 24/7 (730 h/mes).
- VPC Gateway Endpoint hacia S3 (tráfico interno, no cuenta como transfer out).

## Estimación mensual

| Concepto | Cálculo | Costo/mes |
|---|---|---|
| S3 Standard — storage | 110 GB × $0.023/GB | **$2.53** |
| S3 Standard — `PUT`/`POST` | 5.000 req × $0.005/1.000 | **$0.03** |
| S3 Standard — `GET` | 2.000.000 req × $0.0004/1.000 | **$0.80** |
| **Transfer out a internet** (lo no obvio) | (572 GB − 100 GB gratis) × $0.09/GB | **$42.48** |
| VPC Gateway Endpoint (S3) | gratis — sin cargo por hora ni por GB | **$0.00** |
| EC2 `t3.micro` (`app-01`) | 730 h × $0.0104/h | **$7.59** |
| IAM (rol, policies) | sin costo | **$0.00** |
| **Total mes 1 (antes de que el lifecycle archive nada)** | | **≈ $53.43** |

## Proyección a 6+ meses (con lifecycle activo)

Después de 90 días, las imágenes de `uploads/*` empiezan a pasar a Glacier. Si para ese momento ~40 GB del catálogo ya son "frías":

| Concepto | Cálculo | Costo/mes |
|---|---|---|
| S3 Standard — storage (resto activo) | ~90 GB × $0.023/GB | **$2.07** |
| S3 Glacier (Flexible Retrieval) | 40 GB × $0.0036/GB | **$0.14** |
| resto de líneas (igual que arriba) | | **$50.90** |
| **Total proyectado (steady state)** | | **≈ $53.11** |

El archivado a Glacier no mueve mucho la aguja acá porque **el 80% del costo mensual es transfer out a internet**, no storage — es justo el tipo de partida "no obvia" que la consigna pide sumar. Si el volumen de vistas creciera, la prioridad de optimización de costos sería poner un CDN (CloudFront) delante, no optimizar el storage.

## Qué NO está en esta estimación (para completar en el Pricing Calculator real)

- Costo de **CloudWatch** si se agrega monitoreo/alarmas sobre el bucket o la instancia.
- **Data transfer entre AZ** si `app-01` se escala a múltiples instancias en distintas AZ.
- Picos de tráfico estacionales de PixelHub (esto asume una carga plana todo el mes).
- Soporte de AWS (Developer/Business), si el grupo decide incluirlo.

## Link de la calculadora oficial

**[calculator.aws/#/estimate?id=a165ebb18479f4eac63a9ff1e9ff5b199a9f4d43](https://calculator.aws/#/estimate?id=a165ebb18479f4eac63a9ff1e9ff5b199a9f4d43)**

Cargada con los mismos supuestos de esta tabla (S3 Standard 110 GB, 5.000 PUT, 2.000.000 GET, 572 GB de data transfer out a Internet; EC2 `t3.micro` on-demand, 730 h/mes). **Total oficial: $62.42/mes** ($54.83 S3 + $7.59 EC2), contra los ≈$53.43 de la tabla de arriba.

La diferencia (~$9) es la partida "no obvia" real de este ejercicio: el Pricing Calculator dice explícitamente *"the calculations below exclude Free Tier discounts"* — cobra los 572 GB completos de transfer out al precio de $0.09/GB. La tabla de arriba, en cambio, restaba los 100 GB gratis del free tier de AWS antes de aplicar la tarifa (472 GB × $0.09 = $42.48). Los dos números son "correctos" según qué se les pide: la calculadora te da el peor caso (sin asumir free tier, que no está garantizado a largo plazo — es beneficio de cuenta nueva), y la tabla manual te da el estimado esperable con una cuenta ya establecida. **El número que vale para la entrega es el de la calculadora ($62.42/mes)**, por ser la fuente oficial pedida por la consigna.

## Fuentes (precios verificados, agosto 2026, us-east-1)

- S3 Standard storage y requests — [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- S3 Glacier Flexible/Instant Retrieval — [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- EC2 `t3.micro` on-demand — [AWS EC2 On-Demand Pricing](https://aws.amazon.com/ec2/pricing/on-demand/)
- Data transfer out a internet (100 GB gratis, luego $0.09/GB) — [AWS Data Transfer Pricing](https://aws.amazon.com/about-aws/whats-new/2021/11/aws-price-reduction-data-transfers-internet)
- VPC Gateway Endpoint sin costo — [Amazon VPC Pricing](https://aws.amazon.com/vpc/pricing/)
