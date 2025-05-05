const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { spawn } = require('child_process');

const app = express();
app.use(cors());
app.use(bodyParser.json());

app.post('/api/etiquetar', (req, res) => {
    const texto = req.body.texto;
    console.log('Solicitud recibida: /api/etiquetar');
    console.log('Texto recibido:', texto);

    // Aquí se añade un argumento para silenciar los warnings en Python
    const python = spawn('python3', ['-W', 'ignore', '../scripts/script.py']); // -W ignore para ignorar los warnings

    let data = '';
    let error = '';

    python.stdout.on('data', (chunk) => {
        data += chunk;
    });

    python.stderr.on('data', (chunk) => {
        // Filtramos las advertencias de los modelos (como el de roberta-large-mnli)
        if (chunk.toString().includes("Some weights of the model checkpoint")) {
            // Solo lo ignoramos si contiene el mensaje de advertencia específico
            console.log("Advertencia ignorada: ", chunk.toString());
        } else {
            error += chunk;  // Solo agregar otros errores reales
        }
    });

    python.on('close', (code) => {
        if (code !== 0 || error) {
            console.error('Error en script Python:', error);
            return res.status(500).json({ error: 'Error al procesar texto.' });
        }

        try {
            const resultado = JSON.parse(data);
            res.json(resultado);
        } catch (e) {
            console.error('Error al parsear JSON:', e);
            res.status(500).json({ error: 'Respuesta inválida del script Python.' });
        }
    });

    python.stdin.write(texto);
    python.stdin.end();
});

app.listen(3000, () => {
    console.log('Servidor API en puerto 3000');
});
