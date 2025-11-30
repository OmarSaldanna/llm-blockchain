import psycopg2
import requests
import tiktoken
import os
import json
import hashlib
import urllib3
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

load_dotenv()

# --- Base de Datos ---
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.Error as e:
        print(f"{Colors.RED}Error DB: {e}{Colors.END}")
        return None

# --- LLM ---
def get_llm_response(prompt):
    url = os.getenv("LLM_API_URL")
    api_key = os.getenv("LLM_API_KEY")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    # Prompt de sistema simple
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.5
    }

    try:
        # Ajusta la estructura según tu proveedor de LLM (ej. OpenAI, LocalAI, etc)
        # Aquí asumo una estructura tipo OpenAI Chat Completion
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=600)
        response.raise_for_status()
        json_resp = response.json()
        
        # Intenta obtener contenido de diferentes estructuras comunes
        if 'choices' in json_resp:
            return json_resp['choices'][0]['message']['content']
        elif 'content' in json_resp:
            return json_resp['content']
        return str(json_resp)
        
    except Exception as e:
        print(f"{Colors.RED}Error LLM: {e}{Colors.END}")
        return None

# --- Utilidades ---
def count_tokens(text):
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except:
        return 0

# --- Blockchain Utils ---
BLOCKCHAIN_FILE = 'blockchain.json'

def load_blockchain():
    """Carga la blockchain, o crea una nueva si no existe."""
    if not os.path.exists(BLOCKCHAIN_FILE):
        # Bloque Génesis
        genesis = {
            "blockchain": [{
                "hash_anterior": "0",
                "prompts": [],
                "timestamp": str(datetime.now()),
                "hash": "0000000000000000000000000000000000000000000000000000000000000000"
            }]
        }
        save_blockchain(genesis)
        return genesis
    
    with open(BLOCKCHAIN_FILE, 'r') as f:
        return json.load(f)

def save_blockchain(chain_data):
    with open(BLOCKCHAIN_FILE, 'w') as f:
        json.dump(chain_data, f, indent=4)

def calculate_hash(block_data):
    """Calcula el SHA256 de un bloque (diccionario)."""
    block_string = json.dumps(block_data, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()


def get_openai_response(prompt):
    """
    Envía un prompt a la API de OpenAI usando el modelo especificado (gpt-5-nano).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(f"{Colors.RED}Error: OPENAI_API_KEY no encontrada en variables de entorno.{Colors.END}")
        return None

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "You are a helpful and concise assistant."},
                {"role": "user", "content": prompt}
            ],
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"{Colors.RED}Error al conectar con OpenAI: {e}{Colors.END}")
        return None
