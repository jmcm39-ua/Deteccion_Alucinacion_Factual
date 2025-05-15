import json
import matplotlib.pyplot as plt
from collections import Counter
import os
import pandas as pd
from sklearn.metrics import confusion_matrix
import seaborn as sns

def generar_grafica_dataset(ruta_archivo, ruta_guardado="../graficas/distribucion_dataset.png"):
    # Contadores
    conteo = {'FACTUAL': 0, 'NON-FACTUAL': 0}

    # Leer archivo JSONL
    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            entrada = json.loads(linea)
            etiqueta = entrada.get("label")
            if etiqueta in conteo:
                conteo[etiqueta] += 1

    # Datos
    etiquetas = list(conteo.keys())
    valores = list(conteo.values())
    colores = ['#AEC6CF', '#CBAACB']  # Azul pastel y lila pastel

    # Crear gráfico
    plt.figure(figsize=(6, 4))
    barras = plt.bar(etiquetas, valores, color=colores)

    # Añadir números sobre las barras
    for barra in barras:
        altura = barra.get_height()
        plt.text(barra.get_x() + barra.get_width()/2, altura + 1, str(altura), ha='center', va='bottom', fontsize=12)

    # Estética
    plt.title("Distribución de oraciones", fontsize=13)
    plt.ylabel("Número de ejemplos", fontsize=12)
    plt.grid(False)  # Eliminar líneas de cuadrícula
    plt.tick_params(axis='y', left=False)  # Sin marcas en eje y
    plt.box(False)  # Sin borde alrededor de la figura

    # Guardar y mostrar
    plt.tight_layout()
    plt.savefig(ruta_guardado)
    plt.close()
    print(f"Gráfico guardado como '{ruta_guardado}'")

def analizar_extraccion_sujetos(path):
    correctos = 0
    errores = 0
    errores_sin_sujeto = 0
    errores_sin_qid = 0

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            dato = json.loads(line)
            estado = dato.get("estado")
            sujeto = dato.get("sujeto")
            qid = dato.get("qid")

            if estado == "correct":
                correctos += 1
            else:
                errores += 1
                if sujeto is None or sujeto == "(ignorar)":
                    errores_sin_sujeto += 1
                elif qid is None:
                    errores_sin_qid += 1

    # Gráfico 1: Correctos vs Errores
    etiquetas1 = ["Correctos", "Errores"]
    valores1 = [correctos, errores]
    colores1 = ['#b0eacb', '#ffdab9'] 

    plt.figure(figsize=(6, 4))
    barras1 = plt.bar(etiquetas1, valores1, color=colores1)
    for i, v in enumerate(valores1):
        plt.text(i, v + 2, str(v), ha='center', va='bottom', fontsize=10)
    plt.title("Distribución de oraciones correctas vs errores")
    plt.grid(False)
    plt.box(False)
    plt.savefig("../graficas/grafico_correctos_errores_open.png")
    plt.close()

    # Gráfico 2: Tipos de error
    etiquetas2 = ["Sin sujeto", "Sin QID"]
    valores2 = [errores_sin_sujeto, errores_sin_qid]
    colores2 = ['#ffd1dc', '#cbaacb']  # Rosa pastel y azul claro pastel

    plt.figure(figsize=(6, 4))
    barras2 = plt.bar(etiquetas2, valores2, color=colores2)
    for i, v in enumerate(valores2):
        plt.text(i, v + 2, str(v), ha='center', va='bottom', fontsize=10)
    plt.title("Errores por tipo en la extracción")
    plt.grid(False)
    plt.box(False)
    plt.savefig("../graficas/grafico_errores_tipo_open.png")
    plt.close()

def generar_matriz_confusion(archivo,salida):
    # Cargar datos desde JSONL
    datos = []
    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            datos.append(json.loads(linea))

    # Convertir a DataFrame
    df = pd.DataFrame(datos)

    # Obtener etiquetas reales y predichas
    y_true = df["resultado_correcto"]
    y_pred = df["prediccion"].map({
        "contradiction": "NON-FACTUAL",
        "neutral": "NON-FACTUAL",
        "entailment": "FACTUAL"
    })

    # Generar matriz de confusión
    labels = ["FACTUAL", "NON-FACTUAL"]
    matriz = confusion_matrix(y_true, y_pred, labels=labels)

    # Crear heatmap
    plt.figure(figsize=(6, 4))
    sns.heatmap(matriz, annot=True, fmt="d", cmap="Pastel1", xticklabels=labels, yticklabels=labels)
    plt.xlabel("Predicción del modelo")
    plt.ylabel("Etiqueta real")
    plt.title("Matriz de confusión: detección de alucinaciones factuales")
    plt.tight_layout()
    plt.savefig(salida, dpi=300)
    plt.close()

    

def generar_grafica_comparacion_resultados(archivo, salida):
    datos = []
    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            datos.append(json.loads(linea))

    df = pd.DataFrame(datos)
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax1 = axes[0]
    sns.countplot(ax=ax1, data=df, x='resultado_correcto', palette='pastel')
    ax1.set_title('Distribución de clases reales')
    ax1.set_xlabel('Clase')
    ax1.set_ylabel('Frecuencia')

    for p in ax1.patches:
        height = p.get_height()
        ax1.annotate(f'{int(height)}', 
                     (p.get_x() + p.get_width() / 2., height),
                     ha='center', va='bottom',
                     fontsize=10, color='black')

    ax2 = axes[1]
    sns.countplot(ax=ax2, data=df, x='prediccion', palette='pastel')
    ax2.set_title('Distribución de clases predichas')
    ax2.set_xlabel('Clase')
    ax2.set_ylabel('Frecuencia')

    for p in ax2.patches:
        height = p.get_height()
        ax2.annotate(f'{int(height)}', 
                     (p.get_x() + p.get_width() / 2., height),
                     ha='center', va='bottom',
                     fontsize=10, color='black')

    plt.tight_layout()
    plt.savefig(salida, dpi=300)
    plt.close()

def es_correcto(row):
    # Correcto si:
    # prediccion == 'contradiction' y resultado_correcto == 'non-factual'
    # o prediccion == 'entailment' y resultado_correcto == 'factual'
    if (row['prediccion'] == 'contradiction' and row['resultado_correcto'] == 'NON-FACTUAL'):
        return True
    if (row['prediccion'] == 'entailment' and row['resultado_correcto'] == 'FACTUAL'):
        return True
    return False

def generar_graficas_confianza_separadas(archivo, salida):
    datos = []
    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            datos.append(json.loads(linea))

    # Convertir a DataFrame
    df = pd.DataFrame(datos)

    # Extraer la confianza máxima de la lista en cada fila
    df['confianza_max'] = df['confianza'].apply(lambda x: max(x) if isinstance(x, list) and x else 0)

    # Crear columna para saber si la predicción fue correcta o no
    df['correcto'] = df.apply(es_correcto, axis=1)

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    # Histograma para predicciones correctas
    sns.histplot(df[df['correcto']]['confianza_max'], bins=20, kde=True, color='green', ax=axes[0])
    axes[0].set_title('Confianza en Predicciones Correctas')
    axes[0].set_xlabel('Confianza máxima')
    axes[0].set_ylabel('Frecuencia')
    axes[0].set_xlim(0, 1)

    # Histograma para predicciones incorrectas
    sns.histplot(df[~df['correcto']]['confianza_max'], bins=20, kde=True, color='red', ax=axes[1])
    axes[1].set_title('Confianza en Predicciones Incorrectas')
    axes[1].set_xlabel('Confianza máxima')
    axes[1].set_xlim(0, 1)

    plt.tight_layout()
    plt.savefig(salida, dpi=300)
    plt.close()

#generar_grafica_dataset("../datasets/dataset_espanol.jsonl")
#analizar_extraccion_sujetos("../resultados_pruebas/sujetos_openai.jsonl")
generar_matriz_confusion("../resultados_pruebas/benchmark_openai.jsonl","../graficas/confusion_openai.png")
generar_grafica_comparacion_resultados("../resultados_pruebas/benchmark_openai.jsonl","../graficas/comparacion_openai.png")
generar_graficas_confianza_separadas("../resultados_pruebas/benchmark_openai.jsonl","../graficas/confianza_openai.png")

