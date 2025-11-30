import requests
import json
import sys

# --- CONFIGURACIÓN DEL USUARIO ---
# 1. Pega aquí la API Key que generaste en tu base de datos (tabla usuarios)
MI_API_KEY = "6da6d48703a3c11e05e265facd6bc9e551a4e03494a269a7eb99b9c4b35a9dcb"

# 2. La URL donde está corriendo tu api.py (por defecto localhost:5000)
BASE_URL = "http://127.0.0.1:5001"

# --- Colores para la consola ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def enviar_prompt():
    print(f"\n{Colors.HEADER}--- ENVIAR NUEVO PROMPT ---{Colors.END}")
    prompt_text = input(f"{Colors.BLUE}Escribe tu prompt: {Colors.END}")
    
    if not prompt_text.strip():
        print(f"{Colors.WARNING}El prompt no puede estar vacío.{Colors.END}")
        return

    payload = {
        "api_key": MI_API_KEY,
        "prompt": prompt_text
    }

    try:
        response = requests.post(f"{BASE_URL}/submit", json=payload)
        
        if response.status_code == 201:
            data = response.json()
            print(f"\n{Colors.GREEN}✔ ¡Éxito! Prompt encolado.{Colors.END}")
            print(f"   ID del Job: {Colors.BOLD}{data['job_id']}{Colors.END}")
            print(f"   Tokens estimados (costo entrada): {data['tokens_estimados']}")
        else:
            print(f"\n{Colors.FAIL}✘ Error {response.status_code}:{Colors.END}")
            print(json.dumps(response.json(), indent=2))
            
    except requests.exceptions.ConnectionError:
        print(f"\n{Colors.FAIL}Error: No se pudo conectar con el servidor. ¿Está corriendo api.py?{Colors.END}")

def ver_historial():
    print(f"\n{Colors.HEADER}--- VER HISTORIAL DE RESPUESTAS ---{Colors.END}")
    try:
        n_input = input(f"{Colors.BLUE}¿Cuántos registros quieres ver? (Enter para 5): {Colors.END}")
        n = int(n_input) if n_input.strip() else 5
    except ValueError:
        print("Valor inválido, usando 5 por defecto.")
        n = 5

    params = {
        "api_key": MI_API_KEY,
        "n": n
    }

    try:
        response = requests.get(f"{BASE_URL}/history", params=params)
        
        if response.status_code == 200:
            data = response.json()
            history = data.get("history", [])
            
            if not history:
                print(f"\n{Colors.WARNING}No tienes prompts 'listos' todavía o tu historial está vacío.{Colors.END}")
            else:
                print(f"\n{Colors.GREEN}Mostrando los últimos {len(history)} resultados:{Colors.END}\n")
                for i, item in enumerate(history, 1):
                    print(f"{Colors.BOLD}#{i} - {item['fecha']}{Colors.END}")
                    print(f"   {Colors.BLUE}Prompt:{Colors.END} {item['prompt']}")
                    print(f"   {Colors.GREEN}Respuesta:{Colors.END} {item['respuesta'][:100]}...") # Muestra solo los primeros 100 chars
                    print(f"   {Colors.WARNING}Costo Total:{Colors.END} {item['costo_tokens']} tokens")
                    print("-" * 40)
        else:
            print(f"\n{Colors.FAIL}✘ Error {response.status_code}:{Colors.END}")
            print(json.dumps(response.json(), indent=2))

    except requests.exceptions.ConnectionError:
        print(f"\n{Colors.FAIL}Error: No se pudo conectar con el servidor.{Colors.END}")

def menu():
    while True:
        print(f"\n{Colors.BOLD}=== CLIENTE BLOCKCHAIN LLM ==={Colors.END}")
        print("1. 📝 Enviar Prompt (POST)")
        print("2. 📜 Ver Historial (GET)")
        print("3. 🚪 Salir")
        
        opcion = input(f"\n{Colors.BLUE}Selecciona una opción: {Colors.END}")

        if opcion == "1":
            enviar_prompt()
        elif opcion == "2":
            ver_historial()
        elif opcion == "3":
            print("¡Hasta luego!")
            sys.exit()
        else:
            print("Opción no válida.")

if __name__ == "__main__":
    # Verificación rápida de seguridad
    if "tu_api_key" in MI_API_KEY:
        print(f"{Colors.WARNING}¡OJO! No has configurado tu API KEY en el script client.py.{Colors.END}")
        print("Edita el archivo y pon la key generada en la base de datos.")
    
    menu()