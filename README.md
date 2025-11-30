# ⚙️ LLM Prompt Processing Queue

Este proyecto implementa un sistema de cola (queue) para procesar prompts de manera asíncrona utilizando un modelo de lenguaje grande (LLM) auto-alojado y una base de datos PostgreSQL.

El sistema está diseñado para ejecutarse en un servidor durante la noche, procesando una lista de trabajos pendientes uno por uno, registrando los resultados, el uso de tokens y el tiempo de ejecución.

---

## 🚀 ¿Cómo Funciona?

El flujo de trabajo es sencillo pero robusto:

1.  **Agendar un Trabajo**: Un usuario o sistema externo inserta un nuevo registro en la tabla `fila_llm_anahuac` en la base de datos PostgreSQL. Solo necesita proporcionar el `prompt`; el `estatus` se establece por defecto en `'pendiente'`.

2.  **Ejecución Programada**: Un `cron job` en el servidor activa el script principal `queue.sh` a una hora predefinida (ej. 1:00 AM cada día).

3.  **Bucle de Procesamiento**: El script `queue.sh` inicia un bucle que ejecuta `job.py` repetidamente. Este bucle tiene dos condiciones de parada:
    * La hora actual alcanza las 6:00 AM.
    * El script `job.py` crea un archivo temporal `empty_queue.tmp`, indicando que ya no hay más prompts pendientes.

4.  **Procesamiento del Prompt**: En cada ejecución, `job.py` realiza las siguientes acciones:
    * Se conecta a la base de datos y selecciona el prompt pendiente más antiguo.
    * Envía el prompt a la API del LLM.
    * Mide el tiempo de respuesta.
    * Al recibir la respuesta, cuenta los tokens de entrada (`prompt`) y de salida (`respuesta`) utilizando `tiktoken`.
    * Actualiza el registro en la base de datos con la respuesta, los conteos de tokens, el tiempo de ejecución y cambia el `estatus` a `'listo'`.
    * Si ocurre un error, actualiza el `estatus` a `'error'`.

5.  **Limpieza**: Una vez que el bucle en `queue.sh` termina, elimina el archivo `empty_queue.tmp` para asegurar que la ejecución del día siguiente comience correctamente.

---

## 📂 Estructura del Proyecto

```
/tu_proyecto/
├── venv/                 # Entorno virtual de Python
├── .env                  # Archivo de configuración con credenciales (¡NO subir a Git!)
├── .gitignore            # Archivos y carpetas a ignorar por Git
├── modules.py            # Funciones auxiliares (conexión a DB, llamada al LLM, etc.)
├── job.py                # Script principal para procesar UN solo prompt
├── queue.sh              # Script de shell que ejecuta job.py en bucle
└── queue.log             # (Opcional) Archivo de logs generado por cron
```

---

## 🗄️ Esquema de la Base de Datos

La tabla en PostgreSQL que gestiona la cola tiene la siguiente estructura:

```sql
CREATE TABLE fila_llm_anahuac (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    respuesta TEXT,
    fecha_in TIMESTAMP DEFAULT NOW(),
    fecha_out TIMESTAMP,
    tokens_in INT,
    tokens_out INT,
    estatus VARCHAR(10) NOT NULL DEFAULT 'pendiente' CHECK (estatus IN ('pendiente', 'listo', 'error')),
    tiempo_ejecucion NUMERIC(10, 2)
);
```

---

## 🛠️ Instalación y Configuración

Sigue estos pasos para poner en marcha el sistema:

1.  **Clonar el repositorio** (si aplica) o crear los archivos en tu servidor.

2.  **Crear el Entorno Virtual**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar Dependencias**:
    ```bash
    pip install psycopg2-binary requests python-dotenv tiktoken
    ```

4.  **Configurar Variables de Entorno**:
    * Crea un archivo llamado `.env` a partir del archivo `.env.example` o desde cero.
    * Rellena las credenciales de la base de datos y la configuración de la API del LLM.

5.  **Dar Permisos de Ejecución**:
    Asegúrate de que el script de shell sea ejecutable:
    ```bash
    chmod +x queue.sh
    ```

6.  **Configurar el Cron Job**:
    * Abre el editor de crontab: `crontab -e`
    * Añade la siguiente línea, **ajustando las rutas** a las de tu proyecto:
    ```crontab
    0 1 * * * /ruta/completa/a/tu_proyecto/queue.sh >> /ruta/completa/a/tu_proyecto/queue.log 2>&1
    ```

---

## ▶️ Uso

Para usar el sistema, simplemente inserta un nuevo registro en tu base de datos:

```sql
INSERT INTO fila_llm_anahuac (prompt) VALUES ('Escribe un poema corto sobre la programación.');
```

El sistema recogerá y procesará este prompt automáticamente durante el próximo ciclo de ejecución programado.

## 🔑 Archivo .env

```bash
# --- Configuración de la Base de Datos PostgreSQL ---
DB_NAME="timeline"
DB_USER="tu_usuario_de_db"
DB_PASSWORD="tu_contraseña_de_db"
DB_HOST="ip_o_host_de_la_db"
DB_PORT="5432"

# --- Configuración de la API del LLM ---
LLM_API_URL="http: ...."
LLM_API_KEY="tu_api_key_secreta"
```