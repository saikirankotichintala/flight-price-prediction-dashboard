const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup() {
    const keys = ['dashboard', 'analytics', 'history'];
    const tabs = keys.map(key => ({dataset: {tab: key}, attributes: {'aria-controls': `panel-${key}`}, handlers: {},
        addEventListener(name, handler) {this.handlers[name] = handler;},
        getAttribute(name) {return this.attributes[name];}, setAttribute(name, value) {this.attributes[name] = value;},
        focus() {this.focused = true;}}));
    const panels = keys.map(key => ({id: `panel-${key}`, hidden: key !== 'dashboard'}));
    const elements = Object.fromEntries(['sample-flight', 'sample-flight-data', 'result', 'airline', 'source', 'destination'].map(key => [key, {handlers: {}, value: '', addEventListener(name, handler) {this.handlers[name] = handler;}}]));
    elements['sample-flight-data'].textContent = JSON.stringify({airline: 'Indigo', source: 'Delhi', destination: 'Mumbai'});
    const events = {};
    const resized = [];
    const window = {location: {href: 'http://localhost:5000/?airline=Indigo'},
        history: {pushState(_state, _title, url) {window.location.href = String(url);}},
        addEventListener(name, handler) {events[name] = handler;}, Plotly: {Plots: {resize(plot) {resized.push(plot);}}}};
    const document = {getElementById: key => elements[key], querySelectorAll(selector) {
        if (selector === '[data-tab]') return tabs;
        if (selector === '[role="tabpanel"]') return panels;
        if (selector.startsWith('#panel-analytics ')) return ['plot'];
        return [];
    }};
    vm.runInNewContext(fs.readFileSync('static/navigation.js', 'utf8'), {window, document, URL, requestAnimationFrame: fn => fn()});
    const event = overrides => ({button: 0, preventDefault() {this.prevented = true;}, ...overrides});
    return {tabs, panels, window, events, elements, resized, event};
}

test('tabs reveal one panel, preserve filters and resize visible charts', () => {
    const ui = setup();
    ui.tabs[1].handlers.click(ui.event());
    assert.equal(ui.panels[1].hidden, false);
    assert.equal(ui.panels.filter(panel => !panel.hidden).length, 1);
    assert.equal(ui.tabs[1].attributes['aria-selected'], 'true');
    assert.equal(ui.tabs[0].tabIndex, -1);
    assert.match(ui.window.location.href, /airline=Indigo/);
    assert.match(ui.window.location.href, /view=analytics/);
    assert.deepEqual(ui.resized, ['plot']);
});

test('keyboard navigation and browser history maintain the selected tab', () => {
    const ui = setup();
    ui.tabs[0].handlers.keydown(ui.event({key: 'End'}));
    assert.equal(ui.tabs[2].focused, true);
    assert.equal(ui.panels[2].hidden, false);
    ui.tabs[2].handlers.keydown(ui.event({key: 'ArrowRight'}));
    assert.equal(ui.panels[0].hidden, false);
    ui.window.location.href = 'http://localhost:5000/?view=history';
    ui.events.popstate();
    assert.equal(ui.panels[2].hidden, false);
    const modified = ui.event({ctrlKey: true});
    ui.tabs[1].handlers.click(modified);
    assert.equal(modified.prevented, undefined);
});

test('sample flight fills the form without making a prediction', () => {
    const ui = setup();
    ui.elements['sample-flight'].handlers.click();
    assert.equal(ui.elements.source.value, 'Delhi');
    assert.equal(ui.elements.destination.value, 'Mumbai');
    assert.match(ui.elements.result.textContent, /Sample loaded/);
});
