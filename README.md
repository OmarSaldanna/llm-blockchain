# 🔗 Sistema de Procesamiento de Prompts LLM con Trazabilidad Blockchain

Este proyecto implementa una arquitectura híbrida que combina una **API REST**, un **Worker Asíncrono** y un **Ledger Inmutable (Blockchain Centralizada)** para gestionar, procesar y auditar peticiones a Modelos de Lenguaje Grande (LLM).

El sistema permite a los usuarios enviar prompts, descontar "créditos" (tokens) de su saldo, y garantiza que cada transacción y respuesta quede registrada en una cadena de bloques criptográficamente vinculada, asegurando la integridad histórica de los datos.

-----

## 🛡️ Justificación Técnica: Blockchain e Integridad de Datos

Este sistema trasciende una base de datos tradicional mediante la implementación de una **Blockchain Centralizada** (`blockchain.json`) para el registro de transacciones. A diferencia de un log convencional, esta estructura garantiza la **inmutabilidad** y la **coherencia temporal** de las interacciones usuario-sistema.

### ¿Cómo asegura este método las transacciones y prompts?

1.  **Inmutabilidad Criptográfica (SHA-256):**
    Cada lote de prompts procesados ("bloque") contiene un hash único calculado a partir de su contenido y, crucialmente, incluye el **`hash_anterior`** del bloque precedente.

      * *Mecanismo:* $Hash_{bloque} = SHA256(Datos + Timestamp + Hash_{anterior})$
      * *Seguridad:* Si un actor malintencionado intentara modificar un prompt o un saldo en un bloque pasado (ej. Bloque 5), el hash de ese bloque cambiaría. Como el Bloque 6 contiene el hash original del Bloque 5, la cadena se rompería, evidenciando inmediatamente la manipulación.

2.  **Línea de Tiempo Unificada (Timestamping):**
    La blockchain actúa como la "fuente de la verdad" cronológica. Al serializar las transacciones en bloques secuenciales, se crea una línea de tiempo canónica que impide la reordenación de eventos o la inserción de transacciones retroactivas ("double-spending" de tokens).

3.  **Auditabilidad y Cumplimiento (Compliance):**
    El sistema permite auditar el uso de la IA. Al registrar indeleblemente el `prompt` (entrada) y la `respuesta` (salida) junto con el costo en tokens, se asegura que los usuarios cumplan con las políticas de uso. Cualquier intento de negar haber enviado un prompt específico es refutado por la firma criptográfica del bloque correspondiente.

4.  **Consistencia de Saldos (State Integrity):**
    El saldo de tokens de los usuarios no es solo un número en una base de datos mutable, sino el resultado de la suma histórica de transacciones registradas en la blockchain. Esto previene errores de contabilidad y asegura que el consumo de recursos (API del LLM) esté perfectamente correlacionado con el gasto de los usuarios.

-----

## 📂 Arquitectura del Proyecto

### 1\. `api.py` (La Puerta de Enlace)

Servidor Flask que actúa como la interfaz pública del sistema.

  * **Función:** Autentica usuarios mediante API Keys, valida saldos y encola peticiones en PostgreSQL. No procesa la IA directamente, garantizando alta disponibilidad y baja latencia.

### 2\. `job.py` (El Minero y Worker)

El núcleo operativo del sistema. Ejecutado periódicamente (batch processing), realiza las siguientes tareas críticas:

1.  **Fetch:** Recupera prompts pendientes de la base de datos (FIFO).
2.  **Procesamiento:** Envía los prompts al modelo `gpt-5-nano` vía OpenAI.
3.  **Settlement:** Calcula el costo exacto (tokens in + tokens out) y actualiza el saldo del usuario (Atomic Transaction).
4.  **Mining:** Agrupa todas las transacciones exitosas, calcula el hash criptográfico vinculando el bloque anterior y escribe el nuevo bloque en `blockchain.json`.

### 3\. `modules.py` (Librería de Utilidades)

Contiene la lógica compartida y modularizada:

  * Conexión segura a PostgreSQL (`psycopg2`).
  * Integración con APIs de LLM (`get_openai_response`).
  * Funciones criptográficas para cálculo de SHA-256 (`calculate_hash`).
  * Gestión de lectura/escritura del Ledger (`blockchain.json`).

### 4\. `client.py` (Cliente de Usuario)

Interfaz de línea de comandos (CLI) para interactuar con el sistema. Permite a los usuarios enviar prompts y consultar su historial de transacciones de forma amigable.

-----

## 📡 Documentación de la API

### 1\. Enviar Prompt

Añade una solicitud a la cola de procesamiento.

  * **Endpoint:** `POST /submit`
  * **Body:**
    ```json
    {
      "api_key": "tu_api_key_sha256",
      "prompt": "Explica la teoría de la relatividad."
    }
    ```
  * **Respuesta (201 Created):**
    ```json
    {
      "message": "Prompt encolado exitosamente",
      "job_id": 42,
      "tokens_estimados": 15
    }
    ```

### 2\. Consultar Historial

Obtiene las últimas transacciones procesadas y registradas en la blockchain para un usuario.

  * **Endpoint:** `GET /history`
  * **Parámetros:** `?api_key=...&n=5` (donde `n` es el número de registros).
  * **Respuesta (200 OK):**
    ```json
    {
      "history": [
        {
          "prompt": "...",
          "respuesta": "...",
          "costo_tokens": 150,
          "fecha": "2023-10-27 10:00:00"
        }
      ]
    }
    ```

-----

## 🗄️ Estructura de Base de Datos

El sistema utiliza PostgreSQL para la persistencia de estado volátil (cola) y gestión de identidad.

### Tabla: `usuarios`

Gestiona identidades y saldos. Las API Keys se generan y almacenan como hashes.

| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | Identificador único. |
| `nombre` | VARCHAR | Nombre del usuario. |
| `api_key` | VARCHAR(64) | Hash SHA-256 de la llave de acceso. |
| `balance_tokens` | INT | Saldo actual de créditos. |

### Tabla: `fila_llm`

Actúa como *Mempool* (piscina de memoria) para transacciones pendientes antes de ser minadas.

| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | SERIAL (PK) | Identificador del trabajo. |
| `usuario_id` | INT (FK) | Referencia al usuario. |
| `prompt` | TEXT | Entrada de texto. |
| `estatus` | VARCHAR | `pendiente`, `listo`, `error`. |
| `tokens_totales` | INT | Costo final de la operación. |

-----

## 🧱 Estructura del Blockchain (`blockchain.json`)

El "libro mayor" del sistema sigue esta estructura JSON estricta:

```json
{
  "blockchain": [
    {
      "hash": "0000... (Hash del bloque actual)",
      "hash_anterior": "abcd... (Vínculo criptográfico)",
      "timestamp": "2023-10-27 12:00:00",
      "prompts": [
        {
          "usuario": 1,
          "prompt": "Prompt del usuario...",
          "respuesta": "Respuesta de la IA...",
          "tokens_gastados": 120,
          "balance_restante": 9880
        }
      ]
    }
  ]
}
```

-----

## 🛠️ Instalación

1.  **Clonar repositorio y crear entorno virtual:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configurar `.env`:**

    ```env
    DB_NAME=...
    OPENAI_API_KEY=sk-...
    ```

3.  **Ejecución:**

      * API: `python api.py`
      * Worker (Minado): `python job.py`
      * Cliente: `python client.py`