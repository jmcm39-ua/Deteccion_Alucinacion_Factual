let chartInstances = {};  // Variable global para almacenar los gráficos

document.getElementById('enviarBtn').addEventListener('click', function () {
    const texto = document.getElementById('textoInput').value;
    const resultadoDiv = document.getElementById('resultado');
    const leyendaDiv = document.getElementById('leyenda');
    const resumenDiv = document.getElementById('resumen');
    const spinner = document.getElementById('spinner');
    const spinnerTexto = document.getElementById('spinner-texto');
    const graficasDiv = document.getElementById('gráficas');

    // Ocultar todo y mostrar spinner
    resultadoDiv.style.display = 'none';
    resumenDiv.style.display = 'none';
    leyendaDiv.style.display = 'none';
    graficasDiv.style.display = 'none';
    spinner.style.display = 'block';
    spinnerTexto.style.display = 'block';

    fetch('http://localhost:3000/api/etiquetar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: texto })
    })
    .then(response => response.json())
    .then(data => {
        // Ocultar spinner y mostrar los elementos en el orden adecuado
        spinner.style.display = 'none';
        spinnerTexto.style.display = 'none';

        // Primero mostrar la leyenda
        leyendaDiv.style.display = 'flex';

        // Luego mostrar el texto etiquetado
        resultadoDiv.style.display = 'block';

        // Finalmente mostrar los resultados
        resumenDiv.style.display = 'block';

        // Rellenar el contenido de los resultados
        resultadoDiv.innerHTML = data.texto_etiquetado;
        resumenDiv.innerHTML = `
            <p>Total de oraciones: ${data.total_oraciones}</p>
            <p style="color: #f39c12">Neutrales: ${data.n_neutral}</p>
            <p style="color: red">Contradicciones: ${data.n_contradiccion}</p>
            <p style="color: green">Correctas (Entailment): ${data.n_entailment}</p>
        `;

        // Mostrar las gráficas
        graficasDiv.style.display = 'block';

        // Preparar los datos para las gráficas
        const correctas = data.n_entailment;
        const neutrales = data.n_neutral;
        const contradicciones = data.n_contradiccion;
        const total = correctas + neutrales + contradicciones;

        // Convertir a porcentajes
        const porcentajeCorrectas = (correctas / total) * 100;
        const porcentajeNeutrales = (neutrales / total) * 100;
        const porcentajeContradicciones = (contradicciones / total) * 100;

        // Crear los gráficos
        crearGrafico('graficoCorrectas', 'Correctas', porcentajeCorrectas, '#a8e0a8');
        crearGrafico('graficoNeutrales', 'Neutrales', porcentajeNeutrales, '#f0e68c');
        crearGrafico('graficoContradicciones', 'Contradicciones', porcentajeContradicciones, '#add8e6');
    })
    .catch(error => {
        console.error('Error:', error);
        spinner.style.display = 'none';
        spinnerTexto.style.display = 'none';
        resultadoDiv.style.display = 'block';
        leyendaDiv.style.display = 'flex';
        resultadoDiv.innerHTML = 'Error al obtener el texto etiquetado.';
    });
});

// Función para crear los gráficos
function crearGrafico(id, label, porcentaje, color) {
    const ctx = document.getElementById(id).getContext('2d');

    // Si ya existe un gráfico, destruirlo antes de crear uno nuevo
    if (chartInstances[id]) {
        chartInstances[id].destroy();
    }

    // Crear el nuevo gráfico
    chartInstances[id] = new Chart(ctx, {
        type: 'doughnut', // Usar gráfico tipo doughnut
        data: {
            labels: [label, 'Otro'],  // Ahora tiene la etiqueta "Otro"
            datasets: [{
                data: [porcentaje, 100 - porcentaje],
                backgroundColor: [color, '#d3d3d3'], // Color gris pastel para "Otro"
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            animation: {
                duration: 1500, // Duración de la animación
                easing: 'easeOutBounce',
                animateRotate: true, // Animación de rotación
                animateScale: true   // Animación de escala
            },
            cutout: '70%', // Para hacer el gráfico más "hueco" y redondeado
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            // Siempre mostrar el porcentaje
                            return tooltipItem.raw.toFixed(2) + '%';
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                }
            }
        }
    });
}
