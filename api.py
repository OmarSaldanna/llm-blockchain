from flask import Flask, request, jsonify
from modules import get_db_connection, count_tokens

app = Flask(__name__)

@app.route('/submit', methods=['POST'])
def submit_prompt():
    """Recibe: { "api_key": "...", "prompt": "..." }"""
    data = request.json
    api_key = data.get('api_key')
    prompt = data.get('prompt')

    if not api_key or not prompt:
        return jsonify({"error": "Faltan datos"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Validar Usuario
        cur.execute("SELECT id, balance_tokens FROM usuarios WHERE api_key = %s", (api_key,))
        user = cur.fetchone()

        if not user:
            return jsonify({"error": "API Key inválida"}), 401

        user_id, balance = user
        
        # 2. Validar Balance inicial (aprox)
        tokens_in = count_tokens(prompt)
        if balance < tokens_in:
             return jsonify({"error": "Saldo insuficiente para iniciar"}), 402

        # 3. Insertar en la cola
        cur.execute("""
            INSERT INTO fila_llm (usuario_id, prompt, tokens_in, estatus)
            VALUES (%s, %s, %s, 'pendiente')
            RETURNING id
        """, (user_id, prompt, tokens_in))
        
        job_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({
            "message": "Prompt encolado exitosamente",
            "job_id": job_id,
            "tokens_estimados": tokens_in
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/history', methods=['GET'])
def get_history():
    """Params: ?api_key=...&n=5"""
    api_key = request.args.get('api_key')
    n = request.args.get('n', default=5, type=int)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Validar y obtener ID
        cur.execute("SELECT id FROM usuarios WHERE api_key = %s", (api_key,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({"error": "API Key inválida"}), 401
        
        user_id = user[0]

        # Obtener últimos N prompts listos
        cur.execute("""
            SELECT prompt, respuesta, tokens_totales, fecha_out 
            FROM fila_llm 
            WHERE usuario_id = %s AND estatus = 'listo'
            ORDER BY fecha_out DESC 
            LIMIT %s
        """, (user_id, n))
        
        rows = cur.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "prompt": row[0],
                "respuesta": row[1],
                "costo_tokens": row[2],
                "fecha": row[3]
            })

        return jsonify({"history": history})

    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    # Ejecutar en puerto 5000
    app.run(debug=True, host='0.0.0.0', port=5001)