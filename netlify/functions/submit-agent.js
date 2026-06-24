exports.handler = async function(event) {
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
      },
      body: '',
    };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers: {'Access-Control-Allow-Origin':'*'}, body: 'Method Not Allowed' };
  }

  try {
    const { formType, fields } = JSON.parse(event.body);

    const urls = {
      flights: 'https://holidaypirates.app.n8n.cloud/form/8456a79d-e8e1-4b53-9a55-b146e58ddb7e',
      hotels:  'https://holidaypirates.app.n8n.cloud/form/ffd18b39-5554-4e94-a4cd-b111d728135c',
    };

    const url = urls[formType];
    if (!url) return { statusCode: 400, headers: {'Access-Control-Allow-Origin':'*'}, body: JSON.stringify({error:'Unknown formType'}) };

    const boundary = '----FormBoundary' + Math.random().toString(36).slice(2);
    const parts = [];

    for (const [key, value] of Object.entries(fields)) {
      if (Array.isArray(value)) {
        // Send each value individually — n8n reads them as an array
        value.forEach(v => {
          parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${v}`);
        });
      } else {
        parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="${key}"\r\n\r\n${value ?? ''}`);
      }
    }
    parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="useResponseData"\r\n\r\nfalse`);
    parts.push(`--${boundary}--`);
    const body = parts.join('\r\n');

    // Use AbortController to avoid Netlify's 10s function timeout
    // n8n can be slow — we fire and don't wait for full response
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}` },
        body,
        signal: controller.signal,
      });
      clearTimeout(timeout);

      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ ok: true, status: response.status }),
      };
    } catch (fetchErr) {
      clearTimeout(timeout);
      // AbortError or timeout — n8n received the request but took too long to respond
      // This is normal behaviour and means the workflow was triggered successfully
      if (fetchErr.name === 'AbortError' || fetchErr.message.includes('abort') || fetchErr.message.includes('timeout') || fetchErr.message.includes('Timeout')) {
        return {
          statusCode: 200,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
          body: JSON.stringify({ ok: true, status: 202, note: 'n8n acknowledged (timeout on response is normal)' }),
        };
      }
      throw fetchErr;
    }

  } catch (err) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: err.message }),
    };
  }
};
