from google import genai

# 1. Tu API Key
client = genai.Client(api_key="AIzaSyAonDZsT-jP2UMDxJz4fPvwp4_I9o8O1yk")

try:
    # 2. Usamos el modelo 2.5 que es el vigente en 2026
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents="Hola Gemini, soy Nico. Dame un mensaje corto para mi app RunCheck."
    )
    
    print("\n--- ¡POR FIN FUNCIONÓ! ---")
    print(response.text)

except Exception as e:
    print(f"\nError: {e}")