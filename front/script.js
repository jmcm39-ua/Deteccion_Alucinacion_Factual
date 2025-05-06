let chartInstances = {};

// Crear el IntersectionObserver para las gráficas
const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

const graficos = document.querySelectorAll('.grafico');
graficos.forEach(grafico => observer.observe(grafico));

// Función para crear gráficos individuales
function crearGrafico(id, label, porcentaje, color) {
    const ctx = document.getElementById(id).getContext('2d');

    if (chartInstances[id]) {
        chartInstances[id].destroy();
    }

    chartInstances[id] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: [label, 'Otro'],
            datasets: [{
                data: [porcentaje, 100 - porcentaje],
                backgroundColor: [color, '#d3d3d3'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            animation: {
                duration: 1500,
                easing: 'easeOutBounce',
                animateRotate: true,
                animateScale: true
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (tooltipItem) {
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

document.getElementById('enviarBtn').addEventListener('click', function () {
    const texto = document.getElementById('textoInput').value;
    const resultadoDiv = document.getElementById('resultado');
    const leyendaDiv = document.getElementById('leyenda');
    const leyendaauxDiv = document.getElementById('aux-leyenda');
    const spinner = document.getElementById('spinner');
    const spinnerTexto = document.getElementById('spinner-texto');
    const graficasDiv = document.getElementById('gráficas');
    const graficasCorrectasDiv = document.getElementById('gr-correcta');
    const graficasNeutralesDiv = document.getElementById('gr-neutral');
    const graficasResumenDiv = document.getElementById('gr-resumen');
    const graficasIncorrectasDiv = document.getElementById('gr-mal');
    const resumenGlobalDiv = document.getElementById('resumen-global');
    const titulo1Div = document.getElementById('titulo-1');
    const titulo2Div = document.getElementById('titulo-2');
    const titulo3Div = document.getElementById('titulo-3');

    // Ocultar todo y mostrar spinner
    resultadoDiv.style.display = 'none';
    leyendaDiv.style.display = 'none';
    leyendaauxDiv.style.display = 'none';
    graficasDiv.style.display = 'none';
    graficasCorrectasDiv.style.display = 'none';
    graficasNeutralesDiv.style.display = 'none';
    graficasIncorrectasDiv.style.display = 'none';
    graficasResumenDiv.style.display = 'none';
    resumenGlobalDiv.style.display = 'none';
    titulo1Div.style.display = 'none';
    titulo2Div.style.display = 'none';
    titulo3Div.style.display = 'none';
    spinner.style.display = 'block';
    spinnerTexto.style.display = 'block';

    fetch('http://localhost:3000/api/etiquetar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: texto })
    })
    .then(response => response.json())
    .then(data => {
        spinner.style.display = 'none';
        spinnerTexto.style.display = 'none';

        titulo1Div.style.display = 'block';
        leyendaDiv.style.display = 'flex';
        leyendaauxDiv.style.display = 'flex';
        resultadoDiv.style.display = 'block';

        resultadoDiv.innerHTML = data.texto_etiquetado;

        titulo2Div.style.display = 'block';
        graficasDiv.style.display = 'block';
        graficasCorrectasDiv.style.display = 'block';
        graficasIncorrectasDiv.style.display = 'block';
        graficasNeutralesDiv.style.display = 'block';

        const correctas = data.n_entailment;
        const neutrales = data.n_neutral;
        const contradicciones = data.n_contradiccion;
        const total = correctas + neutrales + contradicciones;

        const porcentajeCorrectas = (correctas / total) * 100;
        const porcentajeNeutrales = (neutrales / total) * 100;
        const porcentajeContradicciones = (contradicciones / total) * 100;

        crearGrafico('graficoCorrectas', 'Correctas', porcentajeCorrectas, '#a8e0a8');
        crearGrafico('graficoNeutrales', 'Neutrales', porcentajeNeutrales, '#f0e68c');
        crearGrafico('graficoContradicciones', 'Contradicciones', porcentajeContradicciones, '#add8e6');

        // ✅ Mostrar y generar resumen global
        graficasResumenDiv.style.display = 'block';
        resumenGlobalDiv.style.display = 'flex';
        titulo3Div.style.display = 'flex';

        if (chartInstances['graficoResumen']) {
            chartInstances['graficoResumen'].destroy();
        }
        const ctxResumen = document.getElementById('graficoResumen').getContext('2d');
        chartInstances['graficoResumen'] = new Chart(ctxResumen, {
            type: 'doughnut',
            data: {
                labels: ['Correctas', 'Neutrales', 'Contradicciones'],
                datasets: [{
                    data: [correctas, neutrales, contradicciones],
                    backgroundColor: ['#a8e0a8', '#f0e68c', '#add8e6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                animation: {
                    duration: 1500,
                    easing: 'easeOutBounce',
                    animateRotate: true,
                    animateScale: true
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (tooltipItem) {
                                const valor = tooltipItem.raw;
                                const porcentaje = (valor / total * 100).toFixed(2);
                                return `${tooltipItem.label}: ${porcentaje}% (${valor})`;
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

        // Rellenar datos de resumen textual
        document.getElementById('resumen-total').textContent = `Total de oraciones analizadas: ${total}`;
        document.getElementById('resumen-correctas').textContent = `Correctas (entailment): ${correctas} (${porcentajeCorrectas.toFixed(2)}%)`;
        document.getElementById('resumen-neutrales').textContent = `Neutrales: ${neutrales} (${porcentajeNeutrales.toFixed(2)}%)`;
        document.getElementById('resumen-contradicciones').textContent = `Contradicciones: ${contradicciones} (${porcentajeContradicciones.toFixed(2)}%)`;
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
