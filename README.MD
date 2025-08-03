# Sistema de Chatbots

Este repositorio contiene tres funciones AWS Lambda que forman un sistema completo de chatbots para gestión de solicitudes via WS, generación de códigos QR y procesamiento de consultas con IA.

## 📁 Estructura del Proyecto

```
├── qr/
│   └── index.mjs          # Generador de códigos QR
├── siniestro/
│   └── index.mjs          # Chatbot Siniestro con OpenAI
├── telegram/
│   └── lambda_function.py # Bot principal de Telegram
└── README.md
```

## 🚀 Funciones Lambda

### 1. QR Generator (`qr/index.mjs`)

**Función:** `handler(event)`

Genera códigos QR para enlaces de WhatsApp o Telegram basados en parámetros de consulta.

#### Características:
- Genera códigos QR en formato PNG base64
- Soporte para WhatsApp y Telegram
- Parámetros configurables para saltos de línea
- Headers CORS incluidos

#### Parámetros de entrada:
- `contact_number`: Número de teléfono (default: configurado)
- `token`: Token requerido para el enlace
- `enter`: Agrega salto de línea si es "1"
- `telegram`: Usa Telegram si es "1", WhatsApp por defecto

#### Respuesta:
- **200**: Imagen PNG en base64
- **400**: Error de parámetros faltantes
- **500**: Error al generar QR

---

### 2. Siniestro Chatbot (`siniestro/index.mjs`)

**Función:** `handler(event, context)`

Chatbot inteligente que utiliza OpenAI para responder consultas sobre seguros.

#### Características:
- Integración con OpenAI GPT-3.5-turbo
- Cache de sesiones con limpieza automática
- Recarga dinámica de instrucciones
- Gestión de sesiones por usuario

#### Funciones principales:

##### `loadInstructions(filePath)`
Carga instrucciones desde archivo local.

##### `loadInstructionsFromURL(url)`
Carga instrucciones desde URL remota.

##### `reloadInstructions()`
Recarga instrucciones y reinicia cache.

##### `getCompletion(prompt, model)`
Obtiene respuesta de OpenAI con manejo de sesiones.

##### `checkAndClearInactiveSessions()`
Limpia sesiones inactivas (>30 minutos).

#### Comandos especiales:
- `"siniestro:reborn"`: Reinicia el bot con nuevas instrucciones

---

### 3. Telegram Bot (`telegram/lambda_function.py`)

**Función:** `lambda_handler(event, context)`

Bot principal de Telegram para cotizaciones de seguros de salud con flujo conversacional completo.

#### Características:
- Flujo completo de cotización de seguros
- Integración con DynamoDB para persistencia
- Múltiples roles (usuario, admin, developer, master)
- Gestión de documentos y archivos PDF
- Integración con servicios de ChatGPT y Gandalf

#### Funciones principales:

##### Gestión de usuarios:
- `guardar_usuario(user_id, user_data)`: Guarda datos en DynamoDB
- `recuperar_usuario(user_id)`: Recupera datos de usuario

##### Validaciones:
- `correo_es_valido(correo)`: Valida formato de email
- `validar_fecha(cadena_fecha)`: Valida y convierte fechas
- `fecha_sql(cadena_fecha)`: Convierte a formato SQL
- `parentesco_valido(cadena)`: Valida relaciones familiares

##### Integraciones externas:
- `pregunta_a_chatgpt(mensaje, model)`: Consulta a ChatGPT
- `pregunta_a_gandalf(mensaje, model)`: Consulta modo desarrollador
- `enviar_mensaje_telegram(...)`: Envía mensajes con formato
- `cotizar(datos)`: Realiza cotizaciones
- `agregar_beneficiario(datos)`: Agrega beneficiarios
- `asignar_a_analista(datos)`: Asigna a analista

##### Gestión de documentos:
- `obtener_documentos(folder_path)`: Lista documentos
- `elegir_documento(categoria, subcategoria, company)`: Selecciona documento
- `generar_pdf(id_cotizacion)`: Genera PDF de cotización

##### Utilidades:
- `obtener_boton(data_json, mensaje)`: Procesa botones
- `dividir_mensaje(mensaje, max_length)`: Divide mensajes largos
- `agregar_opciones(historial, opciones, paso_default)`: Gestiona opciones

#### Estados de conversación:
- `start`: Inicio de conversación
- `askedWelcome`: Solicitando nombre
- `askedBirthdate`: Solicitando fecha nacimiento
- `askedEmail`: Solicitando email
- `askedSex`: Solicitando género
- `askBenefit`: Preguntando por beneficiarios
- `askedParent`: Solicitando parentesco
- `askedFamily`: Procesando familia
- `waitForQuestion`: Esperando pregunta libre
- `additionalHelp`: Preguntando ayuda adicional

#### Roles de usuario:
- **user**: Usuario estándar para cotizaciones
- **admin**: Acceso a documentos administrativos
- **developer**: Acceso a modo Gandalf
- **master**: Acceso completo y entrenamiento

## 🔧 Configuración

### Variables de entorno requeridas:

#### Para qr/index.mjs:
```javascript
const DEFAULT_PHONE = "+YOUR_DEFAULT_PHONE";
const TELEGRAM_BOT = "YOUR_TELEGRAM_BOT";
```

#### Para siniestro/index.mjs:
```javascript
const OPENAI_API_KEY = "YOUR_OPENAI_API_KEY";
const INSTRUCTIONS_URL = "https://YOUR_API_ENDPOINT/whatsapp?bot=siniestro";
```

#### Para telegram/lambda_function.py:
```python
# APIs
CHATGPT_API_ENDPOINT = "https://YOUR_CHATGPT_API_ENDPOINT/chatgpt"
GANDALF_API_ENDPOINT = "https://YOUR_GANDALF_API_ENDPOINT/gandalf"

# Telegram
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
BOT_PHONE_NUMBER = "YOUR_BOT_PHONE_NUMBER"

# Servicios externos
PDF_SERVICE = "https://YOUR_PDF_SERVICE.co"
QUOTE_SERVICE = "https://YOUR_QUOTE_SERVICE.co"
DOCUMENT_SERVICE = "https://YOUR_DOCUMENT_SERVICE.co"
```

### Recursos AWS requeridos:
- **DynamoDB**: Tabla 'telegram' para persistencia de usuarios
- **Lambda**: Funciones con permisos de DynamoDB
- **API Gateway**: Endpoints para webhooks

## 📋 Flujo de trabajo

### Cotización estándar:
1. Usuario saluda → Solicita nombre
2. Solicita fecha nacimiento → Valida formato
3. Solicita email → Valida formato
4. Solicita género → Botones M/F
5. Pregunta por beneficiarios → Agrega familia
6. Genera cotizaciones (2 PDFs con diferentes montos)
7. Ofrece ayuda adicional → ChatGPT libre

### Flujo administrativo:
1. Admin accede → Menú de áreas
2. Selecciona categoría → Subcategoría
3. Selecciona compañía (si aplica)
4. Recibe documento o lista de archivos

## 🛠️ Instalación

### Dependencias Node.js:
```bash
cd qr/ && npm install qrcode cors
cd ../siniestro/ && npm install openai
```

### Dependencias Python:
```bash
pip install boto3
```

## 🔒 Seguridad

- Todas las API keys han sido reemplazadas por placeholders
- Tokens de Telegram protegidos
- Validación de webhook con tokens específicos
- Sanitización de inputs de usuario

## 📊 Monitoreo

- Logs detallados en CloudWatch
- Manejo de errores con respuestas apropiadas
- Timeouts y retry logic para APIs externas

## 🚀 Despliegue

1. Configurar variables de entorno
2. Empaquetar funciones Lambda
3. Configurar API Gateway
4. Configurar webhooks de Telegram
5. Configurar DynamoDB con los permisos apropiados

---



