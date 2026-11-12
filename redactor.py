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

def redactar_rompehielos(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}

    prompt = """Eres un experto en ventas B2B en el sector logístico español. 
Tu único trabajo es escribir UNA SOLA FRASE (máximo 20 palabras) que sirva como "rompehielos" hiper-personalizado para abrir un correo.
REGLAS ESTRICTAS:
1. Trata siempre de "usted" (ej: "su trayectoria", "sus oficinas").
2. Menciona a qué se dedican basándote en el contexto (despachos de aduanas, operativas de importación/exportación, tránsitos, etc.).
3. NO saludes ("Hola", "Estimados"). NO te despidas.
4. NO uses comillas.
5. Ejemplo perfecto: He estado analizando su sólida trayectoria en la gestión de despachos aduaneros y tránsitos marítimos desde sus oficinas.
6. Tono corporativo, serio y muy profesional."""

    for modelo in MODELOS_DISPONIBLES:
        data = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Escribe la frase rompehielos para la empresa '{empresa}'. Contexto de su web: '{contexto}'"}
            ],
            "temperature": 0.4
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=15)
            if res.status_code == 200:
                frase = res.json()['choices'][0]['message']['content'].replace('"', '').strip()
                return frase
        except Exception:
            continue
    return None

print("🧠 INICIANDO CEREBRO IA (GENERANDO ROMPEHIELOS PERSONALIZADOS) 🧠")

try:
    # Busca clientes pendientes
    res = supabase.table("prospectos").select("*").eq("estado", "PENDIENTE").limit(50).execute()
    clientes = res.data

    if not clientes:
        print("✅ No hay clientes nuevos para procesar.")

    for c in clientes:
        # Si ya tiene algo guardado en cuerpo_email, es que ya tiene su frase hecha. Lo saltamos.
        if c.get('cuerpo_email'):
            continue

        print(f"\n✍️ Pensando rompehielos para: {c['empresa']}")
        rompehielos = redactar_rompehielos(c['empresa'], c.get('contexto_empresa', ''))

        if not rompehielos:
            print("  [!] Fallo en la IA. Saltando al siguiente.")
            continue

        # Lo guardamos en la columna cuerpo_email pero MANTENEMOS el estado en PENDIENTE
        # para que Google Apps Script pueda encontrarlo mañana.
        supabase.table("prospectos").update({
            "cuerpo_email": rompehielos
        }).eq("id", c['id']).execute()
        print(f"  ✅ Frase lista y guardada: {rompehielos}")

except Exception as e:
    print(f"❌ Error general: {e}")

print("\n🏁 Tarea finalizada.")
