// Dashboard JavaScript - Carga y visualización de datos

// Cargar datos al iniciar
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadLatestAnalysis();
    loadHistoricalChart();
    
    // Actualizar cada 30 segundos
    setInterval(() => {
        loadStats();
        loadLatestAnalysis();
        loadHistoricalChart();
    }, 30000);
});

// Cargar estadísticas generales
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        document.getElementById('total-analyses').textContent = stats.total_analyses || '0';
        document.getElementById('total-coins').textContent = stats.total_unique_coins || '0';
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

// Cargar último análisis
async function loadLatestAnalysis() {
    try {
        const response = await fetch('/api/latest');
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('latest-analysis').innerHTML = 
                `<p class="loading">No hay datos disponibles aún</p>`;
            return;
        }
        
        // Actualizar sentimiento y fear & greed
        document.getElementById('sentiment').textContent = data.sentiment || '-';
        document.getElementById('fear-greed').textContent = data.fear_greed_index || '-';
        
        // Mostrar detalles del análisis
        const analysisHTML = `
            <p><strong>📅 Fecha:</strong> ${new Date(data.timestamp).toLocaleString('es-ES')}</p>
            <p><strong>💰 Monedas Analizadas:</strong> ${data.coins_analyzed}</p>
            <p><strong>😊 Sentimiento:</strong> ${data.sentiment}</p>
            <p><strong>📊 Fear & Greed Index:</strong> ${data.fear_greed_index}/100</p>
            <p><strong>🤖 Recomendación IA:</strong></p>
            <p style="background: white; padding: 15px; border-radius: 8px; margin-top: 10px;">
                ${data.ai_recommendation || 'No disponible'}
            </p>
        `;
        
        document.getElementById('latest-analysis').innerHTML = analysisHTML;
        
        // Mostrar top monedas
        if (data.coins && data.coins.length > 0) {
            displayTopCoins(data.coins);
        }
        
    } catch (error) {
        console.error('Error cargando último análisis:', error);
        document.getElementById('latest-analysis').innerHTML = 
            `<p class="loading">Error cargando datos</p>`;
    }
}

// Mostrar top monedas
function displayTopCoins(coins) {
    const topCoins = coins.slice(0, 6); // Top 6
    
    const coinsHTML = topCoins.map(coin => {
        const change24Class = coin.change_24h >= 0 ? 'positive' : 'negative';
        const change2Class = coin.change_2h >= 0 ? 'positive' : 'negative';
        const arrow24 = coin.change_24h >= 0 ? '📈' : '📉';
        const arrow2 = coin.change_2h >= 0 ? '📈' : '📉';
        
        return `
            <div class="coin-card">
                <div class="coin-symbol">${coin.symbol}</div>
                <div class="coin-price">💰 $${parseFloat(coin.price).toFixed(2)}</div>
                <div class="coin-change ${change24Class}">
                    ${arrow24} 24h: ${parseFloat(coin.change_24h).toFixed(2)}%
                </div>
                <div class="coin-change ${change2Class}">
                    ${arrow2} 2h: ${parseFloat(coin.change_2h).toFixed(2)}%
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('top-coins').innerHTML = coinsHTML;
}

// Cargar gráfico histórico
let historicalChart = null;

async function loadHistoricalChart() {
    try {
        const response = await fetch('/api/historical/30');
        const data = await response.json();
        
        if (!data || data.length === 0) {
            return;
        }
        
        const ctx = document.getElementById('historicalChart').getContext('2d');
        
        // Destruir gráfico anterior si existe
        if (historicalChart) {
            historicalChart.destroy();
        }
        
        historicalChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => new Date(d.timestamp).toLocaleDateString('es-ES')),
                datasets: [{
                    label: 'Fear & Greed Index',
                    data: data.map(d => d.fear_greed_index),
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Índice (0-100)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Fecha'
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error cargando gráfico histórico:', error);
    }
}
