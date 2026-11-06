import os
import requests
from supabase import create_client, Client

url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
groq_key = os.environ.get("GROQ_KEY")

supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

MODELOS_DISPONIBLES = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
]

def redactar_correo(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}

    prompt = """Eres el Fundador de LogiQuote, un SaaS B2B para agentes de aduanas y transitarios que automatiza el cálculo de fletes marítimos/aéreos, recargos locales (THC, BAF, despacho) y márgenes comerciales, generando cotizaciones en PDF en 30 segundos.
REGLAS ESTRICTAS:
1. Tono: Directo, natural y profesional de sector logístico B2B. Sin frases robóticas.
2. Saludo: Saluda con "Hola equipo de [Nombre de la empresa]," o simplemente "Hola,". NUNCA dejes corchetes sin rellenar ni inventes nombres propios.
3. Personalización: Usa el Contexto para mencionar de forma natural su actividad (aduanas, transporte marítimo, aéreo o logística) en las primeras dos líneas.
4. Propuesta de valor: Explica brevemente cómo LogiQuote les ahorra el cuello de botella de cruzar tarifarios y recargos en Excel.
5. Oferta: Invítales a probar la plataforma gratis durante 14 días en: https://logiquote-saas.vercel.app/
6. Código descuento: Añade que con el código LOGI10 tienen un 10% de descuento en su primer mes si deciden quedarse.
7. Despedida: Despídete EXACTAMENTE con:
Un saludo,
Equipo de Operaciones LogiQuote
https://logiquote-saas.vercel.app/
8. Formato: La primera línea DEBE empezar exactamente por "Asunto: " seguido de un asunto corto y técnico. El resto de líneas son el cuerpo del mensaje sin formato Markdown ni asteriscos."""

    for modelo in MODELOS_DISPONIBLES:
        data = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Escribe el correo para la empresa '{empresa}'. Contexto extraído de su web: '{contexto}'"}
            ],
            "temperature": 0.6
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=15)
            if res.status_code == 200:
                texto_completo = res.json()['choices'][0]['message']['content'].strip()
                lineas = [l for l in texto_completo.split('\n') if l.strip() != ""]
                asunto = lineas[0].replace("Asunto:", "").replace("**", "").replace("*", "").strip()
                cuerpo = '\n'.join(texto_completo.split('\n')[1:]).replace("**", "").strip()
                return asunto, cuerpo
        except Exception:
            continue
    return None, None

print("🧠 INICIANDO CEREBRO IA (REDACTANDO BORRADORES EN SUPABASE) 🧠")

# --- INYECTAR CORREO ESPÍA DE CONTROL ---
try:
    check = supabase.table("prospectos").select("id").eq("email", "marcxdiez@gmail.com").execute()
    if not check.data:
        supabase.table("prospectos").insert({
            "empresa": "Monitor LogiQuote",
            "email": "marcxdiez@gmail.com",
            "origen": "Control de Calidad",
            "estado": "PENDIENTE",
            "contexto_empresa": "Transitaria internacional especializada en flete marítimo FCL/LCL, transporte aéreo y despacho de aduanas en Barcelona."
        }).execute()
    else:
        supabase.table("prospectos").update({"estado": "PENDIENTE"}).eq("email", "marcxdiez@gmail.com").execute()
    print("✅ Correo espía (marcxdiez@gmail.com) preparado.")
except Exception as e:
    print(f"⚠️ Aviso con el correo espía: {e}")

# --- PROCESAR CLIENTES PENDIENTES ---
try:
    res = supabase.table("prospectos").select("*").eq("estado", "PENDIENTE").limit(35).execute()
    clientes = res.data

    if not clientes:
        print("✅ No hay clientes pendientes de redactar.")

    for c in clientes:
        print(f"\n✍️ Redactando borrador para: {c['empresa']}")
        asunto, cuerpo = redactar_correo(c['empresa'], c.get('contexto_empresa', ''))

        if not asunto or not cuerpo:
            print("  [!] Fallo en la IA. Saltando al siguiente.")
            continue

        supabase.table("prospectos").update({
            "asunto_email": asunto,
            "cuerpo_email": cuerpo,
            "estado": "REDACTADO"
        }).eq("id", c['id']).execute()
        print(f"  ✅ Borrador listo en Supabase (Estado: REDACTADO)")

except Exception as e:
    print(f"❌ Error general: {e}")

print("\n🏁 Tarea finalizada. Borradores guardados en Supabase listos para cuando decidas activar el envío.")
