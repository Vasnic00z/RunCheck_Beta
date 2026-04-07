import google
import google.generativeai as genai

# 1. Configura tu clave de API 
# Reemplaza lo que está entre comillas con tu clave real
genai.configure(api_key="AIzaSyAonDZsT-jP2UMDxJz4fPvwp4_I9o8O1yk")

# 2. Seleccionamos el modelo
# Gemini 1.5 Flash es ideal para empezar por ser muy rápido
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Definimos una pregunta o instrucción
prompt = "Explícame en tres puntos breves por qué es útil aprender a usar una API de IA."

# 4. Enviamos la solicitud
response = model.generate_content(prompt)

# 5. Mostramos el resultado en la pantalla
print("\n--- Respuesta de Gemini ---")
print(response.text)

pip install google-generativeai

