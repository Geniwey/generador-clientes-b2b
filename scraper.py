import os
import time
import requests
import re
import warnings
from bs4 import BeautifulSoup
from googlesearch import search
from duckduckgo_search import DDGS
from supabase import create_client, Client

# --- APAGAR AVISOS MOLESTOS DE LA CONSOLA ---
warnings.filterwarnings("ignore")

# --- 1. CONEXIONES Y LLAVES ---
url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

APOLLO_KEY = os.environ.get("APOLLO_KEY")
HUNTER_KEY = os.environ.get("HUNTER_KEY")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

ciudades = ["Barcelona", "Madrid", "Valencia", "Algeciras", "Bilbao", "Vigo", "Zaragoza"]
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# --- 2. INTELIGENCIA (Lector de Contexto Ultrarrápido) ---
def extraer_contexto(url):
    if not url or url == "null": return "Sin información"
    if not url.startswith('http'): url = 'https://' + url
    try:
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(["script", "style"]): s.extract()
        return soup.get_text(separator=' ', strip=True)[:500]
    except:
        return "No se pudo leer la web"

# --- 3. ALMACÉN (Con chivato de errores) ---
def guardar(empresa, email, origen, cargo="Desconocido", tel=None, web=None):
    if not supabase or not email or "null" in email.lower(): return
    if any(ext in email.lower() for ext in ['.png', '.jpg', 'wix', 'example', 'sentry']): return
    
    email_limpio = email.lower().strip()
    
    try:
        supabase.table("prospectos").insert({
            "empresa": empresa,
            "email": email_limpio,
            "origen": origen,
            "estado": "PENDIENTE",
            "cargo_contacto": cargo,
            "telefono": tel,
            "contexto_empresa": extraer_contexto(web)
        }).execute()
        print(f"✅ [CAZADO] {empresa} | {email_limpio} | Vía: {origen}")
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate" not in error_msg and "unique" not in error_msg:
            print(f"❌ Error en Supabase al guardar {email_limpio}: {e}")

# --- 4. MOTOR DE CORREOS (Hunter + Scraper) ---
def buscar_correos_por_web(dominio, nombre_empresa, origen_base, tel=None, web_full=None):
    encontrado = False
    if HUNTER_KEY:
        try:
            url_h = f"https://api.hunter.io/v2/domain-search?domain={dominio}&api_key={HUNTER_KEY}"
            correos = requests.get(url_h, timeout=3).json().get('data', {}).get('emails', [])
            for c in correos:
                guardar(nombre_empresa, c.get('value'), f"Hunter ({origen_base})", c.get('position', 'Staff'), tel, web_full)
                encontrado = True
        except: pass
    
    if not encontrado and web_full:
        try:
            html = requests.get(web_full, headers=headers, timeout=3).text
            emails = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+", html))
            for e in emails:
                guardar(nombre_empresa, e, f"Web Scraper ({origen_base})", "Web Extracted", tel, web_full)
        except: pass

# --- 5. MOTOR 1: APOLLO (API - Directivos VIP) ---
def motor_apollo():
    if not APOLLO_KEY: return
    print("🚀 Arrancando Motor 1: Apollo B2B...")
    try:
        url = "https://api.apollo.io/v1/mixed_people/search"
        data = {
            "api_key": APOLLO_KEY,
            "q_keywords": "transitario aduanas freight forwarder",
            "person_titles": ["Operations", "Operaciones", "CEO", "Director", "Gerente", "Aduanas"],
            "person_locations": ["Spain"],
            "page": 1 
        }
        req = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=5)
        resultados = req.json().get('people', [])
        
        if not resultados:
            print("⚠️ Apollo ejecutado pero no devolvió resultados.")
            
        for p in resultados:
            org = p.get('organization', {})
            guardar(org.get('name', 'Empresa Desconocida'), p.get('email'), "Apollo", p.get('title', 'Cargo Desconocido'), web=org.get('website_url'))
    except Exception as e: print(f"❌ Error crítico en Apollo: {e}")

# --- 6. MOTOR 2: SERPAPI (API - Google Maps) ---
def motor_serpapi(ciudad):
    if not SERPAPI_KEY: return
    print(f"🌍 Arrancando Motor 2 (Maps) para {ciudad}...")
    try:
        res = requests.get(f"https://serpapi.com/search.json?engine=google_maps&q=transitario agente aduanas {ciudad} España&api_key={SERPAPI_KEY}", timeout=5).json()
        
        locales = res.get('local_results', [])
        if not locales:
            print(f"⚠️ SerpApi ejecutado pero sin resultados para {ciudad}.")
            
        for lugar in locales:
            web = lugar.get('website')
            if web:
                dominio = web.split('//')[-1].split('/')[0].replace('www.', '')
                buscar_correos_por_web(dominio, lugar.get('title'), f"Maps {ciudad}", lugar.get('phone'), web)
    except Exception as e: print(f"❌ Error crítico en SerpApi: {e}")

# --- 7. MOTOR 3: DUCKDUCKGO (Fuerza Bruta Ligera) ---
def motor_duckduckgo(ciudad):
    print(f"🦆 Arrancando Motor 3 (DuckDuckGo) para {ciudad}...")
    try:
        resultados = DDGS().text(f"transitario logistica aduanas {ciudad} España sitio oficial", max_results=3)
        for r in resultados:
            web = r.get('href', '')
            if web and 'linkedin' not in web and 'facebook' not in web:
                dominio = web.split('//')[-1].split('/')[0].replace('www.', '')
                buscar_correos_por_web(dominio, r.get('title', 'Empresa DDG'), f"DDG {ciudad}", web_full=web)
    except: pass

# --- 8. MOTOR 4: GOOGLE DORKING (Rescate) ---
def motor_google_dorking(ciudad):
    print(f"🔍 Arrancando Motor 4 (Google Dorking) para {ciudad}...")
    try:
        query = f'inurl:contacto "transitario" OR "aduanas" {ciudad}'
        for web in search(query, num_results=2, sleep_interval=1):
            if 'paginasamarillas' in web or 'linkedin' in web: continue
            dominio = web.split('//')[-1].split('/')[0].replace('www.', '')
            buscar_correos_por_web(dominio, "Empresa Búsqueda", f"Google Dorking {ciudad}", web_full=web)
    except: pass

# --- EJECUCIÓN MAESTRA ---
print("⚙️ MEGA-MÁQUINA B2B INICIADA (MODO ALTA VELOCIDAD Y DEBUG) ⚙️")
motor_apollo()
for ciudad in ciudades:
    motor_serpapi(ciudad)
    motor_duckduckgo(ciudad)
    motor_google_dorking(ciudad)

print("🏁 Ejecución diaria finalizada. Revisar base de datos.")
