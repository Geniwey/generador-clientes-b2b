import os
import requests
from supabase import create_client, Client

url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
groq_key = os.environ.get("GROQ_KEY")

supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

# --- ROTADOR DE MODELOS (Basado en tu captura) ---
MODELOS_DISPONIBLES = [
    "openai/gpt-oss-120b",    # Tu primera opción (El más potente)
    "openai/gpt-oss-20b",     # Rescate ultra-rápido
    "llama-3.1-8b-instant"    # El soldado raso que nunca falla
]

def generar_correo_ia(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    
    prompt_sistema = """Eres el Director de Ventas de LogiQuote, un software SaaS B2B para agentes de aduanas y transitarios que automatiza el cálculo de fletes y recargos.
    Tu objetivo es escribir un "Cold Email" (correo frío) hiper-personalizado a un posible cliente.
    Reglas:
    1. Tono: Directo, profesional pero cercano. No suenes a vendedor de humo.
    2. Longitud: Corto (máximo 3-4 párrafos).
    3. Personalización: Usa el [Contexto Web] proporcionado para mencionar a qué se dedican (ej. marítimo, aduanas, perecederos).
    4. Cierre: Una sola pregunta sencilla que invite a responder (ej. "¿Tenéis 5 minutos la semana que viene para verlo?")."""
    
    # Bucle mágico: Intenta un modelo, si falla, va a por el siguiente
    for modelo in MODELOS_DISPONIBLES:
        data = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": f"Escribe un correo de ventas para la empresa '{empresa}' basándote en este contexto de su web: '{contexto}'"}
            ],
            "temperature": 0.7
        }

        try:
            res = requests.post(url, headers=headers, json=data)
            if res.status_code == 200:
                # Si funciona, devuelve el correo y el nombre del modelo que funcionó
                return res.json()['choices'][0]['message']['content'], modelo
            else:
                error_msg = res.json().get('error', {}).get('message', 'Error desconocido')
                print(f"  [!] El modelo {modelo} falló ({error_msg}). Cambiando al siguiente...")
                continue # Salta al siguiente modelo de la lista
        except Exception as e:
            print(f"  [!] Error de conexión con {modelo}: {e}. Cambiando al siguiente...")
            continue
            
    return "Error crítico: Ningún modelo de la lista funcionó.", "N/A"

print("🤖 Conectando a Supabase para leer 3 clientes reales...")
try:
    respuesta = supabase.table("prospectos").select("empresa, contexto_empresa").neq("contexto_empresa", "Sin información").limit(3).execute()
    clientes = respuesta.data
    
    if not clientes:
        print("⚠️ No hay clientes con contexto en la base de datos.")
    
    for c in clientes:
        print(f"\n--- Redactando para {c['empresa']} ---")
        correo, modelo_usado = generar_correo_ia(c['empresa'], c['contexto_empresa'])
        
        # El "Cocido" final formateado para leerlo bien
        print("="*70)
        print(f"📩 DESTINATARIO: {c['empresa']}")
        print(f"🧠 MODELO IA USADO: {modelo_usado}")
        print("="*70)
        print(correo)
        print("="*70)
        
except Exception as e:
    print(f"❌ Error general: {e}")
