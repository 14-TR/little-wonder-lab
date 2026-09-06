export const PROGRESS_KEY = 'little-wonder-lab:progress:v1';
const emptyProgress = () => ({ enabled: false, completed: [] });

export function createProgress(storageFactory, lessonIds) {
  const allowed = new Set(lessonIds);
  const clean = completed => [...new Set(Array.isArray(completed) ? completed.filter(id => allowed.has(id)) : [])];
  return {
    read() {
      try {
        const stored = JSON.parse(storageFactory().getItem(PROGRESS_KEY));
        return stored?.version === 1 && stored.enabled === true ? { enabled: true, completed: clean(stored.completed) } : emptyProgress();
      } catch { return emptyProgress(); }
    },
    save(state) {
      try {
        if (!state.enabled) storageFactory().removeItem(PROGRESS_KEY);
        else storageFactory().setItem(PROGRESS_KEY, JSON.stringify({ version: 1, enabled: true, completed: clean(state.completed) }));
        return true;
      } catch { return false; }
    },
    clear() {
      try { storageFactory().removeItem(PROGRESS_KEY); return true; }
      catch { return false; }
    },
  };
}

export function mountProgress(container, store, lessonId) {
  let state = store.read();
  container.innerHTML = `<section class="completion"><div><p class="eyebrow">A FIELD NOTE TO KEEP · OPTIONAL</p><h2>A little discovery, remembered.</h2><p>No scores. No streaks. Just a note that you explored.</p><label class="check-row"><input id="remember-progress" type="checkbox"><span>Remember our discoveries on this device</span></label><p class="small-note">Stored only in this browser. Not shared or synced. You can forget these notes anytime.</p></div><div class="completion-actions"><button type="button" class="button" id="complete-lesson" aria-pressed="false">We explored this! <span aria-hidden="true">✓</span></button><button type="button" class="forget-button" id="forget-progress">Forget saved wonders</button></div><p id="progress-status" class="small-note" role="status"></p></section>`;
  const remember = container.querySelector('#remember-progress');
  const complete = container.querySelector('#complete-lesson');
  const status = container.querySelector('#progress-status');
  function update() {
    remember.checked = state.enabled;
    complete.disabled = !state.enabled;
    complete.setAttribute('aria-pressed', String(state.completed.includes(lessonId)));
  }
  remember.addEventListener('change', () => {
    state = { enabled: remember.checked, completed: remember.checked ? state.completed : [] };
    status.textContent = store.save(state) ? (state.enabled ? 'This device can remember your discoveries. Mark one whenever you like.' : 'Remembering is off. Saved wonders have been forgotten.') : 'This browser cannot save or change notes. You can still explore everything.';
    update();
  });
  complete.addEventListener('click', () => {
    const completed = new Set(state.completed);
    if (completed.has(lessonId)) completed.delete(lessonId);
    else completed.add(lessonId);
    state = { enabled: true, completed: [...completed] };
    status.textContent = store.save(state) ? (completed.has(lessonId) ? 'Saved on this device. A little wonder worth remembering.' : 'The explored note is removed from this device.') : 'This browser cannot save notes. Your discovery still counts!';
    update();
  });
  container.querySelector('#forget-progress').addEventListener('click', () => {
    if (store.clear()) { state = emptyProgress(); status.textContent = 'Saved wonders forgotten. Nothing else in this browser was changed.'; }
    else status.textContent = 'This browser cannot change saved notes. You can clear site data in browser settings.';
    update();
  });
  update();
}
