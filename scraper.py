import os
import re
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from supabase import create_client, Client

# Conecta con tu base de datos secreta
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# El radar: Qué vamos a buscar en Google
busquedas = [
    "transitarios barcelona",
    "agentes de aduanas valencia",
    "empresas de logistica internacional algeciras"
]

# El filtro para detectar correos electrónicos válidos
patron_email = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+"

for busqueda in busquedas:
    print(f"🔍 Buscando en Google: {busqueda}")
    try:
        # CORRECCIÓN: Usamos num_results=10 y sleep_interval=2 para la nueva versión
        for url_web in search(busqueda, num_results=10, sleep_interval=2):
            try:
                print(f"Escanenado web: {url_web}")
                respuesta = requests.get(url_web, timeout=5)
                emails_encontrados = set(re.findall(patron_email, respuesta.text))
                
                # Saca el nombre de la empresa a partir de la URL limpia
                empresa_nombre = url_web.split('//')[1].split('/')[0].replace('www.', '')

                for email in emails_encontrados:
                    # Filtramos basura (imágenes, extensiones raras)
                    if any(ext in email for ext in ['.png', '.jpg', '.jpeg', '.gif', 'sentry', 'wix']):
                        continue
                        
                    print(f"✅ ¡Cazado!: {email} en {empresa_nombre}")
                    
                    # Lo enviamos directo a tu Supabase
                    try:
                        supabase.table("prospectos").insert({
                            "empresa": empresa_nombre,
                            "email": email.lower(),
                            "origen": "GitHub Auto-Scraper",
                            "estado": "PENDIENTE"
                        }).execute()
                    except:
                        # Si da error es porque ese email ya está en la base de datos
                        pass
            except:
                continue
    except Exception as e:
        print(f"Error en la búsqueda general: {e}")
