import json
import openai
import os
import re

from openai import AzureOpenAI

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="tu-endpoint",
    api_key="tu-api"
)

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
    

def extraer_texto_entre_asteriscos(oracion):
    """
    Extrae el texto encerrado entre ** en una oración.
    Si no hay coincidencias, devuelve None.
    """
    coincidencia = re.search(r"\*\*(.+?)\*\*", oracion)
    return coincidencia.group(1) if coincidencia else None

def extraer_texto_entre_comillas(texto):
    """
    Extrae el texto encerrado entre comillas escapadas \" en una oración.
    Si no hay coincidencias, devuelve None.
    """
    coincidencia = re.search(r'\"(.*?)\"', texto)
    return coincidencia.group(1) if coincidencia else None

def extraer_sujeto_openai(oracion):
    try:

        response = client.chat.completions.create(
            max_tokens=1024,
            temperature=0.5,
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"""Dada una oración en español, extrae el sujeto principal que debe usarse para buscar en Wikidata. Sigue estas reglas:

        1. Si el sujeto es una persona (como actores, políticos, etc.), devuelve su nombre completo, sin artículos ni descripciones.
        - Ejemplo: Ryan Gosling ha estado en un país de África → Ryan Gosling

        2. Si el sujeto es un cargo o título (como "el Papa", "el emperador"), devuelve el nombre de la persona si aparece. Si solo se menciona el cargo, ignora la oración.
        - Ejemplo: El Papa Francisco visitó Brasil → Papa Francisco
        - Ejemplo: El Papa visitó Brasil → (ignorar)

        3. Si el sujeto es una obra (película, serie, libro...), devuelve solo el título, sin añadidos como "(película)".
        - Ejemplo: Los Diez Mandamientos es una película épica → Los Diez Mandamientos

        4. Si el sujeto es un territorio, país o región, y no hay ninguna persona como sujeto, devuelve solo el nombre del lugar.
        - Ejemplo: La taiga de España es verde → España

        5. Si hay tanto persona como lugar, prioriza a la persona.
        - Ejemplo: Ryan Gosling ha estado en un país de África → Ryan Gosling

        Devuelve solo el sujeto extraído, sin explicaciones ni texto adicional.

        Oración: {oracion}"""
                }
            ]
        )
        mensaje = response.choices[0].message.content
        '''
        "Extrae el sujeto para encontrarlo en wikidata, si es un papa o un cargo, devolver solo su nombre completo, sin artículos ni nada, si es una película, no hace falta poner entre paréntesis que lo es, solo el nombre y si el sujeto es un imperio o terreno de un sitio, devolver solo el sitio siempre y cuando que el sujeto no sea una persona por ejemplo, en Ryan Gosling ha estado en un país de África, el sujeto es Ryan Gosling. Sin embargo, en la taiga de España es verde, el sujeto es solo España: {oracion}"
        ''' 
        sujeto = extraer_texto_entre_asteriscos(mensaje)
        if sujeto:
            sujeto2 = extraer_texto_entre_comillas(sujeto)
            if sujeto2:
                return sujeto2
            return sujeto
        sujeto = extraer_texto_entre_comillas(mensaje)
        if (sujeto):
            return sujeto
           
        return mensaje
    
    except Exception as e:
        print(f"Error al obtener el sujeto con Azure OpenAI: {e}")
        return ""