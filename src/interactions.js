import { shadowModel, rampModel, bridgeModel, patternModel } from './models.js';
import { patternSymbols } from './illustrations.js';

export const hand = 'M-13 27l-11-21q-4-8 1-10 5-2 10 9l1-29q0-9 5-9t5 9v15l2-30q1-8 6-7t4 8l-1 29 3-24q1-8 6-7t3 9l-3 25 4-14q2-8 6-6t2 10l-4 24q-1 12-12 20v10h-23z';
const modelFrame = (title, instruction, scene, controls, note) => `<section class="interactive" aria-labelledby="model-title"><div class="model-heading"><div><p class="eyebrow">A TINY ON-SCREEN EXPERIMENT</p><h2 id="model-title">${title}</h2></div><p>${instruction}</p></div><div class="model-stage">${scene}</div><div class="model-controls">${controls}</div><p id="model-result" class="model-result" role="status" aria-live="polite"></p><p class="model-note">A simple picture, not a measurement. ${note}</p></section>`;

function mountShadows(container) {
  container.innerHTML = modelFrame('Make a shadow grow', 'Slide the hand. Keep the light and wall still.', `<svg viewBox="0 0 620 270" role="img" aria-label="A fixed lamp shines past a movable hand onto a wall"><path d="M450 17l127 10v213l-127-7z" fill="#e5e3c9" stroke="#788369"/><path d="M70 130L551 27v213L70 149z" fill="#e4bc55" opacity=".24"/><path d="M46 130l35-22v49l-35-15z" fill="#bb4c2c" stroke="#314d3c" stroke-width="2"/><path d="M50 139l-13 39 20 38m-26 4h51" fill="none" stroke="#314d3c" stroke-width="5" stroke-linecap="round"/><g id="cast-shadow" fill="#3e5342" opacity=".86"><path d="${hand}"/></g><g id="moving-hand" fill="#c58861" stroke="#314d3c" stroke-width="1.5"><path d="${hand}"/></g><path d="M22 239h569" stroke="#bcc3ac"/><g fill="#586353" font-family="Georgia, serif" font-style="italic" font-size="14"><text x="22" y="261">light stays here</text><text x="471" y="261">wall stays here</text></g></svg>`, '<div class="slider-control"><label for="hand-position">Hand position</label><input id="hand-position" type="range" min="0" max="100" value="50" step="1" aria-describedby="hand-hint"><div class="range-ends" id="hand-hint"><span>Closer to the light</span><span>Closer to the wall</span></div></div>', 'Real shadows can have fuzzy edges. Try your own hand with a grown-up.');
  const control = container.querySelector('#hand-position');
  const update = () => {
    const model = shadowModel(control.valueAsNumber);
    container.querySelector('#moving-hand').setAttribute('transform', `translate(${model.handX} 140)`);
    container.querySelector('#cast-shadow').setAttribute('transform', `translate(505 140) scale(${model.scale * .75} ${model.scale * .75})`);
    container.querySelector('#model-result').textContent = model.description;
    control.setAttribute('aria-valuetext', model.description);
  };
  control.addEventListener('input', update);
  update();
}

const car = `<path d="M-30-14l9-13h25l16 13h10v17h-64v-14z" fill="#bc452b" stroke="#314d3c" stroke-width="2"/><path d="M-18-24h20l12 11h-39z" fill="#dce5ce" stroke="#314d3c"/><circle cx="-20" cy="4" r="8" fill="#314d3c"/><circle cx="19" cy="4" r="8" fill="#314d3c"/><circle cx="-20" cy="4" r="3" fill="#e2c98f"/><circle cx="19" cy="4" r="3" fill="#e2c98f"/>`;

function mountRamps(container) {
  container.innerHTML = modelFrame('One car. Two little hills.', 'Guess first: which hill will send the car farther?', `<svg viewBox="0 0 620 280" role="img" aria-label="A car on an adjustable ramp and a flat runout track"><path d="M35 223h550" stroke="#63765d" stroke-width="2"/><g id="ramp-books"></g><path id="ramp-board" fill="#cdab74" stroke="#526343" stroke-width="2"/><path d="M280 220v24" stroke="#b64025" stroke-width="2"/><text x="252" y="264" fill="#586353" font-family="Georgia, serif" font-style="italic" font-size="13">same start of floor</text><g id="stop-markers"></g><g id="rolling-car">${car}</g><path d="M548 216V163l24 9-24 9" fill="#e8c16b" stroke="#526343" stroke-width="2"/></svg>`, `<div class="ramp-controls"><div class="segmented" role="group" aria-label="Ramp height"><button type="button" data-height="low" aria-pressed="true">Lower ramp</button><button type="button" data-height="high" aria-pressed="false">Higher ramp</button></div><button type="button" class="button" id="roll-car">Let it roll <span aria-hidden="true">→</span></button><button type="button" class="button secondary" id="reset-ramp">Clear the track</button></div>`, 'Same car. Same smooth floor. No push. Real rolls can stop in different places.');
  let height = 'low';
  const stops = new Set();
  let animation;
  const carElement = container.querySelector('#rolling-car');
  function resetCar() {
    animation?.cancel();
    const model = rampModel(height);
    container.querySelector('#ramp-board').setAttribute('d', `M${model.startX} ${model.startY}L${model.rampBottomX} ${model.rampBottomY}L${model.rampBottomX + model.boardOffsetX} ${model.rampBottomY + model.boardOffsetY}L${model.startX + model.boardOffsetX} ${model.startY + model.boardOffsetY}z`);
    container.querySelector('#ramp-books').innerHTML = `<path d="M65 ${height === 'high' ? 183 : model.supportTop}h72V218H65z" fill="#ad6246" stroke="#526343" stroke-width="2"/>${height === 'high' ? `<path d="M65 ${model.supportTop}h72V183H65z" fill="#d3b260" stroke="#526343" stroke-width="2"/>` : ''}`;
    carElement.setAttribute('transform', `translate(${model.carX} ${model.carY}) rotate(${model.angle})`);
    container.querySelector('#model-result').textContent = 'Ready? Let go without a push.';
  }
  container.querySelectorAll('[data-height]').forEach(button => button.addEventListener('click', () => {
    height = button.dataset.height;
    container.querySelectorAll('[data-height]').forEach(option => option.setAttribute('aria-pressed', String(option === button)));
    resetCar();
  }));
  container.querySelector('#roll-car').addEventListener('click', () => {
    animation?.cancel();
    const model = rampModel(height);
    carElement.setAttribute('transform', `translate(${model.stopX} 210)`);
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      animation = carElement.animate([{ transform: `translate(${model.carX}px, ${model.carY}px) rotate(${model.angle}deg)`, offset: 0 }, { transform: 'translate(280px, 210px) rotate(0deg)', offset: .45 }, { transform: `translate(${model.stopX}px, 210px) rotate(0deg)`, offset: 1 }], { duration: 1000, easing: 'ease-in-out' });
    }
    stops.add(height);
    container.querySelector('#stop-markers').innerHTML = [...stops].map(stop => `<g data-stop="${stop}" transform="translate(${rampModel(stop).stopX} 223)"><path d="M0 0v17" stroke="${stop === 'low' ? '#526343' : '#b64025'}" stroke-width="3"/><text x="0" y="40" text-anchor="middle" fill="#526343" font-family="Georgia, serif" font-size="14">${stop === 'low' ? 'lower' : 'higher'}</text></g>`).join('');
    container.querySelector('#model-result').textContent = height === 'low' ? 'The lower ramp has a stopping mark. What will a higher ramp do?' : 'In this picture, the higher ramp rolls farther. What happens on your floor?';
  });
  container.querySelector('#reset-ramp').addEventListener('click', () => { stops.clear(); container.querySelector('#stop-markers').innerHTML = ''; resetCar(); });
  resetCar();
}

function mountBridges(container) {
  container.innerHTML = modelFrame('Give paper a new shape', 'Same paper. Same spoon. A different fold.', `<svg viewBox="0 0 620 300" role="img" aria-label="Paper spans two books; change its folded sides and place the same spoon at the center"><g stroke="#526343" stroke-width="2"><path d="M75 181h125v53H75z" fill="#ab7050"/><path d="M419 181h125v53H419z" fill="#ab7050"/><path d="M78 190h120m-120 32h120m224-32h120m-120 32h120" stroke="#e2c197"/><path d="M225 257q82-28 164 0m-151 11q69-20 138 0" fill="none" stroke="#8bacae"/><g id="bridge-rear-wall"></g><path id="bridge-deck" fill="#eee0a0" stroke="#8b7a45"/><g id="bridge-front-wall"></g><g id="bridge-spoon" fill="#b9d0c9" stroke="#426957"><path d="M310 137c-23-25-4-39 9-29 13 10 15 20-1 30l33 44q4 7-2 10-5 2-9-4z"/><path d="M304 115q-4 13 10 17" fill="none" stroke="#eaf0df"/></g></g><g id="bridge-end-view"></g><text x="311" y="44" text-anchor="middle" font-family="Georgia, serif" font-style="italic" font-size="15" fill="#526343">one paper crossing, one little spoon</text></svg>`, '<div class="ramp-controls"><div class="segmented" role="group" aria-label="Paper shape"><button type="button" data-shape="flat" aria-pressed="true">Flat paper</button><button type="button" data-shape="folded" aria-pressed="false">Folded sides</button></div><button type="button" class="button" id="spoon-toggle">Place the spoon</button></div>', 'Folds can help paper resist bending. Real results depend on the paper, folds, gap, and load.');
  let shape = 'flat';
  let loaded = false;
  function update() {
    const { sag, description } = bridgeModel(shape, loaded);
    container.querySelector('#bridge-deck').setAttribute('d', `M142 157Q310 ${157 + sag} 478 157L478 182Q310 ${182 + sag} 142 182z`);
    container.querySelector('#bridge-rear-wall').innerHTML = shape === 'folded' ? `<path d="M142 157Q310 ${157 + sag} 478 157V126Q310 ${126 + sag} 142 126z" fill="#dfc776" stroke="#8b7a45"/>` : '';
    container.querySelector('#bridge-front-wall').innerHTML = shape === 'folded' ? `<path d="M142 182Q310 ${182 + sag} 478 182V151Q310 ${151 + sag} 142 151z" fill="#d1b96a" stroke="#8b7a45"/>` : '';
    const spoon = container.querySelector('#bridge-spoon');
    spoon.style.display = loaded ? '' : 'none';
    spoon.setAttribute('transform', `translate(0 ${sag / 2})`);
    container.querySelector('#bridge-end-view').innerHTML = `<path d="${shape === 'folded' ? 'M35 54v29h62V54' : 'M35 83h62'}" fill="none" stroke="#897b45" stroke-width="3"/><text x="66" y="106" text-anchor="middle" fill="#526343" font-family="Georgia, serif" font-size="13">end view</text>`;
    container.querySelector('#model-result').textContent = description;
    container.querySelector('#spoon-toggle').textContent = loaded ? 'Remove the spoon' : 'Place the spoon';
  }
  container.querySelectorAll('[data-shape]').forEach(button => button.addEventListener('click', () => {
    shape = button.dataset.shape;
    container.querySelectorAll('[data-shape]').forEach(option => option.setAttribute('aria-pressed', String(option === button)));
    update();
  }));
  container.querySelector('#spoon-toggle').addEventListener('click', () => { loaded = !loaded; update(); });
  update();
}

function mountPatterns(container) {
  container.innerHTML = `<section class="interactive pattern-interactive" aria-labelledby="model-title">
    <div class="model-heading"><div><p class="eyebrow">AN ARRANGED REPEATING RULE</p><h2 id="model-title">What belongs in the next space?</h2></div><p>Predict before choosing. Point, say, or draw your idea. You can just watch, too.</p></div>
    <div class="pattern-actions" role="group" aria-label="Choose a repeat"><button class="button secondary" type="button" data-pattern="AB" aria-pressed="true">AB</button><button class="button secondary" type="button" data-pattern="AAB" aria-pressed="false">AAB</button></div>
    <div class="model-stage"><p id="pattern-repeat"></p><div id="pattern-drawing" class="pattern-units" aria-hidden="true"></div><p class="pattern-reading">Read the path (bars separate groups): <span id="pattern-sequence"></span></p></div>
    <div class="model-controls pattern-actions"><button class="button secondary" type="button" data-symbol="leaf">Leaf</button><button class="button secondary" type="button" data-symbol="flower">Flower</button></div>
    <div class="model-controls pattern-actions"><button class="button" type="button" id="pattern-next" aria-disabled="true">Next space</button><button class="button secondary" type="button" id="pattern-restart">Restart path</button></div>
    <p id="model-result" class="model-result" role="status" aria-live="polite" aria-atomic="true"></p>
    <p class="model-note">We arranged these drawings to repeat. Real plants do not all grow in repeating rows. No answers are saved.</p></section>`;
  let mode = 'AB';
  let length = 5;
  let filled = false;
  const status = container.querySelector('#model-result');
  const next = container.querySelector('#pattern-next');
  const prompt = 'What comes next? Say the repeat before choosing a drawing.';
  function draw() {
    const model = patternModel(mode, length);
    const sequence = [...model.sequence, ...(filled ? [] : ['blank'])];
    const groups = [];
    for (let index = 0; index < sequence.length; index += model.unit.length) groups.push(sequence.slice(index, index + model.unit.length));
    container.querySelector('#pattern-repeat').textContent = `Repeat group (${mode}): ${model.unit.join(', ')}. Say the whole group again.`;
    container.querySelector('#pattern-sequence').textContent = groups.map(group => group.join(', ')).join(' | ');
    container.querySelector('#pattern-drawing').innerHTML = groups.map(group => `<div class="pattern-group">${group.map(symbol => `<div class="pattern-tile"><svg viewBox="0 0 60 60" stroke="#344e3d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${patternSymbols[symbol]}</svg><span>${symbol === 'blank' ? 'next?' : symbol}</span></div>`).join('')}</div>`).join('');
    container.querySelectorAll('[data-symbol]').forEach(button => button.setAttribute('aria-disabled', String(filled)));
    next.setAttribute('aria-disabled', String(!filled || length === 8));
    container.querySelectorAll('[data-pattern]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.pattern === mode)));
  }
  container.querySelectorAll('[data-symbol]').forEach(button => button.addEventListener('click', () => {
    if (filled) return;
    const model = patternModel(mode, length);
    if (button.dataset.symbol !== model.expected) {
      status.textContent = `Try looking at the whole group. ${model.reason} The space is still here for another try.`;
      return;
    }
    length += 1;
    filled = true;
    status.textContent = `That fits the rule! ${model.reason} ${length === 8 ? 'Three drawings added. Tell the repeat story, restart, or switch paths.' : 'Choose Next space when you want another blank.'}`;
    draw();
  }));
  next.addEventListener('click', () => {
    if (!filled || length === 8) return;
    filled = false;
    status.textContent = prompt;
    draw();
  });
  function restart() {
    length = 5;
    filled = false;
    status.textContent = prompt;
    draw();
  }
  container.querySelector('#pattern-restart').addEventListener('click', restart);
  container.querySelectorAll('[data-pattern]').forEach(button => button.addEventListener('click', () => {
    mode = button.dataset.pattern;
    restart();
  }));
  restart();
}

const renderers = { shadows: mountShadows, ramps: mountRamps, bridges: mountBridges, patterns: mountPatterns };
export const interactiveKinds = Object.freeze(Object.keys(renderers));
export function mountInteractive(kind, container) {
  if (!Object.hasOwn(renderers, kind)) throw new TypeError(`Unsupported interactive kind: ${kind}`);
  renderers[kind](container);
}
