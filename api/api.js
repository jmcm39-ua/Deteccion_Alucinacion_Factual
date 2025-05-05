const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors'); // Importa el paquete cors

const app = express();
app.use(cors()); // Agrega el middleware cors
app.use(bodyParser.json());

app.post('/api/etiquetar', (req, res) => {
    const texto = req.body.texto;
    const modelo = req.body.modelo;
    console.log('Solicitud recibida: /api/etiquetar');
    console.log('Texto recibido:', texto);
    console.log('Modelo seleccionado:', modelo);

    const palabras = texto.split(' ');
    const resultado = palabras.map(palabra => ({
        texto: palabra,
        subrayado: Math.random() < 0.5 // Aquí podrías usar el modelo
    }));

    console.log('Respuesta enviada:', resultado);
    res.json(resultado);
});


app.listen(3000, () => {
    console.log('Servidor API en puerto 3000');
});