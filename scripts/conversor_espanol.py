import json
import openai
import os
from openai_service import traducir_con_azure_openai
from openai import AzureOpenAI

input_file = "../datasets/dataset_ingles.jsonl"
output_file = "../datasets/dataset_espanol_2.jsonl"


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
