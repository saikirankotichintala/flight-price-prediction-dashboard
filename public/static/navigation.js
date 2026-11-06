(() => {
    const tabs = Array.from(document.querySelectorAll('[data-tab]'));
    const panels = Array.from(document.querySelectorAll('[role="tabpanel"]'));
    function activate(key, updateUrl = true) {
        const chosen = tabs.find(tab => tab.dataset.tab === key) || tabs[0];
        tabs.forEach(tab => {
            const selected = tab === chosen;
            tab.setAttribute('aria-selected', String(selected));
            tab.tabIndex = selected ? 0 : -1;
        });
        panels.forEach(panel => panel.hidden = panel.id !== chosen.getAttribute('aria-controls'));
        if (updateUrl) {
            const url = new URL(window.location.href);
            url.searchParams.set('view', chosen.dataset.tab);
            window.history.pushState({}, '', url);
        }
        requestAnimationFrame(() => {
            document.querySelectorAll(`#${chosen.getAttribute('aria-controls')} .js-plotly-plot`).forEach(plot => {
                if (window.Plotly) window.Plotly.Plots.resize(plot);
            });
        });
    }
    tabs.forEach((tab, index) => {
        tab.addEventListener('click', event => {
            if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button > 0) return;
            event.preventDefault();
            activate(tab.dataset.tab);
        });
        tab.addEventListener('keydown', event => {
            let next;
            if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
            else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = tabs.length - 1;
            else return;
            event.preventDefault();
            tabs[next].focus();
            activate(tabs[next].dataset.tab);
        });
    });
    window.addEventListener('popstate', () => activate(new URL(window.location.href).searchParams.get('view'), false));
    document.getElementById('sample-flight').addEventListener('click', () => {
        const sample = JSON.parse(document.getElementById('sample-flight-data').textContent);
        Object.entries(sample).forEach(([key, value]) => document.getElementById(key).value = value);
        document.getElementById('result').textContent = 'Sample loaded. Select Predict Price to estimate the fare.';
        syncAirline();
    });
    function syncAirline() {
        document.querySelectorAll('.thumb-btn').forEach(button => {
            button.classList.toggle('active', button.dataset.airline === document.getElementById('airline').value);
        });
    }
    document.getElementById('airline').addEventListener('change', syncAirline);
    document.querySelectorAll('.thumb-btn').forEach(button => button.addEventListener('click', () => {
        document.getElementById('airline').value = button.dataset.airline;
        syncAirline();
    }));
    document.querySelectorAll('.graph-card').forEach(card => card.addEventListener('dblclick', () => {
        card.classList.toggle('expanded-card');
        const plot = card.querySelector('.js-plotly-plot');
        if (plot && window.Plotly) window.Plotly.Plots.resize(plot);
    }));
    syncAirline();
})();
