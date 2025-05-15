import json
import matplotlib.pyplot as plt
from collections import Counter
import os

def generar_grafica_dataset(path_archivo, nombre_imagen="distribucion_dataset.png"):
    # Contador para las etiquetas
    contador_etiquetas = Counter()

    # Leer el archivo jsonl
    with open(path_archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            if linea.strip():  # evitar líneas vacías
                try:
                    dato = json.loads(linea)
                    etiqueta = dato.get("label")
                    if etiqueta:
                        contador_etiquetas[etiqueta] += 1
                except json.JSONDecodeError:
                    print("Línea con formato inválido: ", linea)

    # Preparar datos para la gráfica
    etiquetas = list(contador_etiquetas.keys())
    cantidades = [contador_etiquetas[etiqueta] for etiqueta in etiquetas]

    # Crear la gráfica
    plt.figure(figsize=(6, 4))
    colores = ['green' if e == 'FACTUAL' else 'red' for e in etiquetas]
    plt.bar(etiquetas, cantidades, color=colores)
    plt.title('Distribución de ejemplos por tipo de factualidad')
    plt.ylabel('Número de ejemplos')
    plt.xlabel('Etiqueta')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Guardar imagen
    plt.savefig(nombre_imagen, dpi=300)
    print(f"Gráfica guardada como: {os.path.abspath(nombre_imagen)}")

    # Mostrar la gráfica
    plt.show()

generar_grafica_dataset("../datasets/dataset_espanol.jsonl")
