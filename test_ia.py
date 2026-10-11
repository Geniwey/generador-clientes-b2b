import os
import requests
from supabase import create_client, Client

url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
groq_key = os.environ.get("GROQ_KEY")

supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

MODELOS_DISPONIBLES = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant"
]

def generar_correo_ia(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    
    prompt_sistema = """Eres el Fundador de LogiQuote, un software SaaS B2B para agentes de aduanas y transitarios que automatiza el cálculo de fletes y recargos.
    Tu objetivo es escribir un "Cold Email" (correo frío) hiper-personalizado a un posible cliente.
    
    REGLAS ESTRICTAS:
    1. Tono: Directo, profesional, pero como si hablaras de tú a tú. Cero agresividad comercial. No queremos "venderles" a la fuerza, solo que prueben la herramienta.
    2. Personalización: Usa el [Contexto Web] para mencionar un detalle de su empresa (ej. si hacen marítimo, aéreo, aduanas, etc.) en el primer párrafo para demostrar que no es un envío masivo.
    3. Oferta (El núcleo del correo): NO pidas videollamadas. NO pidas reuniones. Diles que pueden probar LogiQuote gratis durante 14 días sin compromiso entrando en: https://logiquote-saas.vercel.app/
    4. Descuento: Ofréceles el código de descuento "LOGI10" para obtener un 10% off en su primera suscripción (mensual o anual) como detalle por leerte en frío.
    5. Despedida: Despídete amablemente, indicando que si tienen dudas pueden responder al correo. FIRMA SOLO CON: Tu nombre (CEO en LogiQuote) y la web (https://logiquote-saas.vercel.app/). NUNCA inventes números de teléfono.
    6. Longitud: Corto y directo al grano (3-4 párrafos).
    """
    
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
                return res.json()['choices'][0]['message']['content'], modelo
            else:
                continue
        except Exception:
            continue
            
    return "Error crítico: Ningún modelo funcionó.", "N/A"

print("🤖 Conectando a Supabase para leer 3 clientes reales...")
try:
    respuesta = supabase.table("prospectos").select("empresa, contexto_empresa").neq("contexto_empresa", "Sin información").limit(3).execute()
    clientes = respuesta.data
    
    for c in clientes:
        print(f"\n--- Redactando para {c['empresa']} ---")
        correo, modelo_usado = generar_correo_ia(c['empresa'], c['contexto_empresa'])
        
        print("="*70)
        print(f"📩 DESTINATARIO: {c['empresa']}")
        print("="*70)
        print(correo)
        print("="*70)
        
except Exception as e:
    print(f"❌ Error general: {e}")
