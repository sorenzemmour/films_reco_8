(() => {
  function showPanel(html) {
    const panel = document.getElementById("sidepanel");
    const container = document.getElementById("explain-content");
    if (!panel || !container) {
      console.error("[explain] sidepanel ou explain-content introuvable");
      return null;
    }
    container.innerHTML = html;
    panel.classList.remove("hidden");
    return { panel, container };
  }

  async function fetchExplain(filmId) {
    const res = await fetch(`/explain/${filmId}`, {
      headers: { "Accept": "application/json" }
    });

    // Si l'API renvoie une page HTML (erreur), res.json() plante => on gère proprement
    const ct = (res.headers.get("content-type") || "").toLowerCase();

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API ${res.status} ${res.statusText}\n${text.slice(0, 400)}`);
    }

    if (!ct.includes("application/json")) {
      const text = await res.text();
      throw new Error(`Réponse non-JSON (content-type: ${ct})\n${text.slice(0, 400)}`);
    }

    return await res.json();
  }

  function buildHelpText(data) {
    const positive = data.contributions.filter(c => c.shap > 0).slice(0, 3);
    const negative = data.contributions.filter(c => c.shap < 0).slice(0, 3);

    let text = `Le modèle part d’une <b>valeur de référence</b> (baseline), puis chaque feature ajoute ou retire une contribution.`;

    if (positive.length > 0) {
      text += ` Ici, <b>${positive.map(p => p.feature).join(", ")}</b> augmentent la probabilité “Must Watch”.`;
    }
    if (negative.length > 0) {
      text += ` À l’inverse, <b>${negative.map(n => n.feature).join(", ")}</b> la réduisent (poussent vers “Skip”).`;
    }

    return `<p style="opacity:.9; line-height:1.45; margin:.5rem 0 1rem 0;">${text}</p>`;
  }

  function renderExplain(data) {
    // Structure panneau + zone plot
    showPanel(`
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
        <h2 style="margin:0;font-size:1.1rem;">Explication</h2>
        <button id="close-panel"
          style="background:#444;color:white;border:0;padding:6px 10px;border-radius:6px;cursor:pointer;">
          Fermer
        </button>
      </div>

      <p style="margin:.5rem 0 0 0;">
        Prédiction: <b>${data.prediction_label}</b> — Proba Must Watch: <b>${(data.prediction_proba * 100).toFixed(1)}%</b>
      </p>

      ${buildHelpText(data)}

      <div id="plot" style="height:420px;"></div>

      <h3 style="margin:16px 0 8px 0; font-size:1rem;">Top 10 contributions</h3>
      <div id="table"></div>
    `);

    document.getElementById("close-panel")?.addEventListener("click", () => {
      document.getElementById("sidepanel")?.classList.add("hidden");
    });

    // Plotly
    if (typeof Plotly === "undefined") {
      document.getElementById("plot").innerHTML =
        `<p style="color:#ff6b6b;">Plotly n’est pas chargé (CDN bloqué ou script manquant).</p>`;
      return;
    }

    const features = data.contributions.map(c => c.feature).reverse();
    const shapVals = data.contributions.map(c => c.shap).reverse();
    const colors = shapVals.map(v => (v > 0 ? "green" : "red"));

    Plotly.newPlot("plot", [{
      type: "bar",
      x: shapVals,
      y: features,
      orientation: "h",
      marker: { color: colors }
    }], {
      title: "Contributions SHAP (Top 10)",
      paper_bgcolor: "#1E1E1E",
      plot_bgcolor: "#1E1E1E",
      font: { color: "white" },
      margin: { l: 180, r: 20, t: 50, b: 40 }
    }, { displayModeBar: false });

    // Table valeurs
    const rows = data.contributions.map(c => `
      <tr>
        <td style="padding:6px;border-bottom:1px solid #333;">${c.feature}</td>
        <td style="padding:6px;border-bottom:1px solid #333;">${c.value}</td>
        <td style="padding:6px;border-bottom:1px solid #333;">${Number(c.shap).toFixed(5)}</td>
      </tr>
    `).join("");

    document.getElementById("table").innerHTML = `
      <table style="width:100%;border-collapse:collapse;font-size:.9rem;">
        <thead>
          <tr>
            <th style="text-align:left;padding:6px;border-bottom:1px solid #333;">Feature</th>
            <th style="text-align:left;padding:6px;border-bottom:1px solid #333;">Valeur</th>
            <th style="text-align:left;padding:6px;border-bottom:1px solid #333;">SHAP</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  // Event delegation : marche même si le DOM change
  document.addEventListener("click", async (e) => {
    const card = e.target.closest(".card");
    if (!card) return;

    const filmId = card.dataset.id;
    console.log("[explain] clicked filmId:", filmId);

    if (!filmId) {
      showPanel(`<p style="color:#ff6b6b;">Erreur: data-id manquant sur cette carte.</p>`);
      return;
    }

    showPanel(`<p>Chargement… (film ${filmId})</p>`);

    try {
      const data = await fetchExplain(filmId);
      renderExplain(data);
    } catch (err) {
      console.error("[explain] error", err);
      showPanel(`<pre style="white-space:pre-wrap;color:#ff6b6b;">${String(err)}</pre>`);
    }
  });
})();