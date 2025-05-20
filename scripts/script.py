import spacy
from transformers import AutoTokenizer, AutoModelForSequenceClassification, MarianMTModel, MarianTokenizer
import torch
from difflib import get_close_matches
from huggingface_hub import login
import requests
from difflib import get_close_matches
import sys
import json
import re
import warnings
from openai_service import extraer_sujeto_openai
warnings.filterwarnings("ignore")
from transformers.utils import logging
logging.set_verbosity_error()



# Modelos spacy para detección sujetos
nlp = spacy.load("es_core_news_md")
nlp_en = spacy.load("en_core_web_trf")

# Modelo traducción inglés
modelo_trad = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-es-en")
tokenizer_trad = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-es-en")

# Modelo NLI
modelo_nli = AutoModelForSequenceClassification.from_pretrained("roberta-large-mnli")
tokenizer_nli = AutoTokenizer.from_pretrained("roberta-large-mnli")

#Función para traducir de español a inglés
def traducir_es_en(texto):
    inputs = tokenizer_trad([texto], return_tensors="pt", truncation=True, padding=True)
    translated = modelo_trad.generate(**inputs)
    return tokenizer_trad.decode(translated[0], skip_special_tokens=True)

#Función de extracción de oraciones
def dividir_en_oraciones(texto):
    doc = nlp(texto)
    return [sent.text.strip() for sent in doc.sents]

#Función de extracción de keywords
def extraer_keywords(oracion):
    doc = nlp(oracion)
    return [ent.text for ent in doc.ents if ent.label_ in {"PER", "ORG", "LOC", "MISC"}]


#Función de extracción de sujeto
def extraer_sujeto(oracion):
    doc_es = nlp(oracion)
    
    entidades_es = [ent.text for ent in doc_es.ents if ent.label_ in {"PER", "ORG"}]
    if entidades_es:
        return entidades_es[0]

    doc_en = nlp_en(oracion)
    
    entidades_en = [ent.text for ent in doc_en.ents if ent.label_ in {"PER", "ORG"}]
    if entidades_en:
        return entidades_en[0]

    for token in doc_es:
        if token.dep_ in {"nsubj", "nsubj:pass"}:
            # Devuelve el sujeto sin modificadores
            sujeto = " ".join([w.text for w in token.subtree])
            # Filtro de palabras comunes
            filtros = {"el", "la", "los", "las", "un", "una", "unos", "unas", "este", "ese", "poeta", "presidente", "doctor", "profesor"}
            palabras = [p for p in sujeto.split() if p.lower() not in filtros]
            return " ".join(palabras)

    return None

#Función de búsqueda de entidades
def buscar_entidad_wikidata(nombre):
    #print(f"Buscando entidad en Wikidata para: {nombre}")
        
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={nombre}&language=es&format=json"
    response = requests.get(url)
    data = response.json()

    if 'search' in data and data['search']:
        best_match = data['search'][0]
        entity_id = best_match['id']
        label = best_match['label']
        
        url_entity = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={entity_id}&sites=wikidata&props=descriptions&languages=es&format=json"
        response_entity = requests.get(url_entity)
        data_entity = response_entity.json()

        description = data_entity.get('entities', {}).get(entity_id, {}).get('descriptions', {}).get('es', {}).get('value', 'Descripción no disponible')

        #print(f"Entidad encontrada: {label} ({entity_id})")
        return entity_id, label, description
    
    return None, None, None

# Función de obtención de tipos de la entidad
def obtener_tipo_entidad(qid):
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid}&sites=wikidata&props=claims&format=json"
        response = requests.get(url)
        data = response.json()
        
        if 'entities' not in data or qid not in data['entities']:
            #print(f"No se encontraron datos para el QID: {qid}")
            return []

        claims = data.get("entities", {}).get(qid, {}).get("claims", {})

        if "P31" in claims:
            tipos = [c.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') for c in claims["P31"]]
            #print(f"Tipos para {qid}: {tipos}")
            return tipos

        return []
    except Exception as e:
        #print(f"Error al obtener tipo de entidad: {e}")
        return []
    
#Función de obtención de label
def obtener_label(QID, idioma='es'):
    try:
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{QID}.json"
        response = requests.get(url)
        data = response.json()
        entity = data['entities'][QID]
        labels = entity['labels']
        return labels.get(idioma, {}).get('value', QID)
    except:
        return QID

#Función de obtención de fechas
def obtener_fecha_publicacion(qid_obra):
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid_obra}&format=json&props=claims"
    response = requests.get(url)
    data = response.json()
    claims = data.get('entities', {}).get(qid_obra, {}).get('claims', {})
    if 'P577' in claims:
        fecha = claims['P577'][0].get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('time', '')
        return fecha
    return None

#Función de obtención de hechos
def recuperar_hechos(qid):
    try:
        #print(f"Recuperando hechos para la entidad: {qid}")

        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid}&sites=wikidata&props=claims|descriptions&format=json"
        response = requests.get(url)
        data = response.json()
        entity_data = data.get('entities', {}).get(qid, {}).get('claims', {})
        entity = data.get('entities', {}).get(qid, {})

        hechos = []

        # Descripción corta
        descripcion_corta = entity.get('descriptions', {}).get('es', {}).get('value', '')
        if descripcion_corta:
            hechos.append(f"{descripcion_corta}.")

        propiedades = {
            # Personas
            'P106': 'Ocupación',
            'P166': 'Premio recibido',
            'P19': 'Lugar de nacimiento',
            'P20': 'Lugar de fallecimiento',
            'P569': 'Fecha de nacimiento',
            'P570': 'Fecha de fallecimiento',
            'P800': 'Obra destacada',
            'P27': 'Nacionalidad',
            'P39': 'Cargo o posición',
            'P69': 'Educación',
            'P26': 'Cónyuge',
            'P22': 'Padre',
            'P25': 'Madre',
            'P734': 'Apellido',
            'P735': 'Nombre de pila',
            'P161': 'Películas en las que ha actuado',
            'P175': 'Intérprete',
            'P3095': 'Personaje interpretado',
            'P108': 'Empleado en',

            # Películas / Producciones audiovisuales
            'P57': 'Director',
            'P58': 'Guionista',
            'P161': 'Reparto',
            'P272': 'Productora',
            'P364': 'Idioma original',
            'P577': 'Fecha de publicación/estreno',
            'P1040': 'Editor',
            'P2130': 'Costo de producción',
            'P2142': 'Ingresos brutos',
            'P1476': 'Título oficial',

            # Libros / Obras
            'P50': 'Autor',
            'P577': 'Fecha de publicación',
            'P110': 'Ilustrador',
            'P291': 'Lugar de publicación',
            'P364': 'Idioma de la obra',
            'P1476': 'Título oficial',
            'P1680': 'Descripción corta',
            'P123': 'Editorial',
            'P655': 'Título original',
            'P98': 'Editor literario',

            # Organizaciones / Empresas
            'P112': 'Fundador',
            'P159': 'Sede',
            'P571': 'Fecha de fundación',
            'P452': 'Industria',
            'P1454': 'Accionista',
            'P127': 'Propietario',
            'P749': 'Empresa matriz',
            'P1128': 'Empleados',
            'P2139': 'Recuento de ingresos',
            'P2403': 'Autoridad reguladora',

            # Lugares
            'P17': 'País',
            'P131': 'Ubicación administrativa',
            'P625': 'Coordenadas',
            'P2046': 'Área',
            'P1082': 'Población',
            'P856': 'Página web oficial',
            'P1448': 'Nombre oficial',
            'P1464': 'Categoría de patrimonio',

            # Objetos astronómicos / Planetas
            'P2583': 'Clase espectral',
            'P2120': 'Gravedad superficial',
            'P2067': 'Masa',
            'P2050': 'Órbita',
            'P2146': 'Diámetro',
            'P3984': 'Órbita de',
            'P3996': 'Luna de',
            'P376': 'Órbita alrededor de',
            'P625': 'Coordenadas celestes',
            'P59': 'Constelación',

            # Relaciones / colaboraciones / composición
            'P361': 'Parte de',
            'P527': 'Tiene como parte',
            'P176': 'Fabricante',
            'P137': 'Patrocinado por',
            'P710': 'Participante',
            'P155': 'Predecesor',
            'P156': 'Sucesor',
            'P144': 'Basado en',
            'P50': 'Autor de la obra',
            'P629': 'Versión o edición de',

            # Deportes (por si aparecen atletas)
            'P54': 'Miembro de equipo deportivo',
            'P1350': 'Número de victorias',
            'P1351': 'Número de derrotas',
            'P641': 'Deporte practicado',

            # Música
            'P676': 'Número de catálogo',
            'P435': 'ID MusicBrainz',

            # Tecnología / Software
            'P178': 'Desarrollador',
            'P348': 'Versión',
            'P275': 'Licencia',
            'P1072': 'Sitio web oficial del software',

            # Cultura / Historia
            'P128': 'Lugar de exposición',
            'P573': 'Período histórico',
            'P2189': 'Proyecto artístico',

            # Biología / Ciencia
            'P27': 'Especie',
            'P2219': 'Organismo relacionado',
            'P2313': 'Función biológica',
            'P679': 'Propiedades genéticas',

            # Vehículos / Transportes
            'P414': 'Compañía aérea',
            'P1098': 'Propietario del vehículo',
            'P3407': 'Tipo de transporte',

            # Construcción / Arquitectura
            'P279': 'Tipo de edificio',
            'P152': 'Material de construcción',
            'P3179': 'Arquitecto',

            # Alimentos
            'P476': 'Ingrediente principal',
            'P2067': 'Método de preparación',

            # Medio ambiente / Naturaleza
            'P720': 'Habita en',
            'P1632': 'Requiere',

            # Invenciones
            'P1799': 'Nombre del invento',
            'P3504': 'Patente',

            
        }


        for pid, descripcion in propiedades.items():
            if pid in entity_data:
                for item in entity_data[pid]:
                    mainsnak = item.get('mainsnak', {})
                    datavalue = mainsnak.get('datavalue', {}).get('value', {})

                    # Identificadores de entidad (QIDs)
                    if isinstance(datavalue, dict) and 'id' in datavalue:
                        qid = datavalue['id']
                        etiqueta = obtener_label(qid)
                        texto = f"{descripcion}: {etiqueta}"

                        # Fecha asociada al premio
                        if pid == 'P166':
                            qualifiers = item.get('qualifiers', {})
                            if 'P585' in qualifiers:
                                fecha_val = qualifiers['P585'][0].get('datavalue', {}).get('value', {}).get('time', '')
                                if fecha_val:
                                    texto += f" (fecha: {fecha_val[1:11]})"  # Quitar el signo +

                        # Fecha de publicación de obra destacada
                        elif pid == 'P800':
                            fecha_pub = obtener_fecha_publicacion(qid)
                            if fecha_pub:
                                texto += f" (fecha: {fecha_pub[1:11]})"

                        hechos.append(texto)

                    # Fechas puras (como P569, P570)
                    elif isinstance(datavalue, dict) and 'time' in datavalue:
                        fecha = datavalue['time'][1:11]
                        hechos.append(f"{descripcion}: {fecha}")

                    # Strings simples
                    elif isinstance(datavalue, str):
                        hechos.append(f"{descripcion}: {datavalue}")

        return hechos

    except Exception as e:
        #print(f"Error al recuperar hechos: {e}")
        return []

# Función para resolver QIDs a etiquetas
def resolver_qids(qids):
    etiquetas = {}
    if not qids:
        return etiquetas

    ids_str = "|".join(set(qids))
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={ids_str}&format=json&props=labels&languages=es"
    response = requests.get(url)
    data = response.json()

    for qid, info in data.get('entities', {}).items():
        etiqueta = info.get('labels', {}).get('es', {}).get('value', 'Desconocido')
        etiquetas[qid] = etiqueta

    return etiquetas
    


def generar_oracion_resumen_con_etiquetas(nombre, hechos, tipos_etiquetas):

    # Resolver etiquetas de hechos
    qids = re.findall(r'Q\d+', " ".join(hechos))
    etiquetas = resolver_qids(qids)

    # Resolver etiquetas de tipos
    tipos_qids = [t for t in tipos_etiquetas if t.startswith("Q")]
    etiquetas_tipos = resolver_qids(tipos_qids)
    tipos_legibles = [etiquetas_tipos.get(t, t) for t in tipos_etiquetas]

    # Reemplazar QIDs en los hechos
    hechos_legibles = []
    for h in hechos:
        for q in qids:
            if q in h:
                h = h.replace(q, etiquetas.get(q, q))
        hechos_legibles.append(h)

    resumen = f"Según Wikidata, {nombre}"

    # Clasificación por tipo de propiedad
    def extraer(prop): return [h for h in hechos_legibles if h.startswith(prop)]
    def extraer_valor(prop): return [h.replace(f"{prop}: ", "") for h in hechos_legibles if h.startswith(prop)]

    partes = []

    descripcion = [h for h in hechos_legibles if h.endswith(".") and not ":" in h]
    if descripcion:
        partes.append(descripcion[0].rstrip("."))
    if tipos_legibles:
        partes.append(f"es {', '.join(set(tipos_legibles))}")

    # Datos personales
    ocup = extraer_valor("Ocupación")
    #premio = extraer_valor("Premio recibido")
    nac = extraer("Fecha de nacimiento")
    lugar_nac = extraer_valor("Lugar de nacimiento")
    falle = extraer("Fecha de fallecimiento")
    lugar_falle = extraer_valor("Lugar de fallecimiento")
    nacionalidad = extraer_valor("Nacionalidad")
    educacion = extraer_valor("Educación")
    conyuge = extraer_valor("Cónyuge")
    padre = extraer_valor("Padre")
    madre = extraer_valor("Madre")
    cargo = extraer_valor("Cargo o posición")
    apellido = extraer_valor("Apellido")
    nombre_pila = extraer_valor("Nombre de pila")
    peliculas = extraer_valor("Películas en las que ha actuado")
    interprete = extraer_valor("Intérprete")
    personaje = extraer_valor("Personaje interpretado")
    #obra = extraer_valor("Obra destacada")
    companias = extraer_valor("Empleado en") 

    # Información de nacimiento
    if lugar_nac and nac:
        partes.append(f"nació en {', '.join(set(lugar_nac))} el {nac[0].replace('Fecha de nacimiento: +', '').split('T')[0]}")

    # Información de fallecimiento
    if lugar_falle and falle:
        partes.append(f"falleció en {', '.join(set(lugar_falle))} el {falle[0].replace('Fecha de fallecimiento: +', '').split('T')[0]}")

    # Información de nacionalidad
    if nacionalidad:
        partes.append(f"de nacionalidad {', '.join(set(nacionalidad))}")

    # Información de educación
    if educacion:
        partes.append(f"estudió en {', '.join(set(educacion))}")

    # Información de cónyuge
    if conyuge:
        partes.append(f"su cónyuge es {', '.join(set(conyuge))}")

    # Información de los padres
    if padre or madre:
        parentesco = []
        if padre: parentesco.append(f"padre: {', '.join(set(padre))}")
        if madre: parentesco.append(f"madre: {', '.join(set(madre))}")
        partes.append("tiene como " + " y ".join(parentesco))

    # Información de ocupación
    if ocup:
        partes.append(f"fue {', '.join(set(ocup))}")

    # Información de cargos
    if cargo:
        partes.append(f"ocupó cargos como {', '.join(set(cargo))}")

    # Información sobre apellidos y nombres
    if apellido or nombre_pila:
        nombres = []
        if apellido: nombres.append(f"apellido: {', '.join(set(apellido))}")
        if nombre_pila: nombres.append(f"nombre de pila: {', '.join(set(nombre_pila))}")
        partes.append("con " + " y ".join(nombres))

    # Información sobre películas y personajes interpretados
    if peliculas or interprete or personaje:
        peliculas_info = []
        if peliculas: peliculas_info.append(f"actuó en películas como {', '.join(set(peliculas))}")
        if interprete: peliculas_info.append(f"fue intérprete de {', '.join(set(interprete))}")
        if personaje: peliculas_info.append(f"interpretó personajes como {', '.join(set(personaje))}")
        partes.append(" ".join(peliculas_info))

# Premios con fechas completas
    premios = [h for h in hechos_legibles if h.startswith("Premio recibido")]
    premios_format = []
    for p in premios:
        if "@" in p:
            nombre, fecha = p.split("@")
            nombre = nombre.replace("Premio recibido: ", "").strip()
            premios_format.append(f"{nombre} en {fecha}")
        else:
            premios_format.append(p.replace("Premio recibido: ", ""))
    if premios_format:
        partes.append(f"recibió premios como {', '.join(set(premios_format))}")

    # Obras con fechas completas
    obras = [h for h in hechos_legibles if h.startswith("Obra destacada")]
    obras_format = []
    for o in obras:
        if "@" in o:
            nombre, fecha = o.split("@")
            nombre = nombre.replace("Obra destacada: ", "").strip()
            obras_format.append(f"{nombre} en {fecha}")
        else:
            obras_format.append(o.replace("Obra destacada: ", ""))
    if obras_format:
        partes.append(f"es conocido por obras como {', '.join(set(obras_format))}")

    if companias:
        partes.append(f"trabajó en {', '.join(set(companias))}")

    
    # Datos de producciones audiovisuales
    director = extraer_valor("Director")
    guionista = extraer_valor("Guionista")
    reparto = extraer_valor("Reparto")
    productora = extraer_valor("Productora")
    idioma_original = extraer_valor("Idioma original")
    fecha_estreno = extraer("Fecha de publicación/estreno")
    compositor = extraer_valor("Compositor")
    editor = extraer_valor("Editor")
    costo_produccion = extraer_valor("Costo de producción")
    ingresos_brutos = extraer_valor("Ingresos brutos")
    titulo_oficial = extraer_valor("Título oficial")

    # Información de director
    if director:
        partes.append(f"dirigido por {', '.join(set(director))}")

    # Información de guionista
    if guionista:
        partes.append(f"escrito por {', '.join(set(guionista))}")

    # Información de reparto
    if reparto:
        partes.append(f"con la participación de {', '.join(set(reparto))}")

    # Información de productora
    if productora:
        partes.append(f"producido por {', '.join(set(productora))}")

    # Información de idioma original
    if idioma_original:
        partes.append(f"en idioma original {', '.join(set(idioma_original))}")

    # Información de fecha de estreno
    if fecha_estreno:
        partes.append(f"estrenado el {fecha_estreno[0].replace('Fecha de publicación/estreno: +', '').split('T')[0]}")

    # Información de compositor
    if compositor:
        partes.append(f"con música de {', '.join(set(compositor))}")

    # Información de editor
    if editor:
        partes.append(f"editado por {', '.join(set(editor))}")

    # Información de costo de producción
    if costo_produccion:
        partes.append(f"con un costo de producción de {', '.join(set(costo_produccion))}")

    # Información de ingresos brutos
    if ingresos_brutos:
        partes.append(f"y unos ingresos brutos de {', '.join(set(ingresos_brutos))}")

    # Información de título oficial
    if titulo_oficial:
        partes.append(f"con el título oficial {', '.join(set(titulo_oficial))}")

    # Datos de libros y obras
    autor = extraer_valor("Autor")
    fecha_publicacion = extraer("Fecha de publicación")
    ilustrador = extraer_valor("Ilustrador")
    lugar_publicacion = extraer_valor("Lugar de publicación")
    idioma_obra = extraer_valor("Idioma de la obra")
    titulo_oficial_obra = extraer_valor("Título oficial")
    descripcion_corta = extraer_valor("Descripción corta")
    editorial = extraer_valor("Editorial")
    titulo_original = extraer_valor("Título original")
    editor_literario = extraer_valor("Editor literario")

    # Información de autor
    if autor:
        partes.append(f"escrito por {', '.join(set(autor))}")

    # Información de fecha de publicación
    if fecha_publicacion:
        partes.append(f"publicado el {fecha_publicacion[0].replace('Fecha de publicación: +', '').split('T')[0]}")

    # Información de ilustrador
    if ilustrador:
        partes.append(f"con ilustraciones de {', '.join(set(ilustrador))}")

    # Información de lugar de publicación
    if lugar_publicacion:
        partes.append(f"publicado en {', '.join(set(lugar_publicacion))}")

    # Información de idioma de la obra
    if idioma_obra:
        partes.append(f"en el idioma {', '.join(set(idioma_obra))}")

    # Información de título oficial
    if titulo_oficial_obra:
        partes.append(f"con el título oficial {', '.join(set(titulo_oficial_obra))}")

    # Información de descripción corta
    if descripcion_corta:
        partes.append(f"su descripción corta es: {', '.join(set(descripcion_corta))}")

    # Información de editorial
    if editorial:
        partes.append(f"publicado por {', '.join(set(editorial))}")

    # Información de título original
    if titulo_original:
        partes.append(f"con el título original {', '.join(set(titulo_original))}")

    # Información de editor literario
    if editor_literario:
        partes.append(f"editado por {', '.join(set(editor_literario))}")

    # Datos de organizaciones y empresas
    fundador = extraer_valor("Fundador")
    sede = extraer_valor("Sede")
    fecha_fundacion = extraer("Fecha de fundación")
    industria = extraer_valor("Industria")
    accionista = extraer_valor("Accionista")
    propietario = extraer_valor("Propietario")
    empresa_matriz = extraer_valor("Empresa matriz")
    empleados = extraer_valor("Empleados")
    recuento_ingresos = extraer_valor("Recuento de ingresos")
    autoridad_reguladora = extraer_valor("Autoridad reguladora")

    # Información de fundador
    if fundador:
        partes.append(f"fundada por {', '.join(set(fundador))}")

    # Información de sede
    if sede:
        partes.append(f"su sede se encuentra en {', '.join(set(sede))}")

    # Información de fecha de fundación
    if fecha_fundacion:
        partes.append(f"fundada el {fecha_fundacion[0].replace('Fecha de fundación: +', '').split('T')[0]}")

    # Información de industria
    if industria:
        partes.append(f"pertenece a la industria de {', '.join(set(industria))}")

    # Información de accionistas
    if accionista:
        partes.append(f"con accionistas como {', '.join(set(accionista))}")

    # Información de propietario
    if propietario:
        partes.append(f"es propiedad de {', '.join(set(propietario))}")

    # Información de empresa matriz
    if empresa_matriz:
        partes.append(f"forma parte del grupo {', '.join(set(empresa_matriz))}")

    # Información de empleados
    if empleados:
        partes.append(f"emplea a {', '.join(set(empleados))}")

    # Información de recuento de ingresos
    if recuento_ingresos:
        partes.append(f"con un recuento de ingresos de {', '.join(set(recuento_ingresos))}")

    # Información de autoridad reguladora
    if autoridad_reguladora:
        partes.append(f"y está regulada por {', '.join(set(autoridad_reguladora))}")

    # Lugar
    pais = extraer_valor("País")
    ubicacion_administrativa = extraer_valor("Ubicación administrativa")
    coordenadas = extraer_valor("Coordenadas")
    area = extraer_valor("Área")
    poblacion = extraer_valor("Población")
    pagina_web = extraer_valor("Página web oficial")
    nombre_oficial = extraer_valor("Nombre oficial")
    categoria_patrimonio = extraer_valor("Categoría de patrimonio")

    # Información de país
    if pais:
        partes.append(f"se encuentra en {', '.join(set(pais))}")

    # Información de ubicación administrativa
    if ubicacion_administrativa:
        partes.append(f"ubicado en la {', '.join(set(ubicacion_administrativa))}")

    # Información de coordenadas
    if coordenadas:
        partes.append(f"con coordenadas {', '.join(set(coordenadas))}")

    # Información de área
    if area:
        partes.append(f"con un área de {', '.join(set(area))} km²")

    # Información de población
    if poblacion:
        partes.append(f"con una población de {', '.join(set(poblacion))}")

    # Información de página web
    if pagina_web:
        partes.append(f"su página web oficial es {', '.join(set(pagina_web))}")

    # Información de nombre oficial
    if nombre_oficial:
        partes.append(f"su nombre oficial es {', '.join(set(nombre_oficial))}")

    # Información de categoría de patrimonio
    if categoria_patrimonio:
        partes.append(f"y está clasificado como {', '.join(set(categoria_patrimonio))} en términos de patrimonio")

    # Datos astronómicos
    clase_espectral = extraer_valor("Clase espectral")
    gravedad_superficial = extraer_valor("Gravedad superficial")
    masa = extraer_valor("Masa")
    orbita = extraer_valor("Órbita")
    diametro = extraer_valor("Diámetro")
    orbita_de = extraer_valor("Órbita de")
    luna_de = extraer_valor("Luna de")
    orbita_alrededor_de = extraer_valor("Órbita alrededor de")
    coordenadas_celestes = extraer_valor("Coordenadas celestes")
    constelacion = extraer_valor("Constelación")

    # Información de clase espectral
    if clase_espectral:
        partes.append(f"su clase espectral es {', '.join(set(clase_espectral))}")

    # Información de gravedad superficial
    if gravedad_superficial:
        partes.append(f"su gravedad superficial es de {', '.join(set(gravedad_superficial))} m/s²")

    # Información de masa
    if masa:
        partes.append(f"su masa es {', '.join(set(masa))} kg")

    # Información de órbita
    if orbita:
        partes.append(f"su órbita es {', '.join(set(orbita))}")

    # Información de diámetro
    if diametro:
        partes.append(f"su diámetro es de {', '.join(set(diametro))} km")

    # Información de órbita de
    if orbita_de:
        partes.append(f"orbita alrededor de {', '.join(set(orbita_de))}")

    # Información de luna de
    if luna_de:
        partes.append(f"es luna de {', '.join(set(luna_de))}")

    # Información de órbita alrededor de
    if orbita_alrededor_de:
        partes.append(f"orbita alrededor de {', '.join(set(orbita_alrededor_de))}")

    # Información de coordenadas celestes
    if coordenadas_celestes:
        partes.append(f"sus coordenadas celestes son {', '.join(set(coordenadas_celestes))}")

    # Información de constelación
    if constelacion:
        partes.append(f"pertenece a la constelación de {', '.join(set(constelacion))}")

    # Datos de relaciones y colaboraciones
    parte_de = extraer_valor("Parte de")
    tiene_como_parte = extraer_valor("Tiene como parte")
    fabricante = extraer_valor("Fabricante")
    patrocinado_por = extraer_valor("Patrocinado por")
    participante = extraer_valor("Participante")
    predecesor = extraer_valor("Predecesor")
    sucesor = extraer_valor("Sucesor")
    basado_en = extraer_valor("Basado en")
    autor_obra = extraer_valor("Autor de la obra")
    version_edicion = extraer_valor("Versión o edición de")

    # Información de parte de
    if parte_de:
        partes.append(f"es parte de {', '.join(set(parte_de))}")

    # Información de tiene como parte
    if tiene_como_parte:
        partes.append(f"tiene como parte {', '.join(set(tiene_como_parte))}")

    # Información de fabricante
    if fabricante:
        partes.append(f"fue fabricado por {', '.join(set(fabricante))}")

    # Información de patrocinado por
    if patrocinado_por:
        partes.append(f"fue patrocinado por {', '.join(set(patrocinado_por))}")

    # Información de participante
    if participante:
        partes.append(f"participó en {', '.join(set(participante))}")

    # Información de predecesor
    if predecesor:
        partes.append(f"su predecesor fue {', '.join(set(predecesor))}")

    # Información de sucesor
    if sucesor:
        partes.append(f"su sucesor fue {', '.join(set(sucesor))}")

    # Información de basado en
    if basado_en:
        partes.append(f"está basado en {', '.join(set(basado_en))}")

    # Información de autor de la obra
    if autor_obra:
        partes.append(f"fue obra de {', '.join(set(autor_obra))}")

    # Información de versión o edición de
    if version_edicion:
        partes.append(f"es una versión o edición de {', '.join(set(version_edicion))}")

    # Datos de deportes
    miembro_equipo = extraer_valor("Miembro de equipo deportivo")
    numero_victorias = extraer_valor("Número de victorias")
    numero_derrotas = extraer_valor("Número de derrotas")
    deporte_practicado = extraer_valor("Deporte practicado")

    # Información de miembro de equipo deportivo
    if miembro_equipo:
        partes.append(f"fue miembro de {', '.join(set(miembro_equipo))}")

    # Información de número de victorias
    if numero_victorias:
        partes.append(f"tiene {', '.join(set(numero_victorias))} victorias")

    # Información de número de derrotas
    if numero_derrotas:
        partes.append(f"y {', '.join(set(numero_derrotas))} derrotas")

    # Información de deporte practicado
    if deporte_practicado:
        partes.append(f"practicó {', '.join(set(deporte_practicado))}")

    # Datos musicales
    numero_catalogo = extraer_valor("Número de catálogo")
    id_musicbrainz = extraer_valor("ID MusicBrainz")

    # Información de número de catálogo
    if numero_catalogo:
        partes.append(f"su número de catálogo es {', '.join(set(numero_catalogo))}")

    # Información de ID MusicBrainz
    if id_musicbrainz:
        partes.append(f"su ID en MusicBrainz es {', '.join(set(id_musicbrainz))}")

    # Datos de tecnología/software
    desarrollador = extraer_valor("Desarrollador")
    version = extraer_valor("Versión")
    licencia = extraer_valor("Licencia")
    sitio_web = extraer_valor("Sitio web oficial del software")

    # Información de desarrollador
    if desarrollador:
        partes.append(f"fue desarrollado por {', '.join(set(desarrollador))}")

    # Información de versión
    if version:
        partes.append(f"su versión es {', '.join(set(version))}")

    # Información de licencia
    if licencia:
        partes.append(f"su licencia es {', '.join(set(licencia))}")

    # Información de sitio web oficial
    if sitio_web:
        partes.append(f"su sitio web oficial es {', '.join(set(sitio_web))}")

    # Cultura / Historia
    lugar_exposicion = extraer_valor("Lugar de exposición")
    periodo_historico = extraer_valor("Período histórico")
    proyecto_artistico = extraer_valor("Proyecto artístico")

    # Biología / Ciencia
    especie = extraer_valor("Especie")
    organismo_relacionado = extraer_valor("Organismo relacionado")
    funcion_biologica = extraer_valor("Función biológica")
    propiedades_geneticas = extraer_valor("Propiedades genéticas")

    # Información de lugar de exposición
    if lugar_exposicion:
        partes.append(f"se expuso en {', '.join(set(lugar_exposicion))}")

    # Información de período histórico
    if periodo_historico:
        partes.append(f"pertenece al período histórico de {', '.join(set(periodo_historico))}")

    # Información de proyecto artístico
    if proyecto_artistico:
        partes.append(f"fue parte del proyecto artístico {', '.join(set(proyecto_artistico))}")

    # Información de especie
    if especie:
        partes.append(f"pertenece a la especie {', '.join(set(especie))}")

    # Información de organismo relacionado
    if organismo_relacionado:
        partes.append(f"está relacionado con {', '.join(set(organismo_relacionado))}")

    # Información de función biológica
    if funcion_biologica:
        partes.append(f"su función biológica es {', '.join(set(funcion_biologica))}")

    # Información de propiedades genéticas
    if propiedades_geneticas:
        partes.append(f"tiene las siguientes propiedades genéticas: {', '.join(set(propiedades_geneticas))}")

    # Vehículos / Transportes
    compania_aerea = extraer_valor("Compañía aérea")
    propietario_vehiculo = extraer_valor("Propietario del vehículo")
    tipo_transporte = extraer_valor("Tipo de transporte")

    # Construcción / Arquitectura
    tipo_edificio = extraer_valor("Tipo de edificio")
    material_construccion = extraer_valor("Material de construcción")
    arquitecto = extraer_valor("Arquitecto")

    # Alimentos
    ingrediente_principal = extraer_valor("Ingrediente principal")
    metodo_preparacion = extraer_valor("Método de preparación")

    # Información de compañía aérea
    if compania_aerea:
        partes.append(f"es operado por la compañía aérea {', '.join(set(compania_aerea))}")

    # Información de propietario del vehículo
    if propietario_vehiculo:
        partes.append(f"su propietario es {', '.join(set(propietario_vehiculo))}")

    # Información de tipo de transporte
    if tipo_transporte:
        partes.append(f"es un {', '.join(set(tipo_transporte))}")

    # Información de tipo de edificio
    if tipo_edificio:
        partes.append(f"es un tipo de edificio {', '.join(set(tipo_edificio))}")

    # Información de material de construcción
    if material_construccion:
        partes.append(f"está construido con {', '.join(set(material_construccion))}")

    # Información de arquitecto
    if arquitecto:
        partes.append(f"fue diseñado por {', '.join(set(arquitecto))}")

    # Información de ingrediente principal
    if ingrediente_principal:
        partes.append(f"su ingrediente principal es {', '.join(set(ingrediente_principal))}")

    # Información de método de preparación
    if metodo_preparacion:
        partes.append(f"su método de preparación es {', '.join(set(metodo_preparacion))}")

    # Medio ambiente / Naturaleza
    habita_en = extraer_valor("Habita en")
    requiere = extraer_valor("Requiere")

    # Invenciones
    nombre_invento = extraer_valor("Nombre del invento")
    patente = extraer_valor("Patente")

    # Información de hábitat
    if habita_en:
        partes.append(f"habita en {', '.join(set(habita_en))}")

    # Información de requisitos
    if requiere:
        partes.append(f"requiere {', '.join(set(requiere))}")

    # Información de nombre del invento
    if nombre_invento:
        partes.append(f"su invento se llama {', '.join(set(nombre_invento))}")

    # Información de patente
    if patente:
        partes.append(f"su patente es {', '.join(set(patente))}")

    resumen += ", " + ", ".join(partes) + "."

    return resumen


# Función para predecir NLI traduciendo al inglés
def predecir_nli_traducido(premisa_es, hipotesis_es):
    #print(premisa_es)
    premisa_en = traducir_es_en(premisa_es)
    #print(premisa_en)
    hipotesis_en = traducir_es_en(hipotesis_es)
    #print(hipotesis_en)

    # Hacemos predicción con el modelo NLI en inglés
    inputs = tokenizer_nli(premisa_en, hipotesis_en, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = modelo_nli(**inputs).logits
    probs = torch.softmax(logits, dim=1).squeeze().tolist()
    etiquetas = ["contradiction", "neutral", "entailment"]
    prediccion = etiquetas[torch.argmax(logits)]
    return prediccion, probs


# Función para predecir NLI con oraciones en español
def predecir_con_oracion(evidencia_es, hipotesis_es):
    pred, probs = predecir_nli_traducido(evidencia_es, hipotesis_es)
    return pred, probs

# Función para extraer oraciones de un archivo JSONL
def extraer_oraciones_jsonl(path_archivo):
    oraciones = []
    with open(path_archivo, 'r', encoding='utf-8') as archivo:
        for linea in archivo:
            if linea.strip():  # Ignorar líneas vacías
                datos = json.loads(linea)
                oracion = datos.get("claim_es")
                if oracion:
                    oraciones.append(oracion)
    return oraciones

# Función para extraer sujetos del dataset
def extraer_sujetos_prueba():
    ruta_entrada = "../datasets/dataset_espanol.jsonl"
    ruta_salida = "../resultados_pruebas/sujetos.jsonl"
    numero_oracion = 0

    oraciones = extraer_oraciones_jsonl(ruta_entrada)

    with open(ruta_salida, 'w', encoding='utf-8') as f_out:
        for oracion in oraciones:
            numero_oracion += 1
            print(f"Oracion: {numero_oracion}/2000")
            sujeto = extraer_sujeto(oracion)
            qid, label, descripcion = buscar_entidad_wikidata(sujeto) if sujeto else (None, None, None)

            estado = "correct" if sujeto and qid else "error"

            resultado = {
                "oracion": oracion,
                "sujeto": sujeto,
                "qid": qid,
                "estado": estado
            }

            f_out.write(json.dumps(resultado, ensure_ascii=False) + '\n')
            f_out.flush()

# Función para extraer sujetos del dataset usando OpenAI
def extraer_sujetos_prueba_openai():
    ruta_entrada = "../datasets/dataset_espanol.jsonl"
    ruta_salida = "../resultados_pruebas/sujetos_openai.jsonl"
    numero_oracion = 0

    oraciones = extraer_oraciones_jsonl(ruta_entrada)

    with open(ruta_salida, 'w', encoding='utf-8') as f_out:
        for oracion in oraciones:
            numero_oracion += 1
            print(f"Oracion: {numero_oracion}/2000")
            sujeto = extraer_sujeto_openai(oracion)
            qid, label, descripcion = buscar_entidad_wikidata(sujeto) if sujeto else (None, None, None)

            estado = "correct" if sujeto and qid else "error"

            resultado = {
                "oracion": oracion,
                "sujeto": sujeto,
                "qid": qid,
                "estado": estado
            }

            f_out.write(json.dumps(resultado, ensure_ascii=False) + '\n')
            f_out.flush()

# Función para combinar claims con QID
def combinar_claims_con_qid(ruta_entrada, ruta_sujetos):
    # Cargar sujetos en un diccionario para acceso rápido por oración
    sujetos_dict = {}
    with open(ruta_sujetos, 'r', encoding='utf-8') as f:
        for linea in f:
            entrada = json.loads(linea)
            sujetos_dict[entrada['oracion']] = {
                'qid': entrada['qid'],
                'sujeto': entrada['sujeto']
            }

    # Combinar datos
    combinados = []
    with open(ruta_entrada, 'r', encoding='utf-8') as f:
        for linea in f:
            entrada = json.loads(linea)
            claim = entrada['claim_es']
            label = entrada['label']
            info_sujeto = sujetos_dict.get(claim)

            if info_sujeto:  # Solo si se encontró qid y sujeto correspondiente
                combinados.append({
                    'claim_es': claim,
                    'label': label,
                    'qid': info_sujeto['qid'],
                    'sujeto': info_sujeto['sujeto']
                })

    return combinados

# Función para realizar el benchmark con SpaCy
def benchmark_con_spacy():
    ruta_entrada = "../datasets/dataset_espanol.jsonl"
    ruta_sujetos = "../resultados_pruebas/sujetos.jsonl"
    ruta_salida = "../resultados_pruebas/benchmark_spacy.jsonl"
    
    datos = combinar_claims_con_qid(ruta_entrada, ruta_sujetos)

    with open(ruta_salida, 'w', encoding='utf-8') as f_salida:
        pass  # Limpiamos el archivo antes de empezar

    for dato in datos:
        oracion = dato["claim_es"]
        resultado_correcto = dato["label"]
        qid = dato["qid"]
        sujeto = dato["sujeto"]

        print(dato)

        if qid:
            hechos = recuperar_hechos(qid)
            tipos_qids = obtener_tipo_entidad(qid)
            tipos_etiquetas = resolver_qids(tipos_qids)
            oracion_datos = generar_oracion_resumen_con_etiquetas(sujeto, hechos, tipos_etiquetas)
            pred, probs = predecir_con_oracion(oracion_datos, oracion)

            resultado = {
                "oracion": oracion,
                "entidad": sujeto,
                "oracion_creada": oracion_datos,
                "prediccion": pred,
                "confianza": probs,
                "resultado_correcto": resultado_correcto
            }

            with open(ruta_salida, 'a', encoding='utf-8') as f_salida:
                f_salida.write(json.dumps(resultado, ensure_ascii=False) + '\n')

# Función para realizar el benchmark con OpenAI
def benchmark_con_openai():
    ruta_entrada = "../datasets/dataset_espanol.jsonl"
    ruta_sujetos = "../resultados_pruebas/sujetos_openai.jsonl"
    ruta_salida = "../resultados_pruebas/benchmark_openai.jsonl"
    
    datos = combinar_claims_con_qid(ruta_entrada, ruta_sujetos)

    with open(ruta_salida, 'w', encoding='utf-8') as f_salida:
        pass  # Limpiamos el archivo antes de empezar

    for dato in datos:
        oracion = dato["claim_es"]
        resultado_correcto = dato["label"]
        qid = dato["qid"]
        sujeto = dato["sujeto"]

        print(dato)

        if qid:
            hechos = recuperar_hechos(qid)
            tipos_qids = obtener_tipo_entidad(qid)
            tipos_etiquetas = resolver_qids(tipos_qids)
            oracion_datos = generar_oracion_resumen_con_etiquetas(sujeto, hechos, tipos_etiquetas)
            pred, probs = predecir_con_oracion(oracion_datos, oracion)

            resultado = {
                "oracion": oracion,
                "entidad": sujeto,
                "oracion_creada": oracion_datos,
                "prediccion": pred,
                "confianza": probs,
                "resultado_correcto": resultado_correcto
            }

            with open(ruta_salida, 'a', encoding='utf-8') as f_salida:
                f_salida.write(json.dumps(resultado, ensure_ascii=False) + '\n')


# Función para analizar el texto introducido
def analizar_texto(texto):
    oraciones = dividir_en_oraciones(texto)
    resultados = []
    entidad_anterior = None
    oracion_anterior = None
    hechos_anterior = []
    numero_oraciones = 0

    for oracion in oraciones:
        if oracion != "":
            numero_oraciones += 1
            #print(f"\n--- Analizando oración ---\n{oracion}")
            sujeto = extraer_sujeto(oracion)

            if sujeto:
                qid, label, descripcion = buscar_entidad_wikidata(sujeto)
                if qid:
                    hechos = recuperar_hechos(qid)
                    tipos_qids = obtener_tipo_entidad(qid)
                    tipos_etiquetas = resolver_qids(tipos_qids)
                    oracion_datos = generar_oracion_resumen_con_etiquetas(sujeto,hechos, tipos_etiquetas)
                    entidad_anterior = label
                    hechos_anterior = hechos
                    oracion_anterior = oracion_datos

                else:
                    hechos = []
            else:
                sujeto = entidad_anterior
                hechos = hechos_anterior
                oracion_datos = oracion_anterior

            pred, probs = predecir_con_oracion(oracion_datos, oracion)

            resultados.append({
                "oracion": oracion,
                "entidad": sujeto,
                "hechos": hechos,
                "oracion_creada": oracion_datos,
                "prediccion": pred,
                "confianza": probs
            })

            #print(f"Entidad     : {sujeto}")
            #print(f"Hechos      : {hechos}")
            #print(f"Oracion      : {oracion_datos}")
            #print(f"Predicción  : {pred} | Confianza: {probs}")

    return resultados, numero_oraciones

# Función para procesar el texto y devolver resultados a la llamada API
def procesar_texto(texto):
    resultados, numero_oraciones = analizar_texto(texto)

    conteo = {
        "contradiction": 0,
        "neutral": 0,
        "entailment": 0
    }

    oraciones_etiquetadas = []

    for resultado in resultados:
        pred = resultado["prediccion"]
        conteo[pred] += 1

        oracion = resultado["oracion"]

        if pred == "contradiction":
            oracion = f'<span class="subrayado-contradiction">{oracion}</span>'
        elif pred == "neutral":
            oracion = f'<span class="subrayado-neutral">{oracion}</span>'
        else:
            oracion = f'<span class="subrayado-correcto">{oracion}</span>'

        oraciones_etiquetadas.append(oracion)

    texto_etiquetado = ' '.join(oraciones_etiquetadas)

    return {
        "total_oraciones": numero_oraciones,
        "n_contradiccion": conteo["contradiction"],
        "n_neutral": conteo["neutral"],
        "n_entailment": conteo["entailment"],
        "texto_etiquetado": texto_etiquetado
    }



if __name__ == "__main__":

    '''
        texto = """
    El poeta Miguel Hernandez no nació en España. 
    Escribió Cien años de soledad. 
    Gabriel García Márquez no escribió Cien años de soledad. 
    Gabriel García Márquez ganó el Premio Nobel de Literatura en 1982. 
    Gabriel García Márquez fue un escritor destacado.
    Tierra gira alrededor del Sol.
    """
    analizar_texto(texto)


    benchmark_con_openai()
    benchmark_con_spacy()

    texto = sys.stdin.read()
    resultado = procesar_texto(texto)
    print(json.dumps(resultado))

    '''

    texto = sys.stdin.read()
    resultado = procesar_texto(texto)
    print(json.dumps(resultado))

