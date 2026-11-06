const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/dashboard.js', 'utf8');

function setup(saved = new Map(), failStorage = false) {
    const elements = new Map();
    function element() {
        return {textContent: '', value: '', disabled: false, rows: [], handlers: {},
            addEventListener(name, handler) {this.handlers[name] = handler;},
            replaceChildren() {this.rows = []; this.textContent = '';},
            insertRow() {const row = {cells: [], insertCell() {const cell = {}; this.cells.push(cell); return cell;}}; this.rows.push(row); return row;},
            appendChild(child) {this.textContent += child.textContent;}, click() {}, remove() {}};
    }
    for (const id of ['history-status', 'history-body', 'export-history', 'clear-history', 'prediction-form', 'predict-button', 'result', 'model', 'airline', 'source', 'destination', 'departure_time', 'arrival_time', 'stops', 'class', 'duration', 'days_left']) elements.set(id, element());
    const values = {model: 'extra_trees', airline: 'Indigo', source: 'Delhi', destination: 'Mumbai', class: 'Economy', duration: '2', days_left: '4', departure_time: 'Morning', arrival_time: 'Evening', stops: 'zero'};
    Object.entries(values).forEach(([key, value]) => elements.get(key).value = value);
    const result = {model: 'extra_trees', model_name: 'Extra Trees', price: 5000, range_low: 3000, range_high: 7000, nominal_coverage_pct: 90, r2: .95, mae: 1000};
    const downloads = [];
    const context = {Intl, Date, JSON, Number, String, Array, Object, Blob, window: {},
        localStorage: {getItem(key) {if (failStorage) throw Error('unavailable'); return saved.get(key) || null;}, setItem(key, value) {if (failStorage) throw Error('unavailable'); saved.set(key, value);}},
        document: {getElementById: id => elements.get(id), createElement: () => element(), body: element()},
        fetch: async () => ({ok: true, json: async () => result}),
        URL: {createObjectURL(blob) {downloads.push(blob); return 'blob:test';}, revokeObjectURL() {}},
        setTimeout(handler) {handler();}};
    vm.createContext(context);
    vm.runInContext(source, context);
    return {elements, context, saved, downloads, submit: () => elements.get('prediction-form').handlers.submit({preventDefault() {}})};
}

test('prediction history persists, reloads, exports all inputs and clears', async () => {
    const ui = setup();
    await ui.submit();
    assert.match(ui.elements.get('result').textContent, /Estimated 90% range/);
    assert.equal(ui.elements.get('predict-button').disabled, false);
    const records = JSON.parse(ui.saved.get('flight-prediction-history-v1'));
    assert.equal(records.length, 1);
    assert.equal(records[0].inputs.source, 'Delhi');
    const reloaded = setup(ui.saved);
    assert.equal(reloaded.elements.get('history-body').rows.length, 1);
    assert.equal(reloaded.elements.get('export-history').disabled, false);
    reloaded.elements.get('export-history').handlers.click();
    const csv = await reloaded.downloads[0].text();
    assert.match(csv, /nominal_coverage_pct/);
    assert.match(csv, /"Delhi","Mumbai"/);
    reloaded.elements.get('clear-history').handlers.click();
    assert.equal(JSON.parse(ui.saved.get('flight-prediction-history-v1')).length, 0);
    assert.equal(reloaded.elements.get('export-history').disabled, true);
});

test('failed predictions are displayed without saving history', async () => {
    const ui = setup();
    ui.context.fetch = async () => ({ok: false, json: async () => ({error: 'Choose different cities'})});
    await ui.submit();
    assert.equal(ui.elements.get('result').textContent, 'Choose different cities');
    assert.equal(ui.saved.size, 0);
    assert.equal(ui.elements.get('predict-button').disabled, false);
});

test('storage failures preserve session history and CSV export', async () => {
    const ui = setup(new Map(), true);
    await ui.submit();
    assert.match(ui.elements.get('history-status').textContent, /storage is unavailable/);
    assert.equal(ui.elements.get('export-history').disabled, false);
});

test('history is capped at 100 records and export neutralizes formula cells', async () => {
    const ui = setup();
    ui.elements.get('airline').value = '=HYPERLINK("bad")';
    for (let i = 0; i < 102; i++) await ui.submit();
    assert.equal(JSON.parse(ui.saved.get('flight-prediction-history-v1')).length, 100);
    ui.elements.get('export-history').handlers.click();
    assert.match(await ui.downloads[0].text(), /'\=HYPERLINK/);
});
