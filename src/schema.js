export const SUPPORTED_KINDS = Object.freeze(['shadows', 'ramps', 'bridges', 'patterns']);
const topics = new Set(['Science', 'Technology', 'Engineering', 'Math']);
const isText = value => typeof value === 'string' && value.trim().length > 0;
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isDate = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;

// A pure build/test gate. Unknown lesson kinds require intentional UI work.
export function validateLessons(lessons) {
  if (!Array.isArray(lessons) || !lessons.length) return ['lessons must be a nonempty array'];
  const errors = [];
  const ids = new Set();
  const orders = new Set();
  for (const [index, lesson] of lessons.entries()) {
    if (!isObject(lesson)) { errors.push(`lesson ${index} must be an object`); continue; }
    const at = lesson.id || `lesson ${index}`;
    const fail = message => errors.push(`${at}: ${message}`);
    if (typeof lesson.id !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(lesson.id)) fail('id must be an exact lowercase slug');
    if (ids.has(lesson.id)) fail('duplicate id');
    ids.add(lesson.id);
    if (!Number.isInteger(lesson.order) || lesson.order < 1 || orders.has(lesson.order)) fail('order must be a unique positive integer');
    orders.add(lesson.order);
    if (!Number.isInteger(lesson.duration) || lesson.duration < 1 || lesson.duration > 60) fail('duration must be 1–60 whole minutes');
    if (!isDate(lesson.published)) fail('published must be a real YYYY-MM-DD date');
    if (!topics.has(lesson.topic)) fail('topic must be a STEM topic');
    if (!SUPPORTED_KINDS.includes(lesson.kind)) fail('unsupported kind; add a tested renderer first');
    for (const key of ['title', 'subtitle', 'question', 'idea', 'prediction', 'explanation', 'parentNote', 'safety', 'challenge']) {
      if (!isText(lesson[key])) fail(`${key} must be nonempty text`);
    }
    for (const [key, max] of [['title', 70], ['subtitle', 130], ['question', 180], ['idea', 280]]) {
      if (isText(lesson[key]) && lesson[key].length > max) fail(`${key} must remain short for a young reader (max ${max} characters)`);
    }
    if (!Array.isArray(lesson.materials) || !lesson.materials.length || !lesson.materials.every(isText)) fail('materials must be a nonempty text array');
    if (!Array.isArray(lesson.steps) || !lesson.steps.length || !lesson.steps.every(step => isObject(step) && isText(step.title) && isText(step.body))) fail('steps need nonempty title and body');
    if (!Array.isArray(lesson.vocabulary) || !lesson.vocabulary.length || !lesson.vocabulary.every(item => isObject(item) && isText(item.word) && isText(item.meaning))) fail('vocabulary needs word and meaning');
    if (!Array.isArray(lesson.prerequisites) || !lesson.prerequisites.every(isText) || new Set(lesson.prerequisites).size !== lesson.prerequisites.length) fail('prerequisites must be an array of unique IDs');
    if (!Array.isArray(lesson.sources) || !lesson.sources.length) fail('sources must be a nonempty array');
    else for (const source of lesson.sources) {
      if (!isObject(source) || !isText(source.title)) { fail('source requires a title'); continue; }
      try {
        const url = new URL(source.url);
        if (url.protocol !== 'https:' || url.username || url.password || !url.hostname) fail('sources require credential-free HTTPS URLs');
      } catch { fail('sources require valid HTTPS URLs'); }
    }
  }
  const graph = new Map(lessons.filter(isObject).map(lesson => [lesson.id, Array.isArray(lesson.prerequisites) ? lesson.prerequisites : []]));
  const visited = new Set();
  const active = new Set();
  function visit(id) {
    if (active.has(id)) { errors.push(`${id}: prerequisite cycle`); return; }
    if (visited.has(id)) return;
    active.add(id);
    for (const prerequisite of graph.get(id) || []) {
      if (!ids.has(prerequisite)) errors.push(`${id}: unknown prerequisite ${prerequisite}`);
      else visit(prerequisite);
    }
    active.delete(id);
    visited.add(id);
  }
  for (const id of graph.keys()) visit(id);
  return errors;
}
