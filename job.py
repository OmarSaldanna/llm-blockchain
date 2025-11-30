import time
from datetime import datetime
from modules import (
    get_db_connection, get_llm_response, count_tokens, 
    load_blockchain, save_blockchain, calculate_hash, Colors
)

def run_batch_process():
    print(f"{Colors.BLUE}=== Iniciando Batch de Procesamiento y Minado ==={Colors.END}")
    
    conn = get_db_connection()
    if not conn: return

    cursor = conn.cursor()
    
    # Lista para guardar las transacciones exitosas de este bloque
    transacciones_bloque = []

    try:
        # 1. Obtener TODOS los pendientes (Batch processing)
        cursor.execute("""
            SELECT f.id, f.usuario_id, f.prompt, f.tokens_in 
            FROM fila_llm f
            WHERE f.estatus = 'pendiente'
            ORDER BY f.fecha_in ASC
            FOR UPDATE SKIP LOCKED; 
        """)
        
        jobs = cursor.fetchall()
        
        if not jobs:
            print("No hay trabajos pendientes.")
            return

        print(f"Se encontraron {len(jobs)} trabajos pendientes.")

        # 2. Iterar y procesar
        for job in jobs:
            job_id, user_id, prompt_text, tokens_in_estimados = job
            print(f"\nProcesando Job {job_id} (Usuario {user_id})...")

            # A. Llamar al LLM
            start_t = time.time()
            respuesta = get_llm_response(prompt_text)
            tiempo = round(time.time() - start_t, 2)

            if respuesta:
                tokens_out = count_tokens(respuesta)
                # Recalcular tokens_in exactos por si acaso
                tokens_in_real = count_tokens(prompt_text) 
                total_cost = tokens_in_real + tokens_out

                # B. Descontar Balance (Transacción Crítica)
                try:
                    # Intentamos restar. Si el balance baja de 0, fallará por el CHECK constraint de SQL
                    cursor.execute("""
                        UPDATE usuarios 
                        SET balance_tokens = balance_tokens - %s 
                        WHERE id = %s 
                        RETURNING balance_tokens
                    """, (total_cost, user_id))
                    
                    nuevo_balance = cursor.fetchone()[0]

                    # C. Actualizar Fila
                    cursor.execute("""
                        UPDATE fila_llm
                        SET respuesta = %s, fecha_out = NOW(), 
                            tokens_in = %s, tokens_out = %s, 
                            estatus = 'listo', tiempo_ejecucion = %s
                        WHERE id = %s
                    """, (respuesta, tokens_in_real, tokens_out, tiempo, job_id))

                    # D. Agregar a la lista para el bloque
                    transacciones_bloque.append({
                        "usuario": user_id,
                        "prompt": prompt_text,
                        "respuesta": respuesta[:50] + "...", # Truncamos para no llenar el JSON
                        "tokens_gastados": total_cost,
                        "balance_restante": nuevo_balance,
                        "job_id": job_id
                    })
                    
                    print(f"{Colors.GREEN}Éxito. Costo: {total_cost}. Nuevo Balance: {nuevo_balance}{Colors.END}")

                except psycopg2.IntegrityError:
                    # El usuario se quedó sin saldo durante el proceso
                    conn.rollback() # Revertimos el intento de resta
                    print(f"{Colors.RED}Error: Usuario {user_id} sin saldo suficiente.{Colors.END}")
                    
                    # Marcamos como error en la fila (necesitamos un nuevo cursor/transacción limpia)
                    # En este script simple, saltamos al siguiente.
                    # Nota: En producción, deberías manejar esto en una conexión aparte para marcar el error.
                    continue
            else:
                print(f"{Colors.RED}Fallo en LLM para Job {job_id}{Colors.END}")
                cursor.execute("UPDATE fila_llm SET estatus='error' WHERE id=%s", (job_id,))

        # Confirmar cambios en DB
        conn.commit()

        # 3. Minar el Bloque (Si hubo transacciones exitosas)
        if transacciones_bloque:
            print(f"\n{Colors.YELLOW}Minando nuevo bloque con {len(transacciones_bloque)} transacciones...{Colors.END}")
            
            chain_data = load_blockchain()
            last_block = chain_data['blockchain'][-1]
            last_hash = last_block['hash']

            new_block = {
                "hash_anterior": last_hash,
                "timestamp": str(datetime.now()),
                "prompts": transacciones_bloque,
                # El hash se calcula sobre el contenido (sin incluir la clave 'hash' obviamente)
            }
            
            # Calcular Hash del bloque actual
            block_hash = calculate_hash(new_block)
            new_block["hash"] = block_hash

            # Agregar a la cadena
            chain_data['blockchain'].append(new_block)
            save_blockchain(chain_data)
            
            print(f"{Colors.CYAN}Bloque minado: {block_hash}{Colors.END}")
        
    except Exception as e:
        print(f"Error fatal en job: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_batch_process()