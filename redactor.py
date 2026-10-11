import os
import requests
from supabase import create_client, Client

url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
groq_key = os.environ.get("GROQ_KEY")

supabase: Client = create_client(url_db, key_db) if url_db and key_db else None
MODELOS_DISPONIBLES = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]

def redactar_correo(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    
    prompt = """Eres el Fundador de LogiQuote, un SaaS B2B para agentes de aduanas y transitarios que automatiza el cálculo de fletes y recargos.
    REGLAS ESTRICTAS:
    1. Tono: Directo y profesional. Como si hablaras de tú a tú.
    2. Saludo: Saluda con "Hola equipo de {empresa}," o simplemente "Hola,". NUNCA uses corchetes como [Nombre del contacto] ni inventes nombres de personas.
    3. Personalización: Usa el [Contexto] para mencionar a qué se dedican en el primer párrafo.
    4. Oferta: Diles que pueden probar LogiQuote gratis durante 14 días entrando en: https://logiquote-saas.vercel.app/
    5. Regalo: Ofréceles el código LOGI10 para un 10% de descuento en su primera suscripción.
    6. Despedida: Despídete EXACTAMENTE con "CEO de LogiQuote" y debajo la web "https://logiquote-saas.vercel.app/". NUNCA pongas tu nombre, ni te inventes ninguno.
    7. Asunto: La primera línea DEBE ser el Asunto, empezando con "Asunto: ". El resto es el cuerpo del mensaje."""
    
    for modelo in MODELOS_DISPONIBLES:
        data = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Escribe un correo para la empresa '{empresa}'. Contexto: '{contexto}'"}
            ],
            "temperature": 0.7
        }
        try:
            res = requests.post(url, headers=headers, json=data)
            if res.status_code == 200:
                texto_completo = res.json()['choices'][0]['message']['content']
                lineas = texto_completo.split('\n')
                asunto = lineas[0].replace("Asunto:", "").replace("**", "").strip()
                cuerpo = '\n'.join(lineas[1:]).strip()
                return asunto, cuerpo
        except: continue
    return None, None

print("🧠 INICIANDO CEREBRO IA (REDACTANDO Y GUARDANDO EN SUPABASE) 🧠")

# --- INYECTAR CORREO ESPÍA DEL JEFE ---
try:
    check = supabase.table("prospectos").select("id").eq("email", "marcxdiez@gmail.com").execute()
    if not check.data:
        supabase.table("prospectos").insert({
            "empresa": "Monitor LogiQuote",
            "email": "marcxdiez@gmail.com",
            "origen": "Control de Calidad",
            "estado": "PENDIENTE",
            "contexto_empresa": "Empresa de pruebas para monitorear que la IA y los correos funcionan perfecto."
        }).execute()
    else:
        # Si ya existe, lo volvemos a poner PENDIENTE para forzar a la IA a escribirte otra vez
        supabase.table("prospectos").update({"estado": "PENDIENTE"}).eq("email", "marcxdiez@gmail.com").execute()
    print("✅ Correo espía (marcxdiez@gmail.com) listo para recibir prueba.")
except Exception as e:
    print(f"⚠️ Aviso con el correo espía: {e}")

# --- PROCESAR CLIENTES ---
try:
    # Cogemos 30 pendientes para que la IA los redacte y guarde
    res = supabase.table("prospectos").select("*").eq("estado", "PENDIENTE").neq("contexto_empresa", "Sin información").limit(30).execute()
    clientes = res.data
    
    if not clientes:
        print("✅ No hay clientes pendientes de redactar.")
        
    for c in clientes:
        print(f"\n✍️ Redactando correo para: {c['empresa']}")
        asunto, cuerpo = redactar_correo(c['empresa'], c['contexto_empresa'])
        
        if not asunto or not cuerpo:
            print("  [!] Fallo en la IA. Saltando al siguiente.")
            continue
            
        supabase.table("prospectos").update({
            "asunto_email": asunto,
            "cuerpo_email": cuerpo,
            "estado": "REDACTADO"
        }).eq("id", c['id']).execute()
        print(f"  ✅ Correo guardado en Supabase (Estado: REDACTADO)")
        
except Exception as e:
    print(f"❌ Error general: {e}")
print("\n🏁 Tarea finalizada. Textos guardados en Supabase.")
