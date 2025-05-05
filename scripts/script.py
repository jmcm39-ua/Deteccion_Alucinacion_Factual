import spacy
from transformers import AutoTokenizer, AutoModelForSequenceClassification, MarianMTModel, MarianTokenizer
import torch
from difflib import get_close_matches
from huggingface_hub import login
import requests
from difflib import get_close_matches



# Modelos spacy para detección sujetos
nlp = spacy.load("es_core_news_md")
nlp_en = spacy.load("en_core_web_trf")


# Modelo NLI
tokenizer = AutoTokenizer.from_pretrained("PlanTL-GOB-ES/roberta-large-bne-te")
model = AutoModelForSequenceClassification.from_pretrained("PlanTL-GOB-ES/roberta-large-bne-te")
model.eval()

# Modelo traducción inglés
modelo_trad = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-es-en")
tokenizer_trad = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-es-en")

#Rigoberta asociacion -> Castellano flor,
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
    try:
        print(f"Buscando entidad en Wikidata para: {nombre}")
        
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

            print(f"Entidad encontrada: {label} ({entity_id})")
            return entity_id, label, description
        else:
            print(f"No se encontraron resultados en Wikidata para {nombre}")
    
    except Exception as e:
        print(f"Error en la búsqueda de entidad: {e}")
    
    return None, None, None

# Función de obtención de tipos de la entidad
def obtener_tipo_entidad(qid):
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid}&sites=wikidata&props=claims&format=json"
        response = requests.get(url)
        data = response.json()
        
        if 'entities' not in data or qid not in data['entities']:
            print(f"No se encontraron datos para el QID: {qid}")
            return []

        claims = data.get("entities", {}).get(qid, {}).get("claims", {})

        if "P31" in claims:
            tipos = [c.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') for c in claims["P31"]]
            print(f"Tipos para {qid}: {tipos}")
            return tipos

        return []
    except Exception as e:
        print(f"Error al obtener tipo de entidad: {e}")
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
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={qid_obra}&format=json&props=claims"
        response = requests.get(url)
        data = response.json()
        claims = data.get('entities', {}).get(qid_obra, {}).get('claims', {})
        if 'P577' in claims:
            fecha = claims['P577'][0].get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('time', '')
            return fecha
    except Exception as e:
        print(f"Error al obtener fecha de publicación de {qid_obra}: {e}")
    return None

#Función de obtención de hechos
def recuperar_hechos(qid):
    try:
        print(f"Recuperando hechos para la entidad: {qid}")

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

            # Libros / Obras
            'P50': 'Autor',
            'P577': 'Fecha de publicación',
            'P110': 'Ilustrador',
            'P291': 'Lugar de publicación',
            'P364': 'Idioma de la obra',
            'P1476': 'Título oficial',
            'P1680': 'Descripción corta',

            # Organizaciones / Empresas
            'P112': 'Fundador',
            'P159': 'Sede',
            'P571': 'Fecha de fundación',
            'P452': 'Industria',
            'P1454': 'Accionista',
            'P127': 'Propietario',
            'P749': 'Empresa matriz',

            # Lugares
            'P17': 'País',
            'P131': 'Ubicación administrativa',
            'P625': 'Coordenadas',
            'P2046': 'Área',
            'P1082': 'Población',

            # Objetos astronómicos / planetas
            'P2583': 'Clase espectral',
            'P2120': 'Gravedad superficial',
            'P2067': 'Masa',
            'P2050': 'Órbita',
            'P2146': 'Diámetro',
            'P3984': 'Órbita de',
            'P3996': 'Luna de',
            'P376': 'Órbita alrededor de',

            # Relaciones / colaboraciones
            'P361': 'Parte de',
            'P527': 'Tiene como parte',
            'P176': 'Fabricante',
            'P137': 'Patrocinado por',
            'P710': 'Participante',
            'P155': 'Predecesor',
            'P156': 'Sucesor',
            'P144': 'Basado en'
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

        if not hechos:
            print(f"No se encontraron hechos para la entidad {qid}")

        return hechos

    except Exception as e:
        print(f"Error al recuperar hechos: {e}")
        return []


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
    import re

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
    nac = extraer("Fecha de nacimiento")
    lugar_nac = extraer_valor("Lugar de nacimiento")
    falle = extraer("Fecha de fallecimiento")
    lugar_falle = extraer_valor("Lugar de fallecimiento")
    nacionalidad = extraer_valor("Nacionalidad")
    educacion = extraer_valor("Educación")
    conyuge = extraer_valor("Cónyuge")
    padre = extraer_valor("Padre")
    madre = extraer_valor("Madre")
    ocup = extraer_valor("Ocupación")
    cargo = extraer_valor("Cargo o posición")

    if lugar_nac or nac:
        frag = []
        if lugar_nac:
            frag.append(f"nació en {', '.join(set(lugar_nac))}")
        if nac:
            frag.append(f"el {nac[0].replace('Fecha de nacimiento: +', '').split('T')[0]}")
        partes.append(" ".join(frag))

    if lugar_falle or falle:
        frag = []
        if lugar_falle:
            frag.append(f"falleció en {', '.join(set(lugar_falle))}")
        if falle:
            frag.append(f"el {falle[0].replace('Fecha de fallecimiento: +', '').split('T')[0]}")
        partes.append(" ".join(frag))

    if nacionalidad:
        partes.append(f"de nacionalidad {', '.join(set(nacionalidad))}")
    if educacion:
        partes.append(f"estudió en {', '.join(set(educacion))}")
    if conyuge:
        partes.append(f"su cónyuge es {', '.join(set(conyuge))}")
    if padre or madre:
        parentesco = []
        if padre: parentesco.append(f"padre: {', '.join(set(padre))}")
        if madre: parentesco.append(f"madre: {', '.join(set(madre))}")
        partes.append("tiene como " + " y ".join(parentesco))
    if ocup:
        partes.append(f"fue {', '.join(set(ocup))}")
    if cargo:
        partes.append(f"ocupó cargos como {', '.join(set(cargo))}")

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

    # Organización
    fundacion = extraer("Fecha de fundación")
    fundador = extraer_valor("Fundador")
    sede = extraer_valor("Sede")
    industria = extraer_valor("Industria")
    accionistas = extraer_valor("Accionista")
    propietario = extraer_valor("Propietario")
    matriz = extraer_valor("Empresa matriz")

    if fundacion:
        partes.append(f"fue fundada el {fundacion[0].replace('Fecha de fundación: +', '').split('T')[0]}")
    if fundador:
        partes.append(f"fundada por {', '.join(set(fundador))}")
    if sede:
        partes.append(f"tiene sede en {', '.join(set(sede))}")
    if industria:
        partes.append(f"pertenece a la industria de {', '.join(set(industria))}")
    if accionistas:
        partes.append(f"tiene como accionistas a {', '.join(set(accionistas))}")
    if propietario:
        partes.append(f"es propiedad de {', '.join(set(propietario))}")
    if matriz:
        partes.append(f"su empresa matriz es {', '.join(set(matriz))}")

    # Lugar
    pais = extraer_valor("País")
    admin = extraer_valor("Ubicación administrativa")
    area = extraer_valor("Área")
    poblacion = extraer_valor("Población")
    creacion = extraer("Fecha de creación")
    coord = extraer_valor("Coordenadas")

    if pais:
        partes.append(f"está en {', '.join(set(pais))}")
    if admin:
        partes.append(f"pertenece a {', '.join(set(admin))}")
    if creacion:
        partes.append(f"fue creado el {creacion[0].replace('Fecha de creación: +', '').split('T')[0]}")
    if poblacion:
        partes.append(f"tiene una población de {', '.join(set(poblacion))}")
    if area:
        partes.append(f"con un área de {', '.join(set(area))}")
    if coord:
        partes.append(f"ubicado en las coordenadas {', '.join(set(coord))}")

    # Planeta / objeto astronómico
    clase = extraer_valor("Clase espectral")
    gravedad = extraer_valor("Gravedad superficial")
    masa = extraer_valor("Masa")
    diametro = extraer_valor("Diámetro")
    orbita = extraer_valor("Órbita")
    orbita_de = extraer_valor("Órbita alrededor de")
    luna_de = extraer_valor("Luna de")

    if clase:
        partes.append(f"tiene clase espectral {', '.join(set(clase))}")
    if gravedad:
        partes.append(f"con gravedad superficial de {', '.join(set(gravedad))}")
    if masa:
        partes.append(f"y masa de {', '.join(set(masa))}")
    if diametro:
        partes.append(f"con un diámetro de {', '.join(set(diametro))}")
    if orbita:
        partes.append(f"tiene una órbita de {', '.join(set(orbita))}")
    if orbita_de:
        partes.append(f"orbita alrededor de {', '.join(set(orbita_de))}")
    if luna_de:
        partes.append(f"es una luna de {', '.join(set(luna_de))}")

    # Relaciones / Colaboraciones
    parte_de = extraer_valor("Parte de")
    tiene_partes = extraer_valor("Tiene como parte")
    fabricante = extraer_valor("Fabricante")
    patrocinador = extraer_valor("Patrocinado por")
    participante = extraer_valor("Participante")
    basado_en = extraer_valor("Basado en")

    if parte_de:
        partes.append(f"forma parte de {', '.join(set(parte_de))}")
    if tiene_partes:
        partes.append(f"está compuesto por {', '.join(set(tiene_partes))}")
    if fabricante:
        partes.append(f"fue fabricado por {', '.join(set(fabricante))}")
    if patrocinador:
        partes.append(f"patrocinado por {', '.join(set(patrocinador))}")
    if participante:
        partes.append(f"con participación de {', '.join(set(participante))}")
    if basado_en:
        partes.append(f"basado en {', '.join(set(basado_en))}")


    resumen += ", " + ", ".join(partes) + "."

    return resumen



def predecir_nli(premisa, hipotesis):
    inputs = tokenizer(premisa, hipotesis, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=1).squeeze().tolist()
    etiquetas = ["contradiction", "neutral", "entailment"]
    prediccion = etiquetas[torch.argmax(logits)]
    return prediccion, probs

def predecir_nli_traducido(premisa_es, hipotesis_es):
    # Traducimos ambas al inglés
    premisa_en = traducir_es_en(premisa_es)
    hipotesis_en = traducir_es_en(hipotesis_es)

    # Hacemos predicción con el modelo NLI en inglés
    inputs = tokenizer_nli(premisa_en, hipotesis_en, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = modelo_nli(**inputs).logits
    probs = torch.softmax(logits, dim=1).squeeze().tolist()
    etiquetas = ["contradiction", "neutral", "entailment"]
    prediccion = etiquetas[torch.argmax(logits)]
    return prediccion, probs



def predecir_con_oracion(evidencia_es, hipotesis_es):
    pred, probs = predecir_nli_traducido(evidencia_es, hipotesis_es)
    return pred, probs



def analizar_texto(texto):
    oraciones = dividir_en_oraciones(texto)
    resultados = []
    entidad_anterior = None
    oracion_anterior = None
    hechos_anterior = []

    for oracion in oraciones:
        if oracion != "":
            print(f"\n--- Analizando oración ---\n{oracion}")
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
                    #oracion_datos = ""
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

            print(f"Entidad     : {sujeto}")
            print(f"Hechos      : {hechos}")
            print(f"Oracion      : {oracion_datos}")
            print(f"Predicción  : {pred} | Confianza: {probs}")

    return resultados

# Ejemplo de uso
if __name__ == "__main__":
    texto = """
    GitHub fue fundado por Tom Preston-Werner, Chris Wanstrath, PJ Hyett y Scott Chacon en 2007.
    GitHub es una plataforma de desarrollo colaborativo de software y un servicio de control de versiones usando Git.
    El escritor J.K. Rowling nació en Yate, Inglaterra. 
    El poeta Miguel Hernandez no nació en España. 
    Escribió Cien años de soledad. 
    Gabriel García Márquez no escribió Cien años de soledad. 
    Gabriel García Márquez ganó el Premio Nobel de Literatura en 1982. 
    Gabriel García Márquez fue un escritor destacado.
    Tierra gira alrededor del Sol.
    """
    analizar_texto(texto)
