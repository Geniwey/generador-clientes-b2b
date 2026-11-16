import os
import re
import time
import requests
from supabase import create_client, Client

url_db = (os.environ.get("SUPABASE_URL") or "").strip()
key_db = (os.environ.get("SUPABASE_KEY") or "").strip()
groq_key = (os.environ.get("GROQ_KEY") or "").strip()

supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

def detectar_modelos_groq():
    respaldo = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile"
    ]
    if not groq_key:
        return respaldo
    try:
        res = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json().get("data", [])
            ids_disponibles = [
                m["id"] for m in data
                if m.get("id") and not any(
                    x in m["id"].lower()
                    for x in ["whisper", "guard", "tts", "playai", "embed", "safeguard", "orpheus"]
                )
            ]
            if ids_disponibles:
                ordenados = []
                for pref in ["gpt-oss-20b", "gpt-oss", "qwen", "llama-3.3", "llama-3.1", "llama"]:
                    for mid in ids_disponibles:
                        if pref in mid.lower() and mid not in ordenados:
                            ordenados.append(mid)
                return ordenados or respaldo
    except Exception:
        pass
    return respaldo

MODELOS_DISPONIBLES = detectar_modelos_groq()
print(f"🤖 Modelos Groq detectados para redacción: {MODELOS_DISPONIBLES}")

def limpiar_respuesta_ia(texto):
    if not texto:
        return ""
    # Elimina posibles bloques internos de razonamiento <think>...</think>
    limpio = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)
    limpio = limpio.replace('"', "").replace("«", "").replace("»", "").strip()
    # Si devuelve varias líneas, nos quedamos con la primera frase útil
    lineas = [l.strip() for l in limpio.splitlines() if l.strip()]
    return lineas[0] if lineas else ""

def redactar_rompehielos(empresa, contexto):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    contexto_seguro = (contexto or "").strip() or "Transitario internacional, gestión de fletes marítimos/aéreos y despachos de aduanas."

    prompt = """Eres un experto en ventas B2B en el sector logístico español. 
Tu único trabajo es escribir UNA SOLA FRASE (máximo 22 palabras) que sirva como "rompehielos" hiper-personalizado para abrir un correo.
REGLAS ESTRICTAS:
1. Trata siempre de "usted" (ej: "su trayectoria", "sus oficinas", "su operativa").
2. Menciona a qué se dedican basándote en el contexto (despachos de aduanas, operativas de importación/exportación, tránsitos, etc.).
3. NO saludes ("Hola", "Estimados", "Buenos días"). NO te despidas.
4. NO uses comillas ni etiquetas.
5. Ejemplo perfecto: He estado analizando su sólida trayectoria en la gestión de despachos aduaneros y tránsitos marítimos desde sus oficinas.
6. Tono corporativo, serio y muy profesional."""

    for modelo in MODELOS_DISPONIBLES:
        data = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Escribe la frase rompehielos para la empresa '{empresa}'. Contexto de su web: '{contexto_seguro[:400]}'"}
            ],
            "temperature": 0.4
        }
        try:
            res = requests.post(url, headers=headers, json=data, timeout=20)
            if res.status_code == 200:
                contenido = res.json()['choices'][0]['message']['content']
                frase = limpiar_respuesta_ia(contenido)
                if len(frase) > 15:
                    return frase
            elif res.status_code == 429:
                print(f"  ⏳ Límite temporal en {modelo}, esperando 3s y probando respaldo...")
                time.sleep(3)
                continue
        except Exception:
            continue
    return None

print("🧠 INICIANDO CEREBRO IA (GENERANDO ROMPEHIELOS PERSONALIZADOS) 🧠")

try:
    if not supabase:
        print("❌ Faltan credenciales de Supabase.")
        exit(1)

    # Busca clientes pendientes
    res = supabase.table("prospectos").select("*").eq("estado", "PENDIENTE").limit(50).execute()
    clientes = res.data or []

    if not clientes:
        print("✅ No hay clientes nuevos para procesar.")

    procesados = 0
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
        procesados += 1
        print(f"  ✅ Frase lista y guardada: {rompehielos}")
        time.sleep(1.5)

    print(f"\n📊 Total rompehielos generados hoy: {procesados}")

except Exception as e:
    print(f"❌ Error general: {e}")

print("\n🏁 Tarea finalizada.")
