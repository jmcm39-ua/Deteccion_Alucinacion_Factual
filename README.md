# Detección_Alucinación_Factual

## Configuración del entorno.

A continuación se van a mostrar los pasos a seguir para crear y configurar correctamente el entorno para poder ejecutar el detector.

### 1. Crear y activar el entorno

```bash
conda create -n detector python=3.10
conda activate detector
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Descargar modelos de SpaCy

```bash
python -m spacy download es_core_news_md
python -m spacy download en_core_web_trf
```



