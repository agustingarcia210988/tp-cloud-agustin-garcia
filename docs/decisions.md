# Decision log — PixelHub

Registro de decisiones de arquitectura del proyecto (formato ADR).

---

### 001 — Alcance: un componente (storage), no la migración completa

**Decision:** migrar únicamente el storage de imágenes de `app-01` a S3; el cómputo (EC2) y el resto de la app quedan como están.

**Contexto:** la consigna permite elegir entre migración completa o un componente acotado. Con 4 personas y el tiempo del módulo, priorizamos poder justificar cada elección en profundidad antes que cubrir más superficie a medias.

**Alternativas:** migración completa (web + backend + base de datos + archivos) a una arquitectura de 3 capas.

**Tradeoff:** cubrimos menos "amplitud" de la arquitectura de PixelHub, pero el storage queda resuelto con seguridad, costos y plan de corte reales — no un boceto.

**Resultado:** 4 servicios de la cursada implementados end-to-end en LocalStack: S3, IAM, VPC (Gateway Endpoint), EC2.

---

### 002 — Identidad: IAM Role + instance profile, no un IAM user con access keys

**Decision:** `app-01` se autentica contra S3 con un rol IAM asumido automáticamente vía instance profile, no con un usuario IAM y sus access keys.

**Contexto:** el código actual de PixelHub no tiene credenciales de AWS (corre on-prem). Al moverlo a EC2, la forma más simple sería poner un access key/secret en una variable de entorno — pero es una credencial de larga duración que alguien puede filtrar, loguear por accidente o olvidarse de rotar.

**Alternativas:** IAM user con access key en variable de entorno o en Secrets Manager.

**Tradeoff:** el rol sólo funciona porque el recurso es un EC2 (o cualquier servicio que soporte roles); no serviría, por ejemplo, para un script corriendo en la laptop de un desarrollador. Para ese caso seguiría haciendo falta un usuario o SSO — pero no es el caso de `app-01`.

**Resultado:** `iam/trust_policy.json` (sólo `ec2.amazonaws.com` puede asumir el rol) + `pixelhub-app-instance-profile`.

---

### 003 — Red: VPC Gateway Endpoint hacia S3, no NAT Gateway

**Decision:** `app-01` llega a S3 por un VPC Gateway Endpoint, no por un NAT Gateway ni saliendo por una IP pública.

**Contexto:** `app-01` vive en una subred privada y necesita hablar con S3 sin exponerse a internet.

**Alternativas:** NAT Gateway (con costo por hora + por GB procesado) o darle IP pública a la instancia.

**Tradeoff:** el Gateway Endpoint es gratis y mantiene el tráfico dentro del backbone de AWS (más seguro y más rápido), pero sólo sirve para S3 y DynamoDB. Si mañana `app-01` necesita llamar a otro servicio AWS por su API pública, de todas formas va a hacer falta un NAT Gateway o un Interface Endpoint para ese servicio puntual.

**Resultado:** `scripts/vpc_demo.py` crea el endpoint y lo asocia a la route table de la subred de `app-01`.

---

### 004 — Acceso: bucket privado, restringido por origen de red, no bucket público

**Decision:** el bucket `pixelhub-images` es privado; sólo se puede acceder desde el rol de la app y únicamente si la request viene del VPC endpoint (`aws:sourceVpce`) y por TLS (`aws:SecureTransport`).

**Contexto:** las imágenes pertenecen a clientes de PixelHub — no hay motivo de negocio para exponerlas públicamente como sí lo haría, por ejemplo, un sitio de assets estáticos con CDN.

**Alternativas:** bucket público de sólo lectura + CloudFront como CDN delante, para servir las imágenes directo al navegador del usuario final sin pasar por `app-01`.

**Tradeoff:** sin CDN, servir imágenes al usuario final implica que pasan por `app-01` (más carga en la instancia, más lento que un edge de CloudFront). Priorizamos seguridad y simplicidad para el alcance de este componente; CloudFront + bucket público (o firmado) queda como mejora natural del siguiente sprint.

**Resultado:** `iam/bucket_policy.json` con deny explícito fuera del VPC endpoint y sin TLS.

---

### 005 — Ciclo de vida: lifecycle a Glacier a los 90 días, no borrar ni dejar todo en Standard

**Decision:** las imágenes bajo `uploads/*` pasan a S3 Glacier (Flexible Retrieval) a los 90 días de antigüedad (30 días para versiones no vigentes).

**Contexto:** el patrón de acceso típico de una imagen de producto es: mucha consulta las primeras semanas, casi ninguna después.

**Alternativas:** (a) mantener todo en S3 Standard indefinidamente, (b) borrar directamente las imágenes viejas.

**Tradeoff:** Glacier Flexible Retrieval cuesta ~6x menos por GB que Standard, pero recuperar un objeto archivado tarda de minutos a horas (no es instantáneo como Glacier Instant Retrieval, que es más caro). Para imágenes de catálogo viejas, ese tiempo de espera es aceptable; para un caso con acceso impredecible a datos "fríos" convendría Instant Retrieval en vez de Flexible.

**Resultado:** lifecycle rule en `scripts/s3_demo.py`, sin borrar nada — sólo cambia de clase de storage.

---

### 006 — Migración: dual-write + corte, no un solo salto ("big bang")

**Decision:** durante la migración, `app-01` escribe imágenes nuevas tanto al disco local como a S3 en paralelo (dual-write) antes de cortar la lectura hacia S3.

**Contexto:** un corte directo (apagar el disco, prender S3) es riesgoso: si algo falla el día del corte, no hay forma rápida de volver atrás sin perder las imágenes subidas en el medio.

**Alternativas:** migración "big bang" — copiar todo el histórico una vez y cambiar el flag de lectura/escritura el mismo día, sin período de convivencia.

**Tradeoff:** el dual-write agrega complejidad transitoria al código de la app (dos escrituras en vez de una, verificación de integridad con checksums) y duplica el storage por unas semanas, pero da una ventana segura para validar S3 con tráfico real antes de depender de él, y una forma barata de volver atrás si algo no cierra.

**Resultado:** ver `docs/gantt.md` — la fase de "prueba" del cronograma es exactamente esta convivencia antes del corte.
