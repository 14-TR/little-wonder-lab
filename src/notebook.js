export function mountNotebook(container) {
  const steps = [...container.querySelectorAll('.experiment-steps > li')];
  const previous = container.querySelector('#previous-step');
  const next = container.querySelector('#next-step');
  let index = 0;
  const update = () => {
    steps.forEach((step, position) => { step.hidden = position !== index; });
    previous.disabled = index === 0;
    next.disabled = index === steps.length - 1;
    container.querySelector('#step-status').textContent = `Step ${index + 1} of ${steps.length}`;
  };
  previous.addEventListener('click', () => { if (index > 0) index -= 1; update(); });
  next.addEventListener('click', () => { if (index < steps.length - 1) index += 1; update(); });
  update();

  const controller = new AbortController();
  let detailStates;
  const beforePrint = () => {
    if (!detailStates) detailStates = [...container.querySelectorAll('details')].map(details => [details, details.open]);
    detailStates.forEach(([details]) => { details.open = true; });
  };
  const afterPrint = () => { detailStates?.forEach(([details, open]) => { details.open = open; }); detailStates = undefined; };
  window.addEventListener('beforeprint', beforePrint, { signal: controller.signal });
  window.addEventListener('afterprint', afterPrint, { signal: controller.signal });
  container.querySelector('#print-lesson').addEventListener('click', () => { beforePrint(); window.print(); });
  return () => controller.abort();
}
