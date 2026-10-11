import os
import re
import time
import requests
from googlesearch import search
from supabase import create_client, Client

# Conecta con tu base de datos secreta
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Búsquedas más específicas para encontrar directorios directos
busquedas = [
    "transitarios barcelona correo contacto",
    "agentes de aduanas valencia email",
    "empresas logistica internacional algeciras contacto"
]

patron_email = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for busqueda in busquedas:
    print(f"🔍 Buscando en Google: {busqueda}")
    try:
        for url_web in search(busqueda, num_results=5, sleep_interval=5):
            try:
                # Evitamos redes sociales y directorios genéricos
                if any(x in url_web for x in ['linkedin', 'facebook', 'instagram', 'paginasamarillas']):
                    continue
                    
                print(f"Escanenado web: {url_web}")
                # Entramos en la web haciéndonos pasar por un navegador normal
                respuesta = requests.get(url_web, headers=headers, timeout=10)
                emails_encontrados = set(re.findall(patron_email, respuesta.text))
                
                try:
                    empresa_nombre = url_web.split('//')[1].split('/')[0].replace('www.', '')
                except:
                    empresa_nombre = "Empresa Desconocida"

                for email in emails_encontrados:
                    if any(ext in email.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', 'sentry', 'wix']):
                        continue
                        
                    print(f"✅ ¡Cazado!: {email} en {empresa_nombre}")
                    
                    try:
                        supabase.table("prospectos").insert({
                            "empresa": empresa_nombre,
                            "email": email.lower(),
                            "origen": "GitHub Auto-Scraper",
                            "estado": "PENDIENTE"
                        }).execute()
                    except Exception as e:
                        print(f"⚠️ Email ya existe o error en BD: {email}")
            except Exception as e:
                print(f"❌ No se pudo leer {url_web}")
            
            # Pausa para no ser bloqueados
            time.sleep(2)
            
    except Exception as e:
        print(f"Error en la búsqueda general: {e}")
