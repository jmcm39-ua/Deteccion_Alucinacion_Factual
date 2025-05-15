let chartInstances = {};

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
    const resultadoFinalDiv = document.getElementById('resultado-final');
    const leyendaDiv = document.getElementById('leyenda');
    const leyenda1Div = document.getElementById('leyenda-1');
    const leyenda2Div = document.getElementById('leyenda-2');
    const leyenda3Div = document.getElementById('leyenda-3');
    const leyendaauxDiv = document.getElementById('aux-leyenda');
    const spinner = document.getElementById('spinner');
    const spinnerTexto = document.getElementById('spinner-texto');
    const graficasResumenDiv = document.getElementById('gr-resumen');
    const resumenGlobalDiv = document.getElementById('resumen-global');
    const titulo1Div = document.getElementById('titulo-1');
    const titulo3Div = document.getElementById('titulo-3');
    const resumenTotal = document.getElementById('resumen-total');
    const resumenCorrecta = document.getElementById('resumen-correctas');
    const resumenNeutral = document.getElementById('resumen-neutrales');
    const resumenContradiccion = document.getElementById('resumen-contradicciones');
    const checkboxContradiction = document.getElementById('checkbox-contradiction');
    const checkboxNeutral = document.getElementById('checkbox-neutral');
    const checkboxCorrect = document.getElementById('checkbox-correct');
    const checkboxOpciones = document.getElementById('checkbox-options');
    const checkboxOpcionesAux = document.getElementById('checkbox-options-aux');

    // Ocultar todo y mostrar spinner
    resultadoDiv.style.display = 'none';
    resultadoFinalDiv.style.display = 'none';
    leyendaDiv.style.display = 'none';
    leyenda1Div.style.display = 'none';
    leyenda2Div.style.display = 'none';
    leyenda3Div.style.display = 'none';
    leyendaauxDiv.style.display = 'none';
    graficasResumenDiv.style.display = 'none';
    resumenGlobalDiv.style.display = 'none';
    titulo1Div.style.display = 'none';
    titulo3Div.style.display = 'none';
    spinner.style.display = 'block';
    spinnerTexto.style.display = 'block';
    resumenTotal.style.display = 'none'; 
    resumenCorrecta.style.display = 'none'; 
    resumenNeutral.style.display = 'none'; 
    resumenContradiccion.style.display = 'none'; 
    checkboxNeutral.style.display = 'none';
    checkboxContradiction.style.display = 'none';
    checkboxCorrect.style.display = 'none';
    checkboxOpciones.style.display = 'none';
    checkboxOpcionesAux.style.display = 'none';


    fetch('http://localhost:3000/deteccion/etiquetar', {
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
        leyenda1Div.style.display = 'flex';
        leyenda2Div.style.display = 'flex';
        leyenda3Div.style.display = 'flex';
        leyendaauxDiv.style.display = 'flex';
        resultadoDiv.style.display = 'block';
        checkboxOpciones.style.display = 'flex';
        checkboxOpcionesAux.style.display = 'flex';
        checkboxContradiction.style.display = 'flex';
        checkboxNeutral.style.display = 'flex';
        checkboxCorrect.style.display = 'flex';
        data_original = data.texto_etiquetado;
        resultadoDiv.innerHTML = data.texto_etiquetado;

        // Función para aplicar subrayado basado en las selecciones
        function aplicarSubrayado() {
            // Obtener el contenido del div de resultado
            let contenido = data_original;
        
            // Si el checkbox de contradicción está seleccionado, aplicamos el subrayado correspondiente
            if (checkboxContradiction.checked) {
            contenido = contenido.replace(/(contradicciones)/gi, '<span class="subrayado-contradiction">$1</span>');
            } else {
            // Si no está seleccionado, eliminamos el subrayado de contradicción
            contenido = contenido.replace(/<span class="subrayado-contradiction">(.*?)<\/span>/gi, '$1');
            }
        
            // Si el checkbox de neutral está seleccionado, aplicamos el subrayado correspondiente
            if (checkboxNeutral.checked) {
            contenido = contenido.replace(/(neutrales)/gi, '<span class="subrayado-neutral">$1</span>');
            } else {
            // Si no está seleccionado, eliminamos el subrayado de neutral
            contenido = contenido.replace(/<span class="subrayado-neutral">(.*?)<\/span>/gi, '$1');
            }

            // Si el checkbox de correcto está seleccionado, aplicamos el subrayado correspondiente
            if (checkboxCorrect.checked) {
                contenido = contenido.replace(/(correctas)/gi, '<span class="subrayado-correcto">$1</span>');
                } else {
                // Si no está seleccionado, eliminamos el subrayado de neutral
                contenido = contenido.replace(/<span class="subrayado-correcto">(.*?)<\/span>/gi, '$1');
                }
              // Actualizar el HTML con el contenido modificado
            resultadoDiv.innerHTML = contenido;
        }

        // Llamar a la función cada vez que se cambie el estado de los checkboxes
        checkboxContradiction.addEventListener('change', aplicarSubrayado);
        checkboxNeutral.addEventListener('change', aplicarSubrayado);
        checkboxCorrect.addEventListener('change',aplicarSubrayado);

        // Inicializar la función para aplicar el subrayado al cargar
        aplicarSubrayado();
        

        const correctas = data.n_entailment;
        const neutrales = data.n_neutral;
        const contradicciones = data.n_contradiccion;
        const total = correctas + neutrales + contradicciones;

        const porcentajeCorrectas = (correctas / total) * 100;
        const porcentajeNeutrales = (neutrales / total) * 100;
        const porcentajeContradicciones = (contradicciones / total) * 100;

        let mensaje = "";
        let color = "";

        if (porcentajeCorrectas > porcentajeNeutrales && porcentajeCorrectas > porcentajeContradicciones && porcentajeContradicciones < 30) {
            mensaje = "¡Todo correcto! No se ha detectado anomalías en el texto.";
            color = "green";
        } else if (porcentajeNeutrales > porcentajeCorrectas && porcentajeNeutrales > porcentajeContradicciones) {
            mensaje = "¡Cuidado! No se ha podido verificar completamente el texto.";
            color = "orange";
        } else {
            mensaje = "¡Alerta! Se ha detectado información no fiable en el texto introducido."
            color = "red";
        }

        resultadoFinalDiv.style.display = "flex";
        resultadoFinalDiv.innerHTML = mensaje;
        resultadoFinalDiv.style.color = color;

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
                labels: ['Correctas', 'Sin Determinar', 'Contradicciones'],
                datasets: [{
                    data: [correctas, neutrales, contradicciones],
                    backgroundColor: ['#a8e0a8', '#f0e68c', '#F28B82'],
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

        resumenTotal.style.display = 'flex'; 
        resumenCorrecta.style.display = 'block'; 
        resumenNeutral.style.display = 'block'; 
        resumenContradiccion.style.display = 'block'; 
        resumenTotal.textContent = `Total de oraciones analizadas: ${total}`;
        resumenCorrecta.textContent = `Correctas: ${correctas} (${porcentajeCorrectas.toFixed(2)}%)`;
        resumenNeutral.textContent = `Sin determinar: ${neutrales} (${porcentajeNeutrales.toFixed(2)}%)`;
        resumenContradiccion.textContent = `Contradicciones: ${contradicciones} (${porcentajeContradicciones.toFixed(2)}%)`;

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
