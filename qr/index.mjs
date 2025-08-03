import http from 'http';
import url from 'url';
import cors from 'cors';
import qrcode from 'qrcode';

/**
 * AWS Lambda handler para generar códigos QR
 * 
 * Esta función lambda genera códigos QR para enlaces de WhatsApp o Telegram
 * basados en los parámetros de consulta proporcionados.
 * 
 * @param {Object} event - Evento de AWS Lambda que contiene queryStringParameters
 * @returns {Object} Respuesta HTTP con el código QR en formato base64 o mensaje de error
 */
export const handler = async (event) => {
  console.log("Event received:", JSON.stringify(event));

  const { contact_number = "+YOUR_DEFAULT_PHONE", token, enter = "0", telegram = "0"} = event.queryStringParameters;

  if (!contact_number || !token) {
    return {
      statusCode: 400,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
      },
      body: JSON.stringify({ error: "token and contact_number are required" }),
    };
  }

  const encodedToken = encodeURIComponent(token);
  var botURL = `https://api.whatsapp.com/send?phone=${contact_number}&text=${encodedToken}`;

  if (telegram === '1') {
    botURL = `http://t.me/YOUR_TELEGRAM_BOT?start=${token}`;
  }
  
  if (enter === '1') {
    botURL += '%0A';
  }

  try {
    // Generate the QR code
    const buffer = await qrcode.toBuffer(botURL);

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "image/png",
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        "Content-Disposition": `attachment; filename="qr.png"`,
      },
      body: buffer.toString("base64"),
      isBase64Encoded: true,
    };
  } catch (error) {
    console.error("Error generating QR code:", error);
    return {
      statusCode: 500,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
      },
      body: JSON.stringify({ error: "Error generating QR code" }),
    };
  }
};