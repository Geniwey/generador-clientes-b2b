import os
import requests
from supabase import create_client, Client

# 1. Conexión a tu Base de Datos (Supabase)
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 2. Conexión al Cerebro B2B (Apollo.io)
APOLLO_KEY = os.environ.get("APOLLO_KEY")

def arrancar_megamaquina():
    if not APOLLO_KEY:
        print("❌ Falla la API Key de Apollo. Ponla en los Secrets de GitHub.")
        return

    print("🚀 Iniciando extracción B2B VIP en Apollo.io...")
    
    # Endpoint oficial de búsqueda de Apollo
    api_url = "https://api.apollo.io/v1/mixed_people/search"
    
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json"
    }
    
    # El Filtro Francotirador: Qué queremos cazar exactamente
    data = {
        "api_key": APOLLO_KEY,
        "q_keywords": "logistics transitario aduanas freight forwarder forwarding marítimo",
        "person_titles": ["Operations", "Operaciones", "Logistics", "Logística", "CEO", "Director", "Gerente", "Aduanas", "Import", "Export", "Traffic"],
        "person_locations": ["Spain", "España"],
        "page": 1 # El robot empezará por la página 1. Más adelante podemos hacer que pase páginas automáticamente.
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        
        if response.status_code != 200:
            print(f"⚠️ Error de conexión con Apollo: {response.text}")
            return
            
        resultados = response.json().get('people', [])
        
        if not resultados:
            print("No se han encontrado contactos nuevos en esta pasada.")
            return

        for persona in resultados:
            email = persona.get('email')
            empresa = persona.get('organization', {}).get('name', 'Empresa Desconocida')
            cargo = persona.get('title', 'Cargo Desconocido')
            nombre = persona.get('first_name', '')
            
            # Solo guardamos si Apollo nos da un email corporativo válido y real
            if email and email != "null":
                print(f"✅ ¡VIP CAZADO!: {nombre} ({cargo}) en {empresa} -> {email}")
                
                try:
                    # Lo guardamos en tu Supabase listo para el futuro envío
                    supabase.table("prospectos").insert({
                        "empresa": empresa,
                        "email": email.lower(),
                        "origen": f"Apollo: {cargo}",
                        "estado": "PENDIENTE"
                    }).execute()
                except Exception as e:
                    # Si ya está en la base de datos, lo ignoramos para no duplicar
                    pass
                    
        print(f"🏁 Batida completada. Base de datos actualizada.")
        
    except Exception as e:
        print(f"❌ Error crítico en el motor: {e}")

# Encendemos la máquina
arrancar_megamaquina()
