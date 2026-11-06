(() => {
    // Resizing a card does not emit a window resize event (for example, expansion).
    // Observe the actual card width so Plotly follows its available space.
    if (window.ResizeObserver) {
        const widths = new WeakMap();
        const observer = new ResizeObserver(entries => {
            entries.forEach(({target, contentRect}) => {
                if (contentRect.width <= 0 || widths.get(target) === contentRect.width) return;
                widths.set(target, contentRect.width);
                const plot = target.querySelector(".js-plotly-plot");
                if (plot && window.Plotly) window.Plotly.Plots.resize(plot);
            });
        });
        document.querySelectorAll(".graph-card").forEach(card => observer.observe(card));
    }
    const storageKey = "flight-prediction-history-v1";
    const status = document.getElementById("history-status");
    const body = document.getElementById("history-body");
    let history = [];
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
        if (Array.isArray(saved)) history = saved.filter(item => item && item.inputs && item.result && Number.isFinite(item.result.price)).slice(0, 100);
    } catch {
        status.textContent = "Saved history could not be read. New predictions will appear here.";
    }
    const money = value => new Intl.NumberFormat("en-IN", {style: "currency", currency: "INR", maximumFractionDigits: 2}).format(value);
    function renderHistory() {
        body.replaceChildren();
        if (!history.length) {
            const row = body.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 6;
            cell.textContent = "No saved predictions yet.";
        }
        history.forEach(({timestamp, inputs, result}) => {
            const row = body.insertRow();
            [new Date(timestamp).toLocaleString(), `${inputs.source} → ${inputs.destination}`,
                `${inputs.airline} / ${inputs.class}`, result.model_name, money(result.price),
                `${money(result.range_low)} – ${money(result.range_high)}`].forEach(value => {
                row.insertCell().textContent = value;
            });
        });
        document.getElementById("export-history").disabled = !history.length;
        document.getElementById("clear-history").disabled = !history.length;
    }
    function saveHistory() {
        try {
            localStorage.setItem(storageKey, JSON.stringify(history));
            status.textContent = `${history.length} prediction(s) saved in this browser.`;
        } catch {
            status.textContent = "Browser storage is unavailable. History is kept for this visit; export CSV to save it.";
        }
        renderHistory();
    }
    document.getElementById("clear-history").addEventListener("click", () => {
        history = [];
        saveHistory();
    });
    document.getElementById("export-history").addEventListener("click", () => {
        const headers = ["timestamp", "model", "airline", "source", "destination", "departure_time", "arrival_time", "stops", "class", "duration", "days_left", "price", "range_low", "range_high", "nominal_coverage_pct", "r2", "mae"];
        const escape = value => {
            let text = String(value ?? "");
            if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
            return '"' + text.replaceAll('"', '""') + '"';
        };
        const rows = history.map(item => {
            const values = {...item.inputs, ...item.result, timestamp: item.timestamp};
            return headers.map(key => escape(values[key])).join(",");
        });
        const url = URL.createObjectURL(new Blob(["\uFEFF" + [headers.join(","), ...rows].join("\r\n")], {type: "text/csv;charset=utf-8;"}));
        const link = document.createElement("a");
        link.href = url;
        link.download = "flight-prediction-history.csv";
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    document.getElementById("prediction-form").addEventListener("submit", async event => {
        event.preventDefault();
        const button = document.getElementById("predict-button");
        const result = document.getElementById("result");
        const inputs = Object.fromEntries(["model", "airline", "source", "destination", "departure_time", "arrival_time", "stops", "class", "duration", "days_left"].map(key => [key, document.getElementById(key).value]));
        button.disabled = true;
        result.textContent = "Estimating fare…";
        try {
            const response = await fetch("/predict", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(inputs)});
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Prediction failed.");
            result.replaceChildren();
            for (const [className, text] of [
                ["result-label", "YOUR FARE ESTIMATE"],
                ["fare-amount", money(data.price)],
                ["fare-range", `Estimated ${data.nominal_coverage_pct}% range: ${money(data.range_low)} – ${money(data.range_high)}`],
            ]) {
                const line = document.createElement("span");
                line.className = className;
                line.textContent = text;
                result.appendChild(line);
            }
            history.unshift({timestamp: new Date().toISOString(), inputs, result: data});
            history = history.slice(0, 100);
            saveHistory();
        } catch (error) {
            result.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    });
    renderHistory();
})();
