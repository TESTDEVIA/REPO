"""
AWS Lambda function para manejar un chatbot de Telegram .

Esta función maneja todas las interacciones del bot de Telegram, incluyendo:
- Registro de usuarios
- Cotizaciones
- Integración con ChatGPT
- Gestión de documentos
- Flujos de conversación

"""

import time
from datetime import datetime
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote, parse_qs
from urllib.error import URLError, HTTPError
import re
import boto3
import base64
from boto3.dynamodb.types import Binary

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('telegram')

def guardar_usuario(user_id, user_data):
    """
    Guarda los datos de un usuario en DynamoDB.
    
    Args:
        user_id (str): ID único del usuario
        user_data (dict): Datos del usuario a guardar
    """
    table.put_item(Item={'userID': user_id, **user_data})

def recuperar_usuario(user_id):
    """
    Recupera los datos de un usuario desde DynamoDB.
    
    Args:
        user_id (str): ID único del usuario
        
    Returns:
        dict: Datos del usuario o None si no existe
    """
    response = table.get_item(Key={'userID': user_id})
    user_data = response.get('Item', None)
    if user_data:
        return user_data

def correo_es_valido(correo):
    """
    Valida si un correo electrónico tiene formato válido.
    
    Args:
        correo (str or bytes): Email a validar
        
    Returns:
        bool: True si el email es válido, False en caso contrario
    """
    if isinstance(correo, bytes):
        correo = correo.decode('utf-8')
    patron = r"[^@]+@[^@]+\.[^@]+"
    return re.match(patron, correo)

def validar_fecha(cadena_fecha):
    """
    Valida y convierte una cadena de fecha a objeto date.
    
    Args:
        cadena_fecha (str): Fecha en formato DD-MM-YYYY o DD/MM/YYYY
        
    Returns:
        date: Objeto date si es válida, None en caso contrario
    """
    try:
        fecha_obj = datetime.strptime(cadena_fecha, '%d-%m-%Y')
        return fecha_obj.date()
    except ValueError:
        try:
            fecha_obj = datetime.strptime(cadena_fecha, '%d/%m/%Y')
            return fecha_obj.date()
        except ValueError:
            print (cadena_fecha, " es una fecha invalida")
            return None

def fecha_sql(cadena_fecha):
    """
    Convierte una fecha al formato SQL (YYYY-MM-DD).
    
    Args:
        cadena_fecha (str): Fecha en formato DD-MM-YYYY o DD/MM/YYYY
        
    Returns:
        str: Fecha en formato SQL o None si es inválida
    """
    for formato in ('%d-%m-%Y', '%d/%m/%Y'):
        try:
            fecha_obj = datetime.strptime(cadena_fecha, formato).date()
            return fecha_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    print(cadena_fecha, "es una fecha inválida")
    return None

def pregunta_a_chatgpt(mensaje, model="gpt-4o"):
    """
    Envía una pregunta al servicio ChatGPT y obtiene la respuesta.
    
    Args:
        mensaje (str or bytes): Mensaje a enviar
        model (str): Modelo de GPT a usar
        
    Returns:
        str: Respuesta del ChatGPT
    """
    if isinstance(mensaje, bytes):
        mensaje = mensaje.decode('utf-8')
    url_node_script = "https://YOUR_CHATGPT_API_ENDPOINT/chatgpt"
    headers = {'Content-Type': 'application/json'}
    data = {"message": mensaje, "model": model}

    try:
        req = Request(url_node_script, json.dumps(data).encode('utf-8'), headers)
        with urlopen(req) as response:
            respuesta_json = json.load(response)
            return respuesta_json.get('reply', 'No se pudo obtener una respuesta.')
    except HTTPError as e:
        print(f"Error HTTP al enviar la pregunta: {e}")
        return "Hubo un problema al procesar tu pregunta."
    except URLError as e:
        print(f"Error de URL al enviar la pregunta: {e}")
        return "Error al procesar la pregunta."
    except Exception as e:
        print(f"Error al enviar la pregunta: {e}")
        return "Error al procesar la pregunta."

def pregunta_a_gandalf(mensaje, model="gpt-4o"):
    """
    Envía una pregunta al servicio Gandalf (modo desarrollador) y obtiene la respuesta.
    
    Args:
        mensaje (str or bytes): Mensaje a enviar
        model (str): Modelo de GPT a usar
        
    Returns:
        str: Respuesta del servicio Gandalf
    """
    if isinstance(mensaje, bytes):
        mensaje = mensaje.decode('utf-8')
    url_node_script = "https://YOUR_GANDALF_API_ENDPOINT/gandalf"
    headers = {'Content-Type': 'application/json'}
    data = {"message": mensaje, "model": model}

    try:
        req = Request(url_node_script, json.dumps(data).encode('utf-8'), headers)
        with urlopen(req) as response:
            respuesta_json = json.load(response)
            return respuesta_json.get('reply', 'No se pudo obtener una respuesta.')
    except HTTPError as e:
        print(f"Error HTTP al enviar la pregunta: {e}")
        return "Hubo un problema al procesar tu pregunta."
    except URLError as e:
        print(f"Error de URL al enviar la pregunta: {e}")
        return "Error al procesar la pregunta."
    except Exception as e:
        print(f"Error al enviar la pregunta: {e}")
        return "Error al procesar la pregunta."

def modelo_es_valido(model):
    return isinstance(model, str) and bool(model.strip())


def enviar_mensaje_telegram(chat_id, mensaje, botones=None, url_pdf=None, pdf_file=None, opciones=None):
    """
    Envía un mensaje a Telegram con diferentes opciones de formato.
    
    Args:
        chat_id (str): ID del chat de Telegram
        mensaje (str): Mensaje a enviar
        botones (dict): Botones inline opcionales
        url_pdf (str): URL de PDF a adjuntar
        pdf_file (str): Nombre del archivo PDF
        opciones (list): Opciones de teclado
        
    Returns:
        dict: Respuesta de la API de Telegram
    """
    mensaje = re.sub(r'\*(.*?)\*', r'<b>\1</b>', mensaje)
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Enviar mensaje con PDF
    if url_pdf:
        url = f'https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/sendDocument'
        data = {
            'chat_id': chat_id,
            'document': url_pdf,
            'caption': mensaje,
            'parse_mode': 'HTML'
        }
    
    # Enviar mensaje con botones
    elif botones:
        url = f'https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/sendMessage'
        reply_markup = {
            'inline_keyboard': [[{'text': titulo, 'callback_data': boton_id} for boton_id, titulo in botones.items()]]
        }
        data = {
            'chat_id': chat_id,
            'text': mensaje,
            'reply_markup': reply_markup,
            'parse_mode': 'HTML'
        }
    
    # Enviar mensaje con opciones
    elif opciones:
        url = f'https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/sendMessage'
        reply_markup = {
            'keyboard': [[{'text': opcion} for opcion in opciones]],
            'one_time_keyboard': True,
            'resize_keyboard': True
        }
        data = {
            'chat_id': chat_id,
            'text': mensaje,
            'reply_markup': reply_markup,
            'parse_mode': 'HTML'
        }
    
    # Enviar mensaje de texto simple
    else:
        url = f'https://api.telegram.org/botYOUR_TELEGRAM_BOT_TOKEN/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': mensaje,
            'parse_mode': 'HTML'
        }

    try:
        req = Request(url, json.dumps(data).encode('utf-8'), headers)
        with urlopen(req) as response:
            respuesta_json = json.load(response)
            return respuesta_json
    except HTTPError as e:
        error_message = e.read().decode()
        print(f"Error HTTP al enviar el mensaje: {e.code} {e.reason} {error_message}")
        return {'error': 'Hubo un problema al enviar el mensaje.', 'details': error_message}
    except URLError as e:
        print(f"Error de URL al enviar el mensaje: {e.reason}")
        return {'error': 'Error al procesar el mensaje.'}
    except Exception as e:
        print(f"Error general al enviar el mensaje: {e}")
        return {'error': 'Error al procesar el mensaje.'}

def obtener_boton(data_json, mensaje):
    """
    Extrae el dato del botón presionado desde el callback query.
    
    Args:
        data_json (dict): Datos JSON del webhook de Telegram
        mensaje (str): Mensaje de respaldo
        
    Returns:
        str: Dato del botón o mensaje original
    """
    try:
        if 'callback_query' in data_json:
            callback_query = data_json['callback_query']
            print("Botón:", callback_query['data'])
            return callback_query['data']
    except KeyError:
        pass

    return mensaje

def obtener_contenido_pagina(url, params=None):
    """
    Obtiene el contenido de una página web mediante HTTP GET o POST.
    
    Args:
        url (str): URL a consultar
        params (dict): Parámetros para POST (opcional)
        
    Returns:
        str: Contenido de la página
    """
    data = None
    if params:
        data = urlencode(params).encode('utf-8')  # Codifica los parámetros para la solicitud POST
        req = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    else:
        req = Request(url)

    try:
        with urlopen(req) as response:
            contenido = response.read().decode('utf-8')
            return contenido
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        raise
    except URLError as e:
        print(f"URL Error: {e.reason}")
        raise

def generar_pdf(id_cotizacion):
    """
    Genera un PDF de cotización mediante servicio externo.
    
    Args:
        id_cotizacion (str): ID de la cotización
        
    Returns:
        str: Contenido del PDF generado
    """
    try:
        url = f"https://YOUR_PDF_SERVICE.co/pdfgen/gen.php?id={id_cotizacion}&zoom=0.65&orientation=Landscape&nofolder=1&server=YOUR_SERVER.co"
        contenido = obtener_contenido_pagina(url)
        print("PDF generado correctamente")
        return contenido  # O maneja el contenido como necesites
    except HTTPError as e:
        print(f"Error al generar el PDF: {e}")
        raise
    except URLError as e:
        print(f"Error de conexión al generar el PDF: {e}")
        raise

def cotizar(datos):
    """
    Realiza una cotización de seguro mediante API externa.
    
    Args:
        datos (dict): Datos del cliente para cotizar
        
    Returns:
        str: ID de la cotización generada
    """
    url = "https://YOUR_QUOTE_SERVICE.co/app/chatbot/chatbot.php"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    data_encoded = urlencode(datos).encode('utf-8')
    
    req = Request(url, data=data_encoded, headers=headers)

    try:
        with urlopen(req) as response:
            response_text = response.read().decode('utf-8')
            # Convertir la respuesta de JSON a un diccionario de Python
            respuesta_json = json.loads(response_text)
            return respuesta_json.get("id", "")
    except HTTPError as e:
        print(f"Error en la solicitud HTTP: {e.code} - {e.reason}")
        return ""
    except URLError as e:
        print(f"Error en la URL: {e.reason}")
        return ""
    except json.JSONDecodeError:
        print("Error al decodificar la respuesta JSON")
        return ""

def agregar_beneficiario(datos):
    """
    Agrega un beneficiario a una cotización.
    
    Args:
        datos (dict): Datos del beneficiario
        
    Returns:
        str: ID del beneficiario agregado
    """
    url = "https://YOUR_QUOTE_SERVICE.co/app/chatbot/bchatbot.php"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data_encoded = urlencode(datos).encode('utf-8')
    
    req = Request(url, data=data_encoded, headers=headers)

    try:
        with urlopen(req) as response:
            response_text = response.read().decode('utf-8')
            respuesta_json = json.loads(response_text)
            return respuesta_json.get("id", "")
    except HTTPError as e:
        print(f"Error en la solicitud HTTP: {e.code} - {e.reason}")
        return ""
    except URLError as e:
        print(f"Error en la URL: {e.reason}")
        return ""
    except json.JSONDecodeError:
        print("Error al decodificar la respuesta JSON")
        return ""

def asignar_a_analista(datos):
    """
    Asigna un cliente a un analista para seguimiento.
    
    Args:
        datos (dict): Datos del cliente
        
    Returns:
        str: ID de la asignación
    """
    url = "https://YOUR_QUOTE_SERVICE.co/app/chatbot/asignar.php"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data_encoded = urlencode(datos).encode('utf-8')
    
    req = Request(url, data=data_encoded, headers=headers)

    try:
        with urlopen(req) as response:
            response_text = response.read().decode('utf-8')
            respuesta_json = json.loads(response_text)
            return respuesta_json.get("id", "")
    except HTTPError as e:
        print(f"Error en la solicitud HTTP: {e.code} - {e.reason}")
        return ""
    except URLError as e:
        print(f"Error en la URL: {e.reason}")
        return ""
    except json.JSONDecodeError:
        print("Error al decodificar la respuesta JSON")
        return ""

def dump_data(data):
    print("******************")
    data_str = json.dumps(data, ensure_ascii=False).encode('utf-8')
    print(data_str)
    print("******************")

def parentesco_valido(cadena):
    parentescos = {"Madre", "Padre", "Esposo", "Esposa", "Hijo", "Hija", "Hermano", "Hermana"}
    parentescos = {palabra.lower() for palabra in parentescos}

    return cadena.strip().lower() in parentescos

def obtener_documentos(folder_path):
    url = "https://YOUR_DOCUMENT_SERVICE.co/doc_asist/getfiles.php"
    params = {'folder': folder_path}
    query_string = urlencode(params)
    url_with_params = f"{url}?{query_string}"

    try:
        req = Request(url_with_params)
        with urlopen(req) as response:
            data = response.read()
            documentos = json.loads(data)
            return documentos
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        return None
    except URLError as e:
        print(f"URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def agregar_opciones(historial, opciones, paso_default):
    if not isinstance(paso_default, dict):
        paso_default = {opcion.lower(): paso_default for opcion in opciones}

    historial_actualizado = historial if historial else {}

    for opcion in opciones:
        opcion_min = opcion.lower()  # Convertir la opción a minúsculas
        historial_actualizado[opcion_min] = paso_default.get(opcion_min, "start") 
    
    return historial_actualizado


def dividir_mensaje(mensaje, max_length=1000):
    trozos = []
    while len(mensaje) > max_length:
        corte = mensaje.rfind(' ', 0, max_length)
        if corte == -1:
            corte = mensaje.rfind('.', 0, max_length) + 1
        if corte == -1:
            corte = max_length
        trozos.append(mensaje[:corte].strip())
        mensaje = mensaje[corte:].strip()
    trozos.append(mensaje)
    return trozos

def lambda_handler(event, context):
    """
    Función principal de AWS Lambda para manejar webhooks de Telegram.
    
    Esta función procesa todos los mensajes entrantes del bot de Telegram,
    maneja diferentes estados de conversación y coordina las respuestas.
    
    Args:
        event (dict): Evento de AWS Lambda con datos del webhook
        context: Contexto de ejecución de Lambda
        
    Returns:
        dict: Respuesta HTTP para Telegram
    """

    print("Evento completo", event)
    
    method = event['requestContext']['http']['method']

    if 'queryStringParameters' in event:
        params = event['queryStringParameters']
        hub_mode = params.get('hub.mode', None)
        hub_verify_token = params.get('hub.verify_token', None)
        hub_challenge = params.get('hub.challenge', None)
        user_id = params.get('userid', None)
        reset_id = params.get('resetid', None)
        admin_id = params.get('adminid', None)
        add_admin = params.get('add_admin', None)
        add_developer = params.get('add_developer', None)
        master_id  = params.get('master_id', None)
        setnameid  = params.get('setname_id', None)
        name  = params.get('name', None)

        if method == 'GET' and user_id is not None:
            user_data = recuperar_usuario(user_id)
            if user_data:
                print(user_data)
                if 'bcuenta' in user_data:
                    del user_data['bcuenta']
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and admin_id is not None:
            usuario = recuperar_usuario(admin_id)
            usuario['step'] = 'start'
            usuario['rol'] = 'admin'
            usuario['historial'] =  {"hola":"start", "/start":"start"}
            keys_to_delete = ['bcuenta', 'documents', 'companies', 'opciones', 'base_path']
            for key in keys_to_delete:
                if key in usuario:
                    del usuario[key]
            guardar_usuario(admin_id, usuario)
            user_data = recuperar_usuario(admin_id)
            if user_data:
                print(user_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and reset_id is not None:
            usuario = recuperar_usuario(reset_id)
            usuario['step'] = 'start'
            usuario['rol'] = 'user'
            usuario['historial'] =  {"hola":"start", "/start":"start"}
            keys_to_delete = ['bcuenta', 'documents', 'companies', 'opciones', 'base_path']
            for key in keys_to_delete:
                if key in usuario:
                    del usuario[key]
            guardar_usuario(reset_id, usuario)
            user_data = recuperar_usuario(reset_id)
            if user_data:
                print(user_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and setnameid is not None:
            usuario = recuperar_usuario(setnameid)
            usuario['nombre'] = name
            guardar_usuario(setnameid, usuario)
            user_data = recuperar_usuario(setnameid)
            if user_data:
                print(user_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and add_admin is not None:
            usuario = {'step': 'start', 'monto': '', 'nombre': '', 'fecha': '', 'modo': 'normal',  'cotiza': '',  'rol': 'admin'}
            usuario['historial'] =  {"hola":"start", "/start":"start"}
            guardar_usuario(add_admin, usuario)
            user_data = recuperar_usuario(add_admin)
            if user_data:
                print(user_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and add_developer is not None:
            usuario = {'step': 'start', 'monto': '', 'nombre': '', 'fecha': '', 'modo': 'normal',  'rol': 'developer'}
            usuario['historial'] =  {"hola":"start", "/start":"start"}
            usuario['developer'] =  "ON"
            guardar_usuario(add_developer, usuario)
            user_data = recuperar_usuario(add_developer)
            if user_data:
                print(user_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and master_id is not None:
            usuario = recuperar_usuario(master_id)
            usuario['historial'] =  {"hola":"start", "/start":"start"}
            usuario['master'] =  "ON"
            usuario['modo'] =  "normal"
            guardar_usuario(master_id, usuario)
            user_data = recuperar_usuario(master_id)
            if user_data:
                print(user_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps(user_data, indent=4)
                }

        if method == 'GET' and hub_mode == 'subscribe' and hub_verify_token == 'VALOR_TOKEN':
            print('Token verificado correctamente')
            return {
                'statusCode': 200,
                'body': hub_challenge
            }
        else:
            return {
                'statusCode': 403,
                'body': 'Token inválido o método incorrecto'
            }
    elif 'body' in event:
        request_json = json.loads(event['body'])
        data = request_json.get('message', {})
        chat_id = str(data.get('chat', {}).get('id', ''))
        mensaje = data.get('text', '')

        first_name = data.get('from', {}).get('first_name', '')
        last_name = data.get('from', {}).get('last_name', '')

        profile_name = first_name + " " + last_name

        if not chat_id or not mensaje:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Mensaje no válido'})
            }

        print("chat_id:", chat_id, " ",profile_name)
        sender = chat_id

        respuesta = {}        

        url_pdf = None
        pdf_file = None

        mensaje=obtener_boton(data, mensaje)

        if (sender == ""):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Sender not found'})
            }

        if not (mensaje==""):
            print("Mensaje recibido:", mensaje, " de: ",sender)

        usuario = {'step': 'start', 'monto': '', 'nombre': '', 'fecha': '', 'modo': 'normal',  'cotiza': ''}
        if sender is not None and not (sender == ""):
            usuario = recuperar_usuario(sender)
        if not usuario and not (sender == ""):
            if profile_name == "":
                usuario = {'step': 'start', 'monto': '', 'nombre': '', 'fecha': '', 'modo': 'normal',  'cotiza': ''}
            else:
                usuario = {'step': 'start', 'monto': '', 'nombre': profile_name, 'fecha': '', 'modo': 'normal',  'cotiza': ''}
            guardar_usuario(sender, usuario)

        step = usuario['step']
        nombre = usuario['nombre']
        rol = "user"
        if 'rol' in usuario:
            rol = usuario['rol']
        master = "OFF"
        if 'master' in usuario:
            master = usuario['master']
        developer = "OFF"
        if 'developer' in usuario:
            developer = usuario['developer']
        if not (profile_name=="") and (nombre == ""):
            nombre = profile_name
        respuesta = {}
        botones = {}
        opciones = {}

        if isinstance(mensaje, bytes):
            mensaje_decoded = mensaje.decode('utf-8').lower()
        elif isinstance(mensaje, str):
            mensaje_decoded = mensaje.lower()
        else:
            mensaje_decoded = str(mensaje).lower()

        if isinstance(profile_name, bytes):
            profile_name = profile_name.decode('utf-8')

        profile_name = profile_name.title()

        numero_bot = "YOUR_BOT_PHONE_NUMBER"

        adminMode=False

        if sender == numero_bot: # or sender == numero_analista:
            return jsonify({'status': 'ignored'})

        if 'historial' in usuario:
            if mensaje_decoded in usuario['historial']:
                step = usuario['historial'][mensaje_decoded]
                usuario['step'] = step
                print("STEP from historial: ", step)
        if master == "ON" and step == "start":
            step = "master"
            usuario['step'] = step

        print("**********")
        print("SENDER: ",sender)
        print("STEP: ",step)
        print("MODO: ",usuario['modo'])
        print("MENSAJE: ",mensaje_decoded)
        if 'model' in usuario and modelo_es_valido(usuario['model']):
            print("MODELO: ",usuario['model'])
        else:
            print("MODELO: gpt-4o (DEFAULT)")
        print("**********")

        if False and not (step == 'start' or mensaje_decoded=="hola") and not (usuario['cotiza'] == ""):
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Cotizacion ya realizada'})
            }
        analista=""
        if not (master == "ON") and (step == 'start' or mensaje_decoded=="hola" or mensaje_decoded=="/start") and not (mensaje_decoded=="chatgpt" or mensaje_decoded=="dr seguro") and (usuario['modo']=='normal'):
            usuario['poliza'] = 'Salud'
            usuario['cotiza'] = ""
            if nombre == "":
                respuesta['text'] = 'Hola, espero te encuentres bien. Soy *TUBOT*, ejecutivo virtual de *TUEMPRESA*. Es un gusto para mí atenderte para ofrecerte diferentes opciones de seguros de salud.'
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
                time.sleep(1)
                respuesta['text'] = f'¿Sería tan amable de darme su nombre y apellido?'
                usuario['step'] = 'askedWelcome'
            else:
                if rol == "admin":
                    respuesta['text'] = f'Hola *{nombre}*, espero te encuentres bien. Soy *TUBOT*, ejecutivo virtual de *TUEMPRESA*.'
                    print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
                    respuesta['text'] = f'¿En qué área te puedo ayudar?'
                    opciones = ["Riesgos","Soporte al Cliente","Administracion","Hablar con TUBOT"]
                    usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'askedAdmin')
                    print(enviar_mensaje_telegram(sender, respuesta['text'], None, None, None, opciones))
                    respuesta['text'] = ''
                    usuario['step'] = 'askedAdmin'
                elif rol == "developer":
                    respuesta['text'] = f'Hola *{nombre}*, soy *TUBOTSECUNDARIO*, pregúntame lo que quieras'
                    usuario['step'] = 'waitForQuestion'
                    usuario['modo'] = 'gandalf'
                else:
                    respuesta['text'] = f'Hola *{nombre}*, espero te encuentres bien. Soy *TUBOT*, ejecutivo virtual de *TUEMPRESA*. Es un gusto para mí atenderte para ofrecerte diferentes opciones de seguros de salud.'
                    print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
                    time.sleep(1)
                    respuesta['text'] = f'¿Sería tan amable de indicarme su fecha de nacimiento?'
                    usuario['step'] = 'askedBirthdate'

        elif step == 'master':
            usuario['poliza'] = 'Salud'
            usuario['cotiza'] = ""
            respuesta['text'] = f'Hola *{nombre}*, espero te encuentres bien. Soy *TUBOT*, ejecutivo virtual de *TUEMPRESA*.'
            print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
            respuesta['text'] = f'¿Con que rol quieres interactuar conmigo?'
            if developer=="ON":
                opciones = ["Usuario","Asociado","Master","Desarrollador"]
            else:
                opciones = ["Usuario","Asociado","Master"]
            usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'askedMaster')
            print(enviar_mensaje_telegram(sender, respuesta['text'], None, None, None, opciones))
            respuesta['text'] = ''
            usuario['step'] = 'askedMaster'

        elif mensaje_decoded=="chatgpt" or mensaje_decoded=="dr seguro": # and adminMode:
            respuesta['text'] = 'Estoy aqui para responder tus preguntas. Adelante.'
            usuario['step'] = 'waitForQuestion'

        elif step == 'askedWelcome' and (usuario['modo']=='normal'):
            usuario['nombre'] = mensaje_decoded.title()
            nombre=usuario['nombre']
            if isinstance(usuario['nombre'], bytes):
                nombre = usuario['nombre'].decode('utf-8')      
            respuesta['text'] = f'Un gusto *{nombre}*. También indícame tu fecha de nacimiento:'
            usuario['step'] = 'askedBirthdate'

        elif step == 'askedBirthdate':
            fecha=validar_fecha(mensaje_decoded)
            if fecha:
                usuario['fecha'] = mensaje_decoded
                respuesta['text'] = 'Y ahora tu correo electrónico.'
                usuario['step'] = 'askedEmail'
            else:
                respuesta['text'] = 'La fecha no es correcta, por favor ingresa una fecha valida (DD/MM/AAAA).'
                usuario['step'] = 'askedBirthdate'

        elif step == 'askedOnlyName':
            usuario['nombre'] = mensaje_decoded.title()
            usuario['step'] = 'end'
            nombre=usuario['nombre']
            if isinstance(usuario['nombre'], bytes):
                nombre = usuario['nombre'].decode('utf-8')      
            poliza=usuario['poliza']
            data = {
                'telefono': sender,
                'nombre': usuario['nombre'],
                'poliza': usuario['poliza']
            }
            asignar_a_analista(data)
            respuesta['text'] = f'Gracias {nombre}, voy a dirigir tu llamada a un analista para una póliza de {poliza}. ¿Tienes alguna otra pregunta para mí?'
            botones = {
                "Si": "Si",
                "No": "No",
                "Cotiza": "Volver a cotizar"
            }
            usuario['step'] = 'additionalHelp'

        elif step == 'askedName':
            usuario['nombre'] = mensaje_decoded.title()
            respuesta['text'] = 'Proporciona un correo electrónico para contactarte'     
            usuario['step'] = 'askedEmail'

        elif step == 'askedEmail':
            if correo_es_valido(mensaje_decoded):
                usuario['email'] = mensaje_decoded
                respuesta['text'] = 'Por último, selecciona tu género:'
                botones = {
                    "M": "Masculino",
                    "F": "Femenino"
                }            
                usuario['step'] = 'askedSex'
            else:
                respuesta['text'] = 'El correo electrónico ingresado no es válido. Por favor, ingresa un correo electrónico válido.'

        elif step == 'askedSex':
            usuario['sexo'] = mensaje_decoded
            usuario['bcuenta']=0
            usuario['beneficiario'] = "no"
            respuesta['text'] = f'¿Desea agregar a un familiar a la cotización?'
            botones = {
                "Si": "Si",
                "No": "No"
            }
            usuario['step'] = 'askBenefit'

        elif step == 'askBenefit':
            if mensaje_decoded == 'si':
                usuario['beneficiario'] = "si"
                respuesta['text'] = 'Escribe el parentesco (Madre, Padre, Esposo, Esposa, Hijo, Hija, Hermano o Hermana):'
                usuario['step'] = 'askedParent'
            else:
                respuesta['text'] = 'Ha elegido no agregar más familiares. Procederé a preparar su cotización.'
                botones = {
                    "Continuar": "Continuar"
                }
                usuario['step'] = 'askedFamily'

        elif step == 'askedParent':
            if parentesco_valido(mensaje_decoded):
                usuario['parentesco'] = mensaje_decoded.strip().lower()
                parentesco=usuario['parentesco']
                respuesta['text'] = f'Escribe la fecha de nacimiento de tu {parentesco}:'
                usuario['step'] = 'askedBirthdateParent'
            else:
                respuesta['text'] = f'El parentesco no es correcto. Por favor, escribe alguna de estas opciones: Madre, Padre, Esposo, Esposa, Hijo, Hija, Hermano o Hermana'

        elif step == 'askedBirthdateParent':
            fecha=validar_fecha(mensaje_decoded)
            if fecha:
                usuario['bfecha'] = mensaje_decoded
                usuario['bcuenta']=usuario['bcuenta']+1
                data = {
                    'btoken': sender,
                    'bfecha': fecha_sql(usuario['bfecha']),
                    'bparentesco': usuario['parentesco'],
                    'correlativo': usuario['bcuenta']
                }
                agregar_beneficiario(data)
                respuesta['text'] = f'¿Desea agregar a otro familiar a la cotización?'
                botones = {
                    "Si": "Si",
                    "No": "No"
                }
                usuario['step'] = 'askBenefit'
            else:
                respuesta['text'] = 'La fecha no es correcta, por favor ingresa una fecha valida (DD/MM/AAAA).'

        elif step == 'askedFamily':
            usuario['bcuenta']=0
            respuesta['text'] = 'Perfecto, en este momento le estoy enviando un cuadro de cotización para que proceda con su revisión.'
            print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
            time.sleep(1)
            nombre=usuario['nombre']
            usuario['plan']="Amplio"
            usuario['monto']="100000"
            usuario['monto2']="200000"
            usuario['modo'] = "chatgpt"
            usuario['step'] = "waitForQuestion"
            guardar_usuario(sender, usuario)
            if isinstance(usuario['nombre'], bytes):
                nombre = usuario['nombre'].decode('utf-8')           
            data = {
                'telefono': sender,
                'fecha': fecha_sql(usuario['fecha']),
                'nombre': usuario['nombre'],
                'email': usuario['email'],
                'sexo': usuario['sexo'],
                'plan': usuario['plan'],
                'monto': usuario['monto'],
                'monto2': usuario['monto2']
            }            
            id_cotizacion=cotizar(data)
            print("Generando PDF ", id_cotizacion)
            generar_pdf(id_cotizacion)
            if id_cotizacion:
                print("PDF generado con exito ", id_cotizacion)
                usuario['cotiza']=str(id_cotizacion)
                url_pdf = f"https://YOUR_PDF_SERVICE.co/pdfgen/{id_cotizacion}.pdf"
                pdf_file=f"Cotizacion_{id_cotizacion}.pdf"
                respuesta['text'] = f"Tu cotización {id_cotizacion} ya está lista. Puedes verla aquí."
                #if sender not in polizas:
                #    polizas[sender] = {'telefono': sender,'nombre': nombre, 'poliza': "Salud"}                   
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
                time.sleep(15)
            else:
                respuesta['text'] = "Hubo un error al procesar tu cotización."
                url_pdf=None
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))

            respuesta['text'] = "Por otro lado, le estoy enviando otras cotizaciones que puedan adaptarse a su presupuesto"
            url_pdf=None
            print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file,opciones))
            time.sleep(1)
            usuario['monto']= "50000"
            usuario['monto2']="30000"
            usuario['monto3']="20000"
            usuario['plan']="Amplio"

            data = {
                'telefono': sender,
                'fecha': fecha_sql(usuario['fecha']),
                'nombre': usuario['nombre'],
                'email': usuario['email'],
                'sexo': usuario['sexo'],
                'plan': usuario['plan'],
                'monto': usuario['monto'],
                'monto2': usuario['monto2'],
                'monto3': usuario['monto3'],
                'bdelete': "SI"
            }            
            id_cotizacion=cotizar(data)
            generar_pdf(id_cotizacion)
            if id_cotizacion:
                url_pdf = f"https://YOUR_PDF_SERVICE.co/pdfgen/{id_cotizacion}.pdf"
                pdf_file=f"Cotizacion_{id_cotizacion}.pdf"
                respuesta['text'] = f"Tu cotización {id_cotizacion} ya está lista. Puedes verla aquí."
                #if sender not in polizas:
                #    polizas[sender] = {'telefono': sender,'nombre': nombre, 'poliza': "Salud"}                   
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file,opciones))
                time.sleep(15)
            else:
                respuesta['text'] = "Hubo un error al procesar tu cotización."
                url_pdf=None
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file,opciones))
            
            poliza=usuario['poliza']
            data = {
                'telefono': sender,
                'nombre': nombre,
                'poliza': f"Salud #{id_cotizacion}"
            }
            # asignar_a_analista(data)
            url_pdf=None
            respuesta['text'] = 'Tu cotización ha sido procesada con éxito. ¿Tienes alguna otra pregunta para mí?'
            print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file,opciones))
            respuesta['text'] = ''
            usuario['modo'] = "chatgpt"
            usuario['step'] = "waitForQuestion"
            step = "waitForQuestion"
            guardar_usuario(sender, usuario)

        elif step == 'end':
            respuesta['text'] = '¿Tienes alguna otra pregunta para mí?'
            if usuario['poliza'] == 'Salud':
                respuesta['text'] = 'Tu cotización ha sido procesada con éxito. ¿Tienes alguna otra pregunta para mí?'
            if rol == "admin" or rol == "developer":
                botones = {
                    "Si": "Si",
                    "No": "No",
                    "Cotiza": "Volver"
                }
            else:
                botones = {
                    "Si": "Si",
                    "No": "No",
                    "Cotiza": "Volver a cotizar"
                }                
            usuario['step'] = 'additionalHelp'

        elif step == 'additionalHelp':
            if mensaje_decoded == 'no':
                if rol == "admin" or rol == "developer":
                    respuesta['text'] = '¡Gracias por contactarme! Si necesitas más ayuda en el futuro, no dudes en escribirme.'
                else:
                    respuesta['text'] = '¡Gracias por contactarnos! Si necesitas más ayuda en el futuro, no dudes en escribirnos.'
                usuario['step'] = 'finalizado'
                usuario['modo'] = 'normal'
            if mensaje_decoded == 'volver a cotizar' or mensaje_decoded == 'volver' or mensaje_decoded.startswith('hola'):
                if rol == "admin" or rol == "developer":
                    respuesta['text'] = '¡Seguro! Solo escribeme *Hola* otra vez cuando quieras volver a consultar..'
                else:
                    respuesta['text'] = '¡Seguro! Solo escribeme *Hola* otra vez cuando quieras volver a cotizar..'
                usuario['step'] = 'start'
                usuario['modo'] = 'normal'
            elif mensaje_decoded == 'si':
                if usuario['modo'] == 'gandalf':
                    respuesta['text'] = 'Pregúntame lo que quieras. Soy *Gandalf el Blanco*.'
                else:
                    respuesta['text'] = 'Por favor, escribe tu pregunta a continuación.'
                    usuario['modo'] = 'chatgpt'
                usuario['step'] = 'waitForQuestion'
            else:
                if usuario['modo'] == 'chatgpt':
                    respuesta_chatgpt = pregunta_a_chatgpt(mensaje_decoded)
                    if respuesta_chatgpt == "TOKEN_START":
                        respuesta['text'] = "¡Bien! Vamos a cotizar de nuevo..."
                        usuario['step'] = 'start'
                        usuario['modo'] = 'normal'
                    elif respuesta_chatgpt == "TOKEN_END":
                        respuesta['text'] = '¡Gracias por contactarnos! Si necesitas más ayuda en el futuro, no dudes en escribirnos.'
                        usuario['step'] = 'finalizado'
                        usuario['modo'] = 'normal'
                    else:
                        respuesta['text'] = respuesta_chatgpt + "\n\n¿Tienes otra pregunta?"
                        if rol == "admin" or rol == "developer":
                            botones = {
                                "Si": "Si",
                                "No": "No",
                                "Cotiza": "Volver"
                            }
                        else:
                            botones = {
                                "Si": "Si",
                                "No": "No",
                                "Cotiza": "Volver a cotizar"
                            }
                        usuario['step'] = 'confirmContinue'
                else:
                    pass

        elif step == 'endCotiza':
            respuesta['text'] = respuesta_chatgpt + "\n\n¿Tienes otra pregunta?"
            if rol == "admin" or rol == "developer":
                botones = {
                    "Si": "Si",
                    "No": "No",
                    "Cotiza": "Volver"
                }
            else:
                botones = {
                    "Si": "Si",
                    "No": "No",
                    "Cotiza": "Volver a cotizar"
                }
            usuario['step'] = 'confirmContinue'

        elif step == 'waitForQuestion':
            model = "gpt-4o"  # Modelo por defecto
            if not (mensaje_decoded == "continuar"):
                if 'model' in usuario and modelo_es_valido(usuario['model']):
                    model = usuario['model']
                if usuario['modo'] == 'gandalf' or rol == "developer":
                    respuesta_chatgpt = pregunta_a_gandalf(mensaje_decoded, model)
                else:
                    respuesta_chatgpt = pregunta_a_chatgpt(mensaje_decoded, model)
                mensajes = dividir_mensaje(respuesta_chatgpt)
                for respuesta_chatgpt in mensajes:
                    enviar_mensaje_telegram(sender, respuesta_chatgpt, None, None, None, None)
                    time.sleep(1)                
                respuesta['text'] = "¿Tienes otra pregunta?"
                if rol == "admin" or rol == "developer":
                    botones = {
                        "Si": "Si",
                        "No": "No",
                        "Cotiza": "Volver"
                    }
                else:
                    botones = {
                        "Si": "Si",
                        "No": "No",
                        "Cotiza": "Volver a cotizar"
                    }            
                usuario['step'] = 'additionalHelp'

        elif step == 'confirmContinue':
            if mensaje_decoded == 'si':
                respuesta['text'] = '¡Muy bien! Haz tu próxima pregunta.'
                usuario['step'] = 'additionalHelp'
                usuario['modo'] = 'chatgpt'
            if mensaje_decoded == 'cotiza':
                respuesta['text'] = '¡Seguro! Podemos volver a cotizar.'
                usuario['step'] = 'start'
                usuario['modo'] = 'normal'
            else:
                respuesta['text'] = '¡Gracias por contactarnos! Si necesitas más ayuda en el futuro, no dudes en escribirnos.'
                usuario['step'] = 'finalizado'
                usuario['modo'] = 'normal'

        elif step == 'askedAdmin':
            respuesta['text'] = '¿En qué subárea te puedo ayudar?'
            usuario['step'] = 'start'
            usuario['modo'] == 'normal'
            if mensaje_decoded in ['administracion', 'riesgos', 'soporte al cliente']:
                usuario['categoria'] = mensaje_decoded
                suboptions = {
                    'administracion': ["Aranceles", "Relacion Comisiones", "Pago Comisiones", "Contacto"],
                    'riesgos': ["Condicionados", "Métodos Pago", "Requisitos Cotizar", "Requisitos Emitir", "Requ. cotizar colectivo", "Requ. cotizar flota", "Solicitudes",'Edad de admisibilidad','Plazos de espera'],
                    'soporte al cliente': ["Red clinicas", "Proc. Reclamos", "Tramitar Recl.", "Contactos Emerg."]
                }
                opciones = suboptions[mensaje_decoded]
                usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'sub_category_selection')
                usuario['opciones'] = opciones
                respuesta['text'] = "Selecciona una subcategoría:"
                usuario['step'] = 'sub_category_selection'
            if mensaje_decoded == 'hablar con deyna':
                respuesta['text'] = 'Estoy aqui para responder tus preguntas. Adelante.'
                opciones = {}
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
                usuario['step'] = 'waitForQuestion'
                usuario['modo'] == 'chatgpt'
                respuesta['text'] = ''
        elif step == 'askedMaster':
            if mensaje_decoded=="usuario":
                respuesta['text'] = 'Hola, espero te encuentres bien. Soy *TUBOT*, ejecutivo virtual de *TUEMPRESA*. Es un gusto para mí atenderte para ofrecerte diferentes opciones de seguros de salud.'
                print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
                time.sleep(1)
                respuesta['text'] = f'¿Sería tan amable de darme su nombre y apellido?'
                usuario['rol'] == 'user'
                usuario['modo'] == 'normal'
                usuario['step'] = 'askedWelcome'
            if mensaje_decoded=="asociado":
                respuesta['text'] = f'¿En qué área te puedo ayudar?'
                opciones = ["Riesgos","Soporte al Cliente","Administracion","Hablar con TUBOT"]
                usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'askedAdmin')
                print(enviar_mensaje_telegram(sender, respuesta['text'], None, None, None, opciones))
                respuesta['text'] = ''
                usuario['rol'] == 'admin'
                usuario['step'] = 'askedAdmin'
                usuario['modo'] == 'normal'
            if mensaje_decoded=="desarrollador" and developer=="ON":
                respuesta['text'] = f'Hola *{nombre}*, soy *TUBOTSECUNDARIO*, pregúntame lo que quieras'
                usuario['rol'] == 'developer'
                usuario['step'] = 'waitForQuestion'
                usuario['modo'] = 'gandalf'
            if mensaje_decoded=="master":
                respuesta['text'] = '¡Hola Maestro! ¿Que nueva instrucción o sugerencia quieres que aprenda?'
                usuario['step'] = 'askedTrainer'

        elif step == 'askedTrainer':
            respuesta['text'] = 'Memorizando. Espera un momento por favor...'
            print(enviar_mensaje_telegram(sender, respuesta['text'], None, None, None, None))
            user_data = recuperar_usuario("deyna")
            instrucciones = ""
            if user_data and 'instrucciones' in user_data:
                user_data['instrucciones']=user_data['instrucciones']+"\n"+mensaje_decoded
                guardar_usuario("deyna", user_data)
                time.sleep(1)
                response = pregunta_a_chatgpt("TUBOT:reborn")
                respuesta['text'] = 'Mi base de conocimiento ha sido actualizada con éxito.'
                usuario['step'] = 'master'
            else:
                respuesta['text'] = 'Mi base de conocimiento no tiene instrucciones. Algo anda mal con mi servidor.'
                usuario['step'] = 'master'

        elif step == 'gandalf':
            respuesta['text'] = 'Estoy aqui para responder tus preguntas. Adelante.'
            opciones = {}
            print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))
            usuario['step'] = 'waitForQuestion'
            usuario['modo'] == 'gandalf'
            respuesta['text'] = ''
        elif step == 'sub_category_selection':
            if usuario['categoria'] in ['administracion', 'riesgos', 'soporte al cliente']:
                usuario['subcategoria'] = mensaje_decoded
                if mensaje_decoded in ['condicionados', 'métodos pago', 'solicitudes','red clinicas']:
                    usuario['step'] = 'company_selection'
                    # Define companies based on the subcategory
                    companies = {
                        'conicionados': ['Compania1', 'Compania2', 'Compania3', 'Compania4', 'Compania5', 'Compania6', 'Compania7', 'Compania8', 'Compania9', 'Compania10'],
                        'red clinicas': ['Compania1', 'Compania2', 'Compania3', 'Compania4', 'Compania5', 'Compania6', 'Compania7', 'Compania8', 'Compania9', 'Compania10'],
                        'métodos pago': ['Compania1', 'Compania2', 'Compania3', 'Compania4', 'Compania5', 'Compania6', 'Compania7', 'Compania8', 'Compania9', 'Compania10'],
                        'solicitudes': ['Compania1', 'Compania2', 'Compania3', 'Compania4', 'Compania5', 'Compania6', 'Compania7', 'Compania8', 'Compania9', 'Compania10']
                    }                    
                    usuario['companies'] = companies.get(mensaje_decoded, [])
                    opciones = usuario['companies']
                    usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'company_selection')
                    respuesta['text'] = "Selecciona una aseguradora:"
                else:
                    print ("ELEGIR: ",usuario['categoria'], ",", mensaje_decoded, ",", usuario['subcategoria'])
                    documento, tipo, base_path = elegir_documento(usuario['categoria'], mensaje_decoded)
                    usuario['base_path'] = base_path
                    if tipo == 'list':
                        usuario['documents'] = documento                        
                        print("1:",base_path,"2:",documento)                        
                        opciones = documento
                        usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'document_choice')
                        respuesta['text'] = "Selecciona un archivo o carpeta:" 
                        usuario['step'] = 'document_choice'
                    elif tipo == 'single':
                        url_pdf = documento
                        if 'base_path' in usuario and usuario['base_path'] is not None:
                            url_pdf=usuario['base_path']+url_pdf
                        pdf_file = f"{mensaje_decoded[:22]}.pdf"
                        respuesta['text'] = f"Aquí está el documento que solicitaste"
                        usuario['step'] = 'start'                    
                    else:
                        respuesta['text'] = "Opción no válida. Selecciona una opción válida."
            else:
                respuesta['text'] = "Subcategoría no reconocida. Elige una opción válida."
        elif step == 'company_selection':
            documento, tipo, base_path = elegir_documento(usuario['categoria'], usuario['subcategoria'], mensaje_decoded)
            usuario['base_path'] = base_path
            if tipo == 'list':
                usuario['documents'] = documento
                print("1:",base_path,"2:",documento)
                usuario['base_path'] = base_path
                opciones = documento
                usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'document_choice')
                respuesta['text'] = "Selecciona un archivo o carpeta:" 
                usuario['step'] = 'document_choice'
            elif tipo == 'single':
                url_pdf = documento
                if 'base_path' in usuario and usuario['base_path'] is not None:
                    url_pdf=usuario['base_path']+url_pdf
                pdf_file = f"{mensaje_decoded}.pdf"
                respuesta['text'] = f"Aquí está el documento que solicitaste"
                usuario['step'] = 'start'                    
            else:
                respuesta['text'] = "Opción no válida. Selecciona una opción válida."
        elif step == 'document_choice':
            selected_doc = usuario['documents'].get(mensaje_decoded, None)
            if selected_doc:
                print("Documento seleccionado: ",selected_doc)
                if selected_doc.endswith("pdf"):
                    print("Termina en PDF")
                    url_pdf = selected_doc
                    pdf_file = f"{mensaje_decoded}"
                    respuesta['text'] = f"Aquí está el documento que solicitaste"
                    botones = {}
                    opciones = {}
                    usuario['step'] = 'start'
                else:
                    print("No termina en PDF")
                    folder_path = usuario['base_path'].rstrip('/') + '/' + mensaje_decoded.lstrip('/')
                    print("obtener_documentos(",folder_path,")")
                    documentos = obtener_documentos(folder_path.replace("https://YOUR_DOCUMENT_SERVICE.co/doc_asist/", ""))
                    if documentos:
                        if not folder_path.endswith("/"):
                            folder_path=folder_path+"/"
                        documentos_urls = {doc: f"{folder_path}{doc}" for doc in documentos}
                        usuario['documents'] = documentos_urls
                        opciones = documentos_urls
                        usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'document_choice')
                        respuesta['text'] = "Selecciona un archivo o carpeta:" 
                        usuario['step'] = 'document_choice'
                    else:
                        respuesta['text'] = "Documento no válido o carpeta vacia. Intente de nuevo."
                        usuario['step'] = 'start'
            else:
                folder_path = usuario['base_path'].rstrip('/') + '/' + mensaje_decoded.lstrip('/')
                print("obtener_documentos(",folder_path,")")
                documentos = obtener_documentos(folder_path.replace("https://YOUR_DOCUMENT_SERVICE.co/doc_asist/", ""))
                if documentos:
                    if not folder_path.endswith("/"):
                        folder_path=folder_path+"/"
                    documentos_urls = {doc: f"{folder_path}{doc}" for doc in documentos}
                    usuario['documents'] = documentos_urls
                    opciones = documentos_urls
                    usuario['historial'] = agregar_opciones(usuario.get('historial', {}), opciones, 'document_choice')
                    respuesta['text'] = "Selecciona un archivo o carpeta:" 
                    usuario['step'] = 'document_choice'
                else:
                    respuesta['text'] = "Documento no válido o carpeta vacia. Intente de nuevo."
                    usuario['step'] = 'start'
        else:
            respuesta['text'] = 'No entiendo tu mensaje. Escribe *hola* para empezar de nuevo.'
            usuario['step'] = 'start'
            usuario['modo'] = 'normal'
        if 'text' in respuesta and not (respuesta['text'] == ''):
            print(enviar_mensaje_telegram(sender, respuesta['text'], botones, url_pdf, pdf_file, opciones))

        if sender is not None and not (sender == "") and usuario:
            guardar_usuario(sender, usuario)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Operación realizada correctamente'})
        }

    else:
        return {
            'statusCode': 405,
            'body': json.dumps({'message': 'Method Not Allowed'})
        }


def registrar_log(data):
    with open("messages.txt", "a", encoding='utf-8') as f:
        f.write(data + "\n")

def main():
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "hub.mode": "subscribe",
            "hub.verify_token": "Speed_1972",
            "hub.challenge": "12345"
        }
    }
    
    print(lambda_handler(event, None))


if __name__ == "__main__":

    main()
