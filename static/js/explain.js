document.querySelectorAll(".card").forEach(card => {
    card.addEventListener("click", async () => {

        const filmId = card.dataset.id;

        const response = await fetch(`/explain/${filmId}`);
        const data = await response.json();

        const panel = document.getElementById("sidepanel");
        const container = document.getElementById("explain-content");

        const x = data.contributions.map(c => c.feature);
        const y = data.contributions.map(c => c.shap);

        const colors = y.map(v => v > 0 ? "green" : "red");

        const trace = {
            type: "bar",
            x: y,
            y: x,
            orientation: "h",
            marker: { color: colors }
        };

        Plotly.newPlot(container, [trace], {
            title: "Top 10 Contributions",
            paper_bgcolor: "#121212",
            plot_bgcolor: "#121212",
            font: { color: "white" }
        });

        panel.classList.remove("hidden");
    });
});

const positive = data.contributions.filter(c => c.shap > 0);
const negative = data.contributions.filter(c => c.shap < 0);

let text = `Le modèle part d'une probabilité moyenne puis `;

if (positive.length > 0) {
    text += `les variables ${positive.map(p => p.feature).slice(0,3).join(", ")} augmentent la probabilité`;
}

if (negative.length > 0) {
    text += ` tandis que ${negative.map(n => n.feature).slice(0,3).join(", ")} la réduisent.`;
}

container.innerHTML += `<p>${text}</p>`;