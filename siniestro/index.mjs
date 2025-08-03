import path from 'path';
import https from 'https';
import * as fs from 'fs/promises';

/**
 * Carga instrucciones desde un archivo local
 * 
 * @param {string} filePath - Ruta del archivo de instrucciones
 * @returns {string} Contenido del archivo de instrucciones
 */
async function loadInstructions(filePath) {
  try {
    const instructions = await fs.readFile(filePath, 'utf8');
    return instructions;
  } catch (error) {
    console.error('Error al cargar las instrucciones:', error);
    throw error;
  }
}

const OPENAI_API_KEY = "YOUR_OPENAI_API_KEY";

import { OpenAI } from "openai";

let openai = new OpenAI({
    apiKey: OPENAI_API_KEY,
});

let sessionCache = {};

/**
 * Carga instrucciones desde una URL remota
 * 
 * @param {string} url - URL desde donde cargar las instrucciones
 * @returns {Promise<string>} Contenido de las instrucciones
 */
async function loadInstructionsFromURL(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (resp) => {
            let data = '';

            // Un trozo de datos ha sido recibido.
            resp.on('data', (chunk) => {
                data += chunk;
            });

            // Toda la respuesta ha sido recibida.
            resp.on('end', () => {
                resolve(data);
            });

        }).on("error", (err) => {
            console.error('Error al cargar las instrucciones:', err);
            reject(err);
        });
    });
}

let instrucciones = '';

/**
 * Recarga las instrucciones desde la URL y reinicia el cache de sesión
 */
async function reloadInstructions() {
    try {
        instrucciones = await loadInstructionsFromURL("https://YOUR_API_ENDPOINT/whatsapp?bot=siniestro");
        sessionCache = {};
        openai = new OpenAI({ apiKey: OPENAI_API_KEY });
        console.log('Instrucciones recargadas y objeto OpenAI reiniciado');
    } catch (error) {
        console.error('Error al obtener las instrucciones desde la URL:', error);
    }
}

try {
    instrucciones = await loadInstructionsFromURL("https://YOUR_API_ENDPOINT/whatsapp?bot=siniestro");
} catch (error) {
    console.error('Error al obtener las instrucciones desde la URL:', error);
}

/**
 * Obtiene una respuesta completada de OpenAI
 * 
 * @param {string} prompt - El prompt a enviar a OpenAI
 * @param {string} model - El modelo de OpenAI a usar (por defecto gpt-3.5-turbo)
 * @returns {Promise<string>} La respuesta generada por OpenAI
 */
const getCompletion = async (prompt, model = "gpt-3.5-turbo") => {

    if (prompt == "siniestro:reborn") {
        await reloadInstructions();
        return "Siniestro ha sido reiniciado con exito";
    }

    const now = new Date();
    let sessionId=1;
    if (!sessionCache[sessionId]) {
        sessionCache[sessionId] = {
            messages: [{ role: "system", content: instrucciones }],
            lastAccessed: now
        };
        // console.log("No hay sesión activa: Instrucciones iniciales proporcionadas");
    } else {
        sessionCache[sessionId].lastAccessed = now;
        // console.log("Sesión activa");
    }

    sessionCache[sessionId].messages.push({ role: "user", content: prompt });

    try {
        const response = await openai.chat.completions.create({
            model: model,
            messages: sessionCache[sessionId].messages,
        });
        
        sessionCache[sessionId].messages.push({ role: "assistant", content: response.choices[0].message.content });

        return response.choices[0].message.content;
    } catch (error) {
        console.error("Error al obtener respuesta de OpenAI:", error);
        throw error;
    }
};

/**
 * Verifica y limpia sesiones inactivas del cache
 * Elimina mensajes de sesiones que han estado inactivas por más de 30 minutos
 */
const checkAndClearInactiveSessions = () => {
    const now = new Date();
    Object.keys(sessionCache).forEach(sessionId => {
        const session = sessionCache[sessionId];
        const minutesInactive = (now - session.lastAccessed) / 1000 / 60;
        if (minutesInactive > 30) {
            const systemMessages = session.messages.filter(message => message.role === "system");
            sessionCache[sessionId] = {
                messages: systemMessages,
                lastAccessed: now
            };
        }
    });
};

/**
 * AWS Lambda handler principal para procesar mensajes del chatbot Siniestro
 * 
 * @param {Object} event - Evento de AWS Lambda con el cuerpo de la solicitud
 * @param {Object} context - Contexto de AWS Lambda
 * @returns {Object} Respuesta HTTP con la respuesta del chatbot
 */
const handler = async (event, context) => {
    
    console.log('Evento completo:', JSON.stringify(event, null, 2));

    const prompt = JSON.parse(event.body).message;

    if (!prompt) {
      return {
        statusCode: 400,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*', // Ajusta esto según tu política de CORS
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        body: 'Parámetros de consulta no válidos'
      };
    }    

    try {
        const response = await getCompletion(prompt);
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*', // Ajusta esto según tu política de CORS
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            body: JSON.stringify({ reply: response })
        };
    } catch (error) {
        console.error("Error al procesar la solicitud:", error);
        return {
            statusCode: 500,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*', // Ajusta esto según tu política de CORS
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            body: JSON.stringify({ error: "Error al procesar la solicitud" })
        };
    }
};

export { handler };

setInterval(checkAndClearInactiveSessions, 5 * 60 * 1000);