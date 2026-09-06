// Original SVG field-notebook drawings. No image requests or third-party assets.
const hand = 'M-13 27l-11-21q-4-8 1-10 5-2 10 9l1-29q0-9 5-9t5 9v15l2-30q1-8 6-7t4 8l-1 29 3-24q1-8 6-7t3 9l-3 25 4-14q2-8 6-6t2 10l-4 24q-1 12-12 20v10h-23z';
const sprig = `<g fill="none" stroke="#526f4a" stroke-width="2.5" stroke-linecap="round"><path d="M520 296q-4-47 23-86M523 269q-26-8-26-28 24 2 26 28M528 250q27-2 33-25-24-2-33 25M538 226q-6-22 7-38 12 22-7 38"/></g>`;
const lines = `<path d="M48 312q227 7 510-1M70 322l39 1m300 0 103-1" fill="none" stroke="#66705a" stroke-width="1.5" opacity=".4"/>`;
const shadowScene = `
  <path d="M308 51l224 12 4 234-246-8z" fill="#e8e5d0" stroke="#627260" stroke-width="1.4"/>
  <path d="M321 64l197 10 3 209-215-7z" fill="#f3edce" stroke="#a9ab83" stroke-width="1"/>
  <path d="M151 175L499 75v204L151 202z" fill="#e8b74f" opacity=".25"/>
  <g transform="translate(419 192) scale(1.9)" fill="#374b3e" opacity=".85"><path d="${hand}"/></g>
  <path d="M94 182l68-40 4 78-70-25z" fill="#ba482c" stroke="#314d3c" stroke-width="2.4"/>
  <path d="M159 144l7-3 4 79-6 1z" fill="#e7b744" stroke="#314d3c" stroke-width="2"/>
  <path d="M103 191l-22 49 36 54" stroke="#314d3c" stroke-width="6" fill="none" stroke-linecap="round"/>
  <circle cx="81" cy="240" r="6" fill="#e8bd5b" stroke="#314d3c" stroke-width="2"/>
  <path d="M82 301q36-16 67 0v7H82z" fill="#ba482c" stroke="#314d3c" stroke-width="2"/>
  <path d="M86 306q-51 11-42-16" fill="none" stroke="#526343" stroke-width="2"/>
  <path d="M254 253l-3 50h28l-3-48" fill="#c58760" stroke="#314d3c" stroke-width="2"/>
  <g transform="translate(264 225)" fill="#c58760" stroke="#314d3c" stroke-width="2"><path d="${hand}"/></g>
  <path d="M253 239q10-6 20 0" fill="none" stroke="#9e6648" stroke-width="1.4"/>
  <g fill="none" stroke="#b74427" stroke-linecap="round" stroke-width="1.7"><path d="M209 105q35-24 72-10m-9-8 13 9-13 7M334 40l6-13m10 18 12-7M74 131l-8-11m24 3-2-14"/></g>
  <g fill="#53624e" font-family="Georgia, serif" font-size="15" font-style="italic"><text x="175" y="83" transform="rotate(-7 175 83)">a little hand…</text><text x="368" y="316" transform="rotate(3 368 316)">a BIG hello</text></g>${sprig}${lines}`;
const rampScene = `
  <ellipse cx="313" cy="307" rx="220" ry="12" fill="#d8dbc4"/>
  <g stroke="#344e3d" stroke-width="2" stroke-linejoin="round"><path d="M115 245l105-7 2 56-107 7z" fill="#b54b34"/><path d="M115 245l13-9 102-6-10 8z" fill="#d9926c"/><path d="M117 254l100-7m-98 37 99-7" stroke="#f0c095"/><path d="M105 210l108-4 9 32-107 7z" fill="#e7b957"/><path d="M105 210l9-9 109-5-10 10z" fill="#f2d490"/>
  <path d="M166 181l316 98-23 21-321-103z" fill="#cfa577"/><path d="M138 197l321 103v10L138 206z" fill="#a87e53"/><path d="M162 187l308 96m-316-13 40 0m-43 10 57-2" fill="none" stroke="#a67e55"/>
  <g transform="translate(255 200) rotate(18)"><path d="M-53 8l13-25 43-3 28 21 16 1v24h-105V10z" fill="#c6492f"/><path d="M-34-13l30-2 19 16h-58z" fill="#e4e9c9"/><path d="M-14-13v13" fill="none"/><circle cx="-33" cy="26" r="13" fill="#344e3d"/><circle cx="24" cy="26" r="13" fill="#344e3d"/><circle cx="-33" cy="26" r="5" fill="#ddc799"/><circle cx="24" cy="26" r="5" fill="#ddc799"/><path d="M-46 9h79" stroke="#ee9872"/></g></g>
  <path d="M330 180q37 13 56 41l-3-17m3 17-20-5M75 141l-9-10m23 5-1-16" fill="none" stroke="#b74427" stroke-width="2" stroke-linecap="round"/>
  <path d="M406 271v-75l32 12-31 12" fill="#d3b350" stroke="#344e3d" stroke-width="2"/><path d="M406 196l15 5v13l-14 6m14-19 16 6v12l-16-5" fill="#f4efd9"/>
  <text x="243" y="125" font-family="Georgia, serif" font-size="18" font-style="italic" fill="#53624e" transform="rotate(7 243 125)">ready, set… roll!</text>${sprig}${lines}`;
const bridgeScene = `
  <ellipse cx="303" cy="305" rx="225" ry="13" fill="#d8dbc4"/>
  <g stroke="#344e3d" stroke-width="2" stroke-linejoin="round"><path d="M95 211l84-10 28 21-1 75-108 5z" fill="#b47450"/><path d="M95 211l23 22 89-11m-89 11 1 69" fill="none"/><path d="M403 200l84 8 23 19-2 70-105-2z" fill="#b47450"/><path d="M403 200l24 27h83m-83 0-2 70" fill="none"/>
  <path d="M121 242l80-9m-80 22 80-9m-80 22 80-9m-80 22 80-9m234-32h66m-66 13h66m-66 13h66m-66 13h66" fill="none" stroke="#e0c397" stroke-width="1.4"/>
  <g data-paper-shape="u-channel"><path d="M138 188l287 1v-37l-287-1z" fill="#ddc67b" stroke="#8b7a45"/><path d="M138 188l287 1 30 37-298-1z" fill="#f5e5ab" stroke="#8b7a45"/><path d="M157 225l298 1v-38l-298-1z" fill="#d3b968" stroke="#8b7a45"/><path d="M164 212l280 1m-294-54 267 1" fill="none" stroke="#e8d897"/></g>
  <g data-load="spoon" fill="#a8c2b6" stroke="#436856"><path d="M295 180c-21-11-23-25-12-31 16-9 35 7 31 21-2 5-6 8-9 9l30 42q4 6-2 9-6 3-10-5z"/><path d="M284 155q-7 12 16 17" fill="none" stroke="#e4eade"/></g>
  <path d="M237 281q47-40 94 0" fill="none" stroke="#738b96" stroke-width="3"/><path d="M226 289q59-36 116 0m-101 9q45-19 86 0" fill="none" stroke="#a6bbc0"/></g>
  <g fill="none" stroke="#b74427" stroke-width="1.8" stroke-linecap="round"><path d="M252 127l-9-18m27 13-1-19m21 20 8-16M346 153q43-13 53-36m-10 3 10-3 0 12"/></g>
  <text x="319" y="99" font-family="Georgia, serif" font-size="17" font-style="italic" fill="#53624e" transform="rotate(-5 319 99)">two folds. big ideas.</text>${sprig}${lines}`;

const scenes = { shadows: shadowScene, ramps: rampScene, bridges: bridgeScene };
export const illustrationKinds = Object.freeze(Object.keys(scenes));
export function illustration(kind) {
  if (!Object.hasOwn(scenes, kind)) throw new TypeError(`Unsupported illustration kind: ${kind}`);
  const names = { shadows: 'An open hand makes a bigger waving shadow in a fixed desk lamp beam', ramps: 'A red toy car rolls down a gentle cardboard ramp resting on two books', bridges: 'A paper bridge with two upright folded sides spans two books and carries one full-size plastic spoon' };
  return `<svg class="illustration" viewBox="0 0 600 350" role="img" aria-label="${names[kind]}" xmlns="http://www.w3.org/2000/svg">${scenes[kind]}</svg>`;
}

export const flower = `<svg viewBox="0 0 48 58" fill="none" aria-hidden="true"><g stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M24 53V29M24 45Q8 44 8 33q15-1 16 12M24 39q1-15 16-15-1 14-16 15"/><path d="M24 9c-8-14-21 0-11 8-17 2-10 20 2 14 0 14 19 14 19 1 15 7 22-12 8-16C50 4 31-4 28 9z" fill="currentColor" stroke="none"/><circle cx="26" cy="20" r="5" fill="#f7f3e8" stroke="none"/></g></svg>`;
export const sun = `<svg viewBox="0 0 100 100" fill="none" aria-hidden="true"><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M34 32q14-11 29 0 14 12 2 28-13 13-28 1-14-10-3-29zM48 12l1 10M75 18l-7 10M85 44l-10 1M81 72l-11-7M53 85V74M22 80l9-12M12 50l11-1M19 21l9 10"/><path d="M39 47v2m17-2v2m-15 7q6 6 12 0"/></g></svg>`;
