# Data Model - AnalyticLab

## Introducción

Este documento define la estructura de datos utilizada por AnalyticLab.

El modelo inicial está diseñado para recopilar y analizar información procedente de plataformas digitales, comenzando con Instagram como primera fuente experimental.

El modelo evolucionará progresivamente según aumenten las necesidades del sistema.

---

# Entidades principales

Actualmente AnalyticLab trabaja con las siguientes entidades:
Cuenta
|
↓
Publicación
|
↓
Métricas
|
↓
Análisis

---

# Cuenta

Representa un perfil dentro de una plataforma digital.

## Campos iniciales

| Campo | Descripción |
|---|---|
| id_cuenta | Identificador único |
| plataforma | Red social utilizada |
| nombre_usuario | Usuario de la cuenta |
| fecha_registro | Fecha de incorporación al sistema |
| seguidores | Número de seguidores actuales |

---

# Publicación

Representa una pieza de contenido publicada.

## Campos iniciales

| Campo | Descripción |
|---|---|
| id_publicacion | Identificador único |
| id_cuenta | Cuenta asociada |
| fecha_publicacion | Momento de publicación |
| tipo_contenido | Foto, vídeo, carrusel, reel |
| descripcion | Texto asociado |
| hashtags | Etiquetas utilizadas |

---

# Métricas de publicación

Representan el rendimiento obtenido por una publicación.

## Campos iniciales

| Campo | Descripción |
|---|---|
| alcance | Usuarios alcanzados |
| impresiones | Número de visualizaciones |
| me_gusta | Número de likes |
| comentarios | Interacciones recibidas |
| guardados | Veces guardada |
| compartidos | Veces compartida |
| reproducciones | Visualizaciones de vídeo |

---

# Datos temporales

AnalyticLab debe conservar evolución histórica.

Ejemplo:
Publicación creada
|
↓
Recopilación inicial
|
↓
Actualización de métricas
|
↓
Comparación temporal

Esto permite estudiar:

- Crecimiento.
- Velocidad de interacción.
- Cambios de comportamiento.
- Evolución del contenido.

---

# Métricas calculadas

Además de los datos originales, AnalyticLab podrá generar métricas propias.

Ejemplos:

## Engagement rate

Mide la interacción relativa respecto al alcance.
(interacciones / alcance) × 100

---

## Tasa de conversión

Permite estudiar cómo las visualizaciones generan acciones.

Ejemplos:

- Visualización → Seguimiento.
- Alcance → Interacción.

---

## Rendimiento del contenido

Permite comparar publicaciones según diferentes variables:

- Formato.
- Fecha.
- Tema.
- Duración.
- Audiencia.

---

# Datos futuros

Posibles ampliaciones:

## Usuario del sistema

Cuando AnalyticLab soporte usuarios externos:

- id_usuario.
- permisos.
- preferencias.
- cuentas conectadas.

---

## Experimentos

Para registrar pruebas:

- Hipótesis.
- Cambio aplicado.
- Resultado.
- Conclusión.

---

## Recomendaciones

Información generada por el sistema:

- Sugerencias.
- Patrones detectados.
- Predicciones futuras.

---

# Principios del modelo de datos

## Calidad de datos

Los datos deben ser:

- Correctos.
- Consistentes.
- Trazables.

## Privacidad

La información sensible debe protegerse adecuadamente.

## Historial

Los cambios importantes deben conservarse para análisis posteriores.

## Escalabilidad

El modelo debe permitir añadir nuevas plataformas y fuentes de información.

---

# Estado actual

Actualmente:

✅ Primera fuente de datos: Instagram.  
✅ Recopilación inicial de métricas realizada.  
✅ Modelo conceptual definido.  

Pendiente:

- Definir almacenamiento definitivo.
- Crear esquema de base de datos.
- Automatizar actualización de registros.