const clamp = (value, min, max, fallback = min) => Math.min(max, Math.max(min, Number.isFinite(Number(value)) ? Number(value) : fallback));

const patternUnits = Object.freeze({ AB: Object.freeze(['leaf', 'flower']), AAB: Object.freeze(['leaf', 'leaf', 'flower']) });

// Exact arranged rules, not observations of how plants grow. Length is bounded
// to the five starting drawings plus three additions; invalid inputs fail closed.
export function patternModel(mode, length) {
  if (!Object.hasOwn(patternUnits, mode)) throw new TypeError('Unsupported pattern mode');
  if (!Number.isInteger(length) || length < 0 || length > 8) throw new RangeError('Pattern length must be an integer from 0 to 8');
  const unit = patternUnits[mode];
  const position = length % unit.length + 1;
  const expected = unit[position - 1];
  return {
    unit, position, expected,
    sequence: Array.from({ length }, (_, index) => unit[index % unit.length]),
    reason: `The repeat is ${unit.join(', ')}. This is place ${position} in that group, so ${expected} comes next.`,
  };
}

// Fixed point light and wall; an unchanged hand moves between them.
// Geometry illustrates the trend only: this is not a real-world measurement.
export function shadowModel(position) {
  const bounded = clamp(position, 0, 100, 50);
  const handX = 220 + bounded * 1.9;
  return {
    handX,
    scale: 460 / (handX - 70),
    description: bounded < 34 ? 'Near the light: a bigger shadow. Your hand stays the same size!' : bounded > 66 ? 'Near the wall: a smaller shadow. Your hand stays the same size!' : 'In the middle: a medium shadow. Which way will make it grow?',
  };
}

// Illustrative coordinates, not a distance or speed prediction.
export function rampModel(height) {
  const rampBottomX = 280, rampBottomY = 217;
  const startY = height === 'high' ? 93 : 145;
  // Rotate one rigid board about its bottom; the release mark stays on it.
  const length = 222, releaseFraction = 0.14, thickness = 7;
  const dy = rampBottomY - startY;
  const dx = Math.sqrt(length ** 2 - dy ** 2);
  const startX = rampBottomX - dx;
  return {
    rampBottomX, rampBottomY, startX, startY,
    angle: Math.atan2(dy, dx) * 180 / Math.PI,
    boardOffsetX: -thickness * dy / length,
    boardOffsetY: thickness * dx / length,
    // Wheel contacts are 12 units below the car origin in its local frame.
    carX: startX + releaseFraction * dx + 12 * dy / length,
    carY: startY + releaseFraction * dy - 12 * dx / length,
    supportTop: startY + dy * (137 - startX) / dx + thickness * length / dx,
    stopX: height === 'high' ? 515 : 385,
  };
}

// Qualitative bending only; no maximum load or universal strongest shape.
export function bridgeModel(shape, loaded) {
  const folded = shape === 'folded';
  return { sag: loaded ? (folded ? 7 : 52) : 0,
    description: !loaded ? 'Predict first: what will happen when the spoon lands?' : folded ? 'Folded sides bend less under the same spoon in this picture. Test your own paper!' : 'The flat paper sags in this picture. Can a new shape help?',
  };
}
