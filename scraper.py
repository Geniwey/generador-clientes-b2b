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

# Objetivo semanal (45/día x 3 días = 135 + colchón de seguridad)
OBJETIVO_NUEVOS_LUNES = 180
guardados_hoy = 0

ciudades = [
    "Barcelona", "Madrid", "Valencia", "Algeciras", "Bilbao", "Vigo",
    "Zaragoza", "Las Palmas", "Sevilla", "Tarragona", "Alicante",
    "Castellón", "Málaga", "Murcia", "A Coruña", "Santander"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

DOMINIOS_PROHIBIDOS = [
    "paginasamarillas", "einforma", "infocif", "empresite", "axesor", "iberinform",
    "kompass", "europages", "linkedin", "facebook", "instagram", "twitter", "youtube",
    "google", "boe.es", "agenciatributaria", "correos.es", "sentry", "wix", "example",
    "wordpress", "cloudflare", "github", "amazonaws", "cs.money", "steampowered",
    "wikipedia", "tripadvisor", "booking", "amazon", "ebay", "aliexpress", "milanuncios",
    "wallapop", "infojobs", "indeed", "glassdoor", "expansion.com", "eleconomista",
    "cincodias", "diariodelpuerto", "elvigia", "veintepies", "transportexxi"
]

EXTENSIONES_BASURA = [
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js",
    ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".zip", ".json", ".map"
]

PALABRAS_BASURA_EMAIL = [
    "download", "pdf", "test", "bot", "noreply", "no-reply", "sentry", "daemon",
    "mailer", "example", "react", "lodash", "webpack", "babel", "jquery", "bootstrap",
    "tailwind", "angular", "vue", "next", "nuxt", "vite", "rollup", "eslint",
    "prettier", "axios", "swiper", "polyfill", "core-js", "moment", "dayjs",
    "privacidad", "privacy", "rgpd", "lopd", "protecciondedatos", "dpo",
    "webmaster", "postmaster", "abuse", "hostmaster", "root", "admin@", "support@wix"
]

PALABRAS_SECTOR_LOGISTICO = [
    "transitario", "transitarios", "aduana", "aduanas", "aduanero", "flete", "fletes",
    "maritimo", "marítimo", "aereo", "aéreo", "logistica", "logística", "contenedor",
    "contenedores", "importacion", "importación", "exportacion", "exportación",
    "freight", "forwarder", "forwarding", "customs", "cargo", "shipping", "nvocc",
    "grupaje", "consignatario", "despacho", "mercancias", "mercancías", "transporte internacional"
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
    if len(e) < 6 or len(e) > 85 or "@" not in e:
        return False

    if not re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,10}$", e):
        return False

    if any(e.endswith(ext) or ext in e for ext in EXTENSIONES_BASURA):
        return False
    if any(prohibido in e for prohibido in DOMINIOS_PROHIBIDOS):
        return False
    if any(basura in e for basura in PALABRAS_BASURA_EMAIL):
        return False

    partes = e.split('@')
    if len(partes) != 2:
        return False
    local_part, dom_part = partes[0], partes[1]

    # Bloquea versiones de paquetes JS tipo react-dom@18.2.0 o lodash@4.17.21
    if re.match(r"^\d+(\.\d+)+$", dom_part):
        return False

    # Bloquea prefijos numéricos largos o hashes
    if re.match(r"^\d{2,}", local_part):
        return False
    if re.match(r"^[0-9a-f]{12,}$", local_part):
        return False

    return True

def es_empresa_del_sector(nombre_empresa, dominio, texto_web):
    combinado = f"{nombre_empresa or ''} {dominio or ''} {texto_web or ''}".lower()
    return any(palabra in combinado for palabra in PALABRAS_SECTOR_LOGISTICO)

def extraer_contexto(url):
    if not url or url == "null":
        return "", False
    if not url.startswith('http'):
        url = 'https://' + url
    try:
        res = requests.get(url, headers=headers, timeout=4)
        soup = BeautifulSoup(res.text, 'html.parser')
        for s in soup(["script", "style", "noscript", "svg", "footer", "nav"]):
            s.extract()
        texto = soup.get_text(separator=' ', strip=True)
        texto_limpio = re.sub(r'\s+', ' ', texto)[:650]
        if len(texto_limpio) > 40:
            return texto_limpio, True
    except Exception:
        pass
    return "Operador logístico, transitario y despacho de aduanas en comercio exterior.", False

def guardar(empresa, email, origen, cargo="Operaciones / Tráfico", tel=None, web=None, contexto_precalculado=None):
    global guardados_hoy
    if guardados_hoy >= OBJETIVO_NUEVOS_LUNES:
        return
    if not supabase or not es_email_valido(email):
        return

    email_limpio = email.lower().strip()
    dom = dominio_limpio(web) or email_limpio.split("@")[1]
    nombre_limpio = (empresa or "Agencia Logística").split("|")[0].split("-")[0].strip()[:80]
    if len(nombre_limpio) < 2:
        nombre_limpio = "Agencia Logística"

    if contexto_precalculado is not None:
        contexto = contexto_precalculado
    else:
        contexto, leido_real = extraer_contexto(web)
        # Si leímos la web real y no tiene ni una palabra de logística/aduanas, descartamos (evita CS.MONEY, etc.)
        if leido_real and not es_empresa_del_sector(nombre_limpio, dom, contexto):
            print(f"🚫 [DESCARTADO FUERA DE SECTOR] {nombre_limpio} ({dom})")
            return

    try:
        supabase.table("prospectos").insert({
            "empresa": nombre_limpio,
            "email": email_limpio,
            "origen": origen,
            "estado": "PENDIENTE",
            "cargo_contacto": cargo,
            "telefono": tel,
            "contexto_empresa": contexto
        }).execute()
        guardados_hoy += 1
        print(f"✅ [CAZADO {
