
const factionColors = {
    "axiom": "#7e4b36",
    "bravos": "#ff1a1a",
    "lyra": "#d12358",
    "muna": "#4c7245",
    "ordis": "#00628b",
    "yzmir": "#483b66",
}

let deckStats = JSON.parse(document.getElementById('faction-distribution').textContent);
deckStats = Object.entries(deckStats).sort((a, b) => b[1] - a[1]);
let labels = deckStats.map((dataPoint) => dataPoint[0]);
let data = deckStats.map((dataPoint) => dataPoint[1]);

let ctx = document.getElementById('deckPieChart').getContext('2d');
let deckPieChart = new Chart(ctx, {
    type: 'pie',
    data: {
        labels: labels,
        datasets: [{
            data: data,
            backgroundColor: Array.from(labels, (faction) => factionColors[faction]),
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: {
                position: 'top',
            },
        }
    }
});