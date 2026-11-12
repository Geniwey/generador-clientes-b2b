import os
import time
import requests
import re
import warnings
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from googlesearch import search
from ddgs import DDGS
from supabase import create_client, Client

warnings.filterwarnings("ignore")

url_db = os.environ.get("SUPABASE_URL")
key_db = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url_db, key_db) if url_db and key_db else None

APOLLO_KEY = os.environ.get("APOLLO_KEY")
HUNTER_KEY = os.environ.get("HUNTER_KEY")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

ciudades = ["Barcelona", "Madrid", "Valencia", "Algeciras", "Bilbao", "Vigo", "Zaragoza", "Las Palmas", "Sevilla"]
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

DOMINIOS_PROHIBIDOS = [
    "paginasamarillas", "einforma", "infocif", "empresite", "axesor", "iberinform",
    "kompass", "europages", "linkedin", "facebook", "instagram", "twitter", "youtube",
    "google", "boe.es", "agenciatributaria", "correos.es", "sentry", "wix", "example",
    "wordpress", "cloudflare", "github", "amazonaws"
]

EXTENSIONES_BASURA = [
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js", ".pdf", ".woff", ".ttf"
]

PALABRAS_BASURA_EMAIL = [
    "download", "pdf", "test", "bot", "noreply", "no-reply", "sentry", "daemon", "mailer", "example"
]

def dominio_limpio(url):
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        netloc = urlparse(url).netloc.lower().replace("www.", "")
        return netloc.split(":")[0]
    except Exception:
        return ""

def es_web_valida(url):
    dom = dominio_limpio(url)
    if not dom or "." not in dom:
        return False
    return not any(prohibido in dom for prohibido in DOMINIOS_PROHIBIDOS)

def es_email_valido(email):
    if not email or "null" in email.lower():
        return False
    e = email.lower().strip()
    if len(e) < 6 or len(e) > 90 or "@" not in e:
        return False
    
    # 1. Filtro de extensiones y dominios
    if any(ext in e for ext in EXTENSIONES_BASURA):
        return False
    if any(prohibido in e for prohibido in DOMINIOS_PROHIBIDOS):
        return False
    
    # 2. Filtro anti-basura (pdf-lib, downloadjs, etc)
    if any(basura in e for basura in PALABRAS_BASURA_EMAIL):
        return False
        
    partes = e.split('@')
    if len(partes) != 2: 
        return False
    local_part = partes[0]

    # 3. Filtro de números raros (bloquea cosas como 20peru@ o 1234@)
    if re.match(r"^\d{2,}", local_part):
        return False
        
    if re.match(r"^[0-9a-f]{16,}@", e):
        return False
    return True

def extraer_contexto(url):
    if not url or url == "null":
        return "Agencia de transporte internacional, transitaria y gestión aduanera."
    if not url.startswith('http'):
        url = 'https://' + url
    try:
        res = requests.get(url, headers=headers, timeout=4)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(["script", "style", "noscript", "svg", "footer", "nav"]):
            s.extract()
        texto = soup.get_text(separator=' ', strip=True)
        texto_limpio = re.sub(r'\s+', ' ', texto)[:600]
        return texto_limpio if len(texto_limpio) > 40 else "Operador logístico, transitario y despacho de aduanas en comercio exterior."
    except Exception:
        return "Operador logístico, transitario y despacho de aduanas en comercio exterior."

def guardar(empresa, email, origen, cargo="Operaciones / Tráfico", tel=None, web=None):
    if not supabase or not es_email_valido(email):
        return

    email_limpio = email.lower().strip()
    nombre_limpio = (empresa or "Agencia Logística").split("|")[0].split("-")[0].strip()[:80]
    if len(nombre_limpio) < 2:
        nombre_limpio = "Agencia Logística"

    try:
        supabase.table("prospectos").insert({
            "empresa": nombre_limpio,
            "email": email_limpio,
            "origen": origen,
            "estado": "PENDIENTE",
            "cargo_contacto": cargo,
            "telefono": tel,
            "contexto_empresa": extraer_contexto(web)
        }).execute()
        print(f"✅ [CAZADO] {nombre_limpio} | {email_limpio} | Vía: {origen}")
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate" not in error_msg and "unique" not in error_msg:
            print(f"❌ Error en Supabase al guardar {email_limpio}: {e}")

def priorizar_emails(lista_emails):
    prioridades = ["aduanas", "trafico", "operaciones", "pricing", "import", "export", "comercial", "logistica", "fletes", "info"]
    ordenados = sorted(
        lista_emails,
        key=lambda x: next((i for i, p in enumerate(prioridades) if p in x.lower()), 99)
    )
    return ordenados[:3]

def buscar_correos_por_web(dominio, nombre_empresa, origen_base, tel=None, web_full=None):
    if not dominio or any(p in dominio for p in DOMINIOS_PROHIBIDOS):
        return

    encontrado = False
    if HUNTER_KEY:
        try:
            url_h = f"https://api.hunter.io/v2/domain-search?domain={dominio}&api_key={HUNTER_KEY}"
            correos = requests.get(url_h, timeout=4).json().get('data', {}).get('emails', [])
            for c in correos[:3]:
                guardar(nombre_empresa, c.get('value'), f"Hunter ({origen_base})", c.get('position', 'Operaciones'), tel, web_full)
                encontrado = True
        except Exception:
            pass

    if not encontrado and web_full:
        urls_a_mirar = [web_full]
        base_url = f"https://{dominio}"
        urls_a_mirar.extend([f"{base_url}/contacto", f"{base_url}/contact", f"{base_url}/aviso-legal"])

        emails_hallados = set()
        for u in urls_a_mirar:
            try:
                html = requests.get(u, headers=headers, timeout=3).text
                hallados = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+", html)
                for e in hallados:
                    if es_email_valido(e):
                        emails_hallados.add(e.lower())
                if emails_hallados:
                    break
            except Exception:
                continue

        for e in priorizar_emails(list(emails_hallados)):
            guardar(nombre_empresa, e, f"Web ({origen_base})", "Departamento de Tráfico / Operaciones", tel, web_full)

def motor_apollo():
    if not APOLLO_KEY:
        return
    print("🚀 Arrancando Motor 1: Apollo B2B (Cargos Clave)...")
    try:
        url = "https://api.apollo.io/v1/mixed_people/search"
        data = {
            "api_key": APOLLO_KEY,
            "q_keywords": "transitario aduanas freight forwarder logistica maritima",
            "person_titles": ["Pricing", "Operations", "Operaciones", "Seafreight", "Aduanas", "Tráfico", "CEO", "Director", "Gerente"],
            "person_locations": ["Spain"],
            "page": 1
        }
        req = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=6)
        resultados = req.json().get('people', [])

        for p in resultados:
            org = p.get('organization', {})
            guardar(org.get('name', 'Agencia Transitaria'), p.get('email'), "Apollo B2B", p.get('title', 'Responsable Operaciones'), web=org.get('website_url'))
    except Exception as e:
        print(f"❌ Error en Apollo: {e}")

def motor_serpapi(ciudad):
    if not SERPAPI_KEY:
        return
    print(f"🌍 Arrancando Motor 2 (Google Maps / SerpApi) para {ciudad}...")
    try:
        res = requests.get(
            f"https://serpapi.com/search.json?engine=google_maps&q=transitario agente de aduanas {ciudad} España&api_key={SERPAPI_KEY}",
            timeout=6
        ).json()

        locales = res.get('local_results', [])
        for lugar in locales:
            web = lugar.get('website')
            if web and es_web_valida(web):
                dominio = dominio_limpio(web)
                buscar_correos_por_web(dominio, lugar.get('title'), f"Maps {ciudad}", lugar.get('phone'), web)
    except Exception as e:
        print(f"❌ Error en SerpApi ({ciudad}): {e}")

def motor_censos_y_federaciones(ciudad):
    print(f"⚓ Arrancando Motor 3 (ATEIA, Colegios de Aduanas y Puerto) para {ciudad}...")
    queries = [
        f'transitario "aduanas" "{ciudad}" "flete" sitio oficial',
        f'"agente de aduanas" OR "ATEIA" "{ciudad}" contacto email',
        f'operador logistico maritimo aereo "{ciudad}" "contenedores" contacto'
    ]
    for q in queries:
        try:
            resultados = DDGS().text(q, max_results=4)
            for r in resultados:
                web = r.get('href', '')
                if web and es_web_valida(web):
                    dominio = dominio_limpio(web)
                    buscar_correos_por_web(dominio, r.get('title', f'Transitaria {ciudad}'), f"Censo/DDG {ciudad}", web_full=web)
        except Exception:
            pass

def motor_google_dorking(ciudad):
    print(f"🔍 Arrancando Motor 4 (Google Dorking Directo) para {ciudad}...")
    try:
        query = f'inurl:contacto ("transitario" OR "despacho de aduanas" OR "flete maritimo") "{ciudad}"'
        for web in search(query, num_results=3, sleep_interval=1):
            if not es_web_valida(web):
                continue
            dominio = dominio_limpio(web)
            buscar_correos_por_web(dominio, f"Transitaria {ciudad}", f"Dorking {ciudad}", web_full=web)
    except Exception:
        pass

print("⚙️ MEGA-MÁQUINA LOGIQUOTE B2B INICIADA (MODO PREPARACIÓN) ⚙️")
motor_apollo()
for ciudad in ciudades:
    motor_serpapi(ciudad)
    motor_censos_y_federaciones(ciudad)
    motor_google_dorking(ciudad)

print("🏁 Extracción finalizada. Prospectos guardados en Supabase (sin enviar correos).")
