document.getElementById('enviarBtn').addEventListener('click', function() {
    const texto = document.getElementById('textoInput').value;
    const modelo = parseInt(document.getElementById('modeloSelect').value); // Nuevo
    const resultadoDiv = document.getElementById('resultado');
    const leyendaDiv = document.getElementById('leyenda');

    resultadoDiv.innerHTML = 'Cargando...';
    resultadoDiv.style.display = 'block';
    leyendaDiv.style.display = 'flex';

    fetch('http://localhost:3000/api/etiquetar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ texto: texto, modelo: modelo }) // Incluir modelo
    })
    .then(response => response.json())
    .then(data => {
        let textoEtiquetado = '';
        data.forEach((item, index) => {
            if (item.subrayado) {
                textoEtiquetado += `<span class="subrayado">${item.texto}</span>`;
            } else {
                textoEtiquetado += item.texto;
            }
            if (index < data.length - 1) {
                textoEtiquetado += ' ';
            }
        });
        resultadoDiv.innerHTML = textoEtiquetado;
    })
    .catch(error => {
        console.error('Error:', error);
        resultadoDiv.innerHTML = 'Error al obtener el texto etiquetado.';
    });
});