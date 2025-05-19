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
### 4. Instalar modulos de Node
Para poder lanzar la API es necesario tener Node.js y npm instalado, para instalarlo en ubuntu:
```bash
sudo apt install nodejs npm
```
Para instalar los modulos (importante estar dentro de la carpeta del proyecto):
```bash
npm install express body-parser cors
npm fund
```

## Lanzar el proyecto

Para lanzar el proyecto, simplemente hay que activar la API y ejecutar el front:
```bash
cd api/
node api.js
```
Abrir el archivo index.html.




