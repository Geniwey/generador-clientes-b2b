import os
import requests
from supabase import create_client, Client

url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
groq_key = os.environ.get("GROQ_KEY")

supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

def generar_correo_ia(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    
    prompt_sistema = """Eres el Director de Ventas de LogiQuote, un software SaaS B2B para agentes de aduanas y transitarios que automatiza el cálculo de fletes y recargos.
    Tu objetivo es escribir un "Cold Email" (correo frío) hiper-personalizado a un posible cliente.
    Reglas:
    1. Tono: Directo, profesional pero cercano.
    2. Longitud: Corto (máximo 4 párrafos cortos).
    3. Personalización: Usa el [Contexto Web] proporcionado para mencionar algo específico a lo que se dedican.
    4. Cierre: Una pregunta sencilla que invite a responder."""
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Escribe un correo de ventas para la empresa '{empresa}' basándote en este contexto de su web: '{contexto}'"}
        ],
        "temperature": 0.7
    }

    try:
        res = requests.post(url, headers=headers, json=data)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error con la IA: {e} - Respuesta: {res.text if 'res' in locals() else 'N/A'}"

print("🤖 Conectando a Supabase para leer 3 clientes reales...")
try:
    # Busca 3 clientes que tengan contexto extraído de la web
    respuesta = supabase.table("prospectos").select("empresa, contexto_empresa").neq("contexto_empresa", "Sin información").limit(3).execute()
    clientes = respuesta.data
    
    if not clientes:
        print("⚠️ No hay clientes con contexto en la base de datos para hacer la prueba.")
    
    for c in clientes:
        print(f"\n--- Generando correo para {c['empresa']} ---")
        correo = generar_correo_ia(c['empresa'], c['contexto_empresa'])
        print("="*60)
        print(f"📩 DESTINATARIO: {c['empresa']}")
        print("="*60)
        print(correo)
        print("="*60)
        
except Exception as e:
    print(f"❌ Error general: {e}")
