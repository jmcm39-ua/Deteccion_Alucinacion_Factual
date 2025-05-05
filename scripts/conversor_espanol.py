import json
import openai
import os

from openai import AzureOpenAI

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="Tu endpoint",
    api_key="Tu token"
)

input_file = "../datasets/dataset_ingles.jsonl"
output_file = "../datasets/dataset_espanol_2.jsonl"

# Función para traducir con Azure OpenAI
def traducir_con_azure_openai(texto):
    try:

        response = client.chat.completions.create(max_tokens=1024,
            temperature=0.5,
            model="gpt-4o",
            messages=[
                {"role": "user", "content": f"Traduce al español el siguiente texto: {texto}"}
            ])
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error al traducir con Azure OpenAI: {e}")
        return ""

# Leer archivo original y escribir traducciones
numero = 1
with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for linea in fin:
        print(f"Traduciendo {numero}/2000")
        datos = json.loads(linea)
        claim = datos.get("claim", "")
        label = datos.get("label", "")

        # Traducir el claim usando Azure OpenAI
        traduccion = traducir_con_azure_openai(claim)

        # Guardar la línea traducida en formato JSONL
        json_line = json.dumps({
            "claim_es": traduccion,
            "label": label
        }, ensure_ascii=False)

        fout.write(json_line + "\n")
        numero += 1

print("Traducción completada y guardada en el archivo.")
