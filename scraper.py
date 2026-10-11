import os
import time
import requests
import re
from bs4 import BeautifulSoup
from supabase import create_client, Client

# --- 1. CONEXIONES Y LLAVES SECRETAS ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
APOLLO_KEY = os.environ.get("APOLLO_KEY")
HUNTER_KEY = os.environ.get("HUNTER_KEY")
GOOGLE_MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY")

ciudades_españa = ["Barcelona", "Madrid", "Valencia", "Algeciras", "Bilbao", "Vigo", "Zaragoza"]
headers_navegador = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- 2. EL LECTOR DE CONTEXTO (Para la IA) ---
def extraer_contexto_web(url):
    """Visita la web de la empresa y lee a qué se dedican para hiper-personalizar el email."""
    if not url or url == "null": return "Sin información web"
    if not url.startswith('http'): url = 'https://' + url
    
    try:
        res = requests.get(url, headers=headers_navegador, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Borramos código basura para dejar solo texto legible
        for script in soup(["script", "style"]): script.extract()
        texto_puro = soup.get_text(separator=' ', strip=True)
        # Nos quedamos con los primeros 600 caracteres (suficiente para que la IA entienda el negocio)
        return texto_puro[:600]
    except:
        return "No se pudo analizar la web"

# --- 3. GUARDADO INTELIGENTE ---
def guardar_prospecto(empresa, email, origen, cargo="Desconocido", telefono=None, web=None):
    if not email or "null" in email.lower(): return
    if any(ext in email.lower() for ext in ['.png', '.jpg', 'sentry', 'wix']): return
    
    contexto = extraer_contexto_web(web)
    
    try:
        supabase.table("prospectos").insert({
            "empresa": empresa,
            "email": email.lower(),
            "origen": origen,
            "estado": "PENDIENTE",
            "cargo_contacto": cargo,
            "telefono": telefono,
            "contexto_empresa": contexto
        }).execute()
        print(f"✅ [GUARDADO] {empresa} | {cargo} | {email}")
    except:
        pass # Ignora duplicados automáticamente

# --- 4. MOTOR 1: APOLLO (CEOs y Directores) ---
def raspar_apollo():
    if not APOLLO_KEY: return
    print("🚀 Arrancando Motor 1: Apollo B2B...")
    url = "https://api.apollo.io/v1/mixed_people/search"
    data = {
        "api_key": APOLLO_KEY,
        "q_keywords": "transitario aduanas freight forwarder logistica",
        "person_titles": ["Operations", "Operaciones", "CEO", "Director", "Gerente", "Aduanas"],
        "person_locations": ["Spain"],
        "page": 1 
    }
    try:
        req = requests.post(url, headers={"Content-Type": "application/json"}, json=data)
        for persona in req.json().get('people', []):
            org = persona.get('organization', {})
            guardar_prospecto(
                empresa=org.get('name', 'Empresa Desconocida'),
                email=persona.get('email'),
                origen="Apollo",
                cargo=persona.get('title', 'Cargo Desconocido'),
                web=org.get('website_url')
            )
    except Exception as e:
        print(f"Error Apollo: {e}")

# --- 5. MOTOR 2: GOOGLE MAPS + HUNTER (Volumen Físico) ---
def raspar_google_y_hunter():
    if not GOOGLE_MAPS_KEY or not HUNTER_KEY: return
    print("🌍 Arrancando Motor 2: Maps + Hunter...")
    
    for ciudad in ciudades_españa:
        query = f"transitario agente de aduanas en {ciudad}, España"
        url_maps = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={GOOGLE_MAPS_KEY}"
        
        try:
            res_maps = requests.get(url_maps).json()
            for lugar in res_maps.get('results', []):
                nombre = lugar.get('name')
                place_id = lugar.get('place_id')
                
                # Saca la web y teléfono del mapa
                detalles = requests.get(f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=website,formatted_phone_number&key={GOOGLE_MAPS_KEY}").json().get('result', {})
                web = detalles.get('website')
                telefono = detalles.get('formatted_phone_number')
                
                if web:
                    dominio = web.split('//')[-1].split('/')[0].replace('www.', '')
                    # Le da el dominio a Hunter para sacar correos
                    url_hunter = f"https://api.hunter.io/v2/domain-search?domain={dominio}&api_key={HUNTER_KEY}"
                    correos = requests.get(url_hunter).json().get('data', {}).get('emails', [])
                    
                    if correos:
                        for c in correos:
                            guardar_prospecto(nombre, c.get('value'), f"Hunter ({ciudad})", c.get('position', 'Staff'), telefono, web)
                    else:
                        # MOTOR 3 (Rescate): Rascador web a fuerza bruta
                        try:
                            html = requests.get(web, headers=headers_navegador, timeout=5).text
                            emails_html = set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+", html))
                            for e in emails_html:
                                guardar_prospecto(nombre, e, f"Web Scraper ({ciudad})", "Web Extracted", telefono, web)
                        except:
                            pass
        except Exception as e:
            print(f"Error Maps en {ciudad}: {e}")

# --- ARRANQUE GENERAL ---
print("⚙️ MÁQUINA B2B CONTEXTUAL INICIADA ⚙️")
raspar_apollo()
raspar_google_y_hunter()
print("🏁 Extracción finalizada.")
