(() => {
  'use strict';
  const root = document.getElementById('trial-page');
  if (!root) return;
  const content = document.getElementById('trial-content');
  const lang = root.lang || 'en';
  let copy;
  function node(tag, text, className) {
    const element = document.createElement(tag);
    element.textContent = text || '';
    if (className) element.className = className;
    return element;
  }
  function link(text, href) {
    const element = node('a', text, 'trial-button'); element.href = href; return element;
  }
  function bookLink() {
    return link(copy.book, lang === 'ru' ? '/ru/probnyj-urok/new' : lang === 'ar' ? '/ar/academy-trial/new' : '/academy-trial/new');
  }
  function render(row) {
    const card = node('article', '', 'trial-card');
    card.append(node('p', row.name, 'trial-id'), node('h2', copy[row.status] || row.status));
    if (row.status === 'Scheduled') {
      const time = node('p', row.start_label, 'trial-time'); time.dir = 'ltr'; card.append(time);
      card.append(node('p', `${row.trial_duration || ''} ${copy.minutes}`));
      if (row.teacher_name) card.append(node('p', `${copy.teacher}: ${row.teacher_name}`));
      try {
        const url = new URL(row.trial_meeting_url);
        if (url.protocol === 'https:' && !url.username && !url.password) {
          const join = link(copy.join, url.href); join.rel = 'noopener noreferrer'; card.append(join);
        }
      } catch (_) { /* A missing meeting link never becomes an unsafe link. */ }
    } else {
      card.append(node('p', ['New', 'Contacted'].includes(row.status) ? copy.waiting :
        ['Reschedule', 'No Show'].includes(row.status) ? copy.reschedule : row.status === 'Closed' ? copy.closed : copy.completed));
    }
    [['result', 'trial_result'], ['recommendation', 'trial_recommendation'], ['next', 'trial_next_step']].forEach(([label, field]) => {
      if (row[field]) card.append(node('h3', copy[label]), node('p', row[field]));
    });
    if (row.status === 'Closed') card.append(bookLink());
    return card;
  }
  async function load() {
    content.setAttribute('aria-busy', 'true');
    try {
      if (!copy) {
        const response = await fetch('/assets/allimquran/trial-copy.json');
        if (!response.ok) throw new Error('copy');
        const all = await response.json(); copy = all[lang] || all.en;
      }
      content.replaceChildren(node('p', copy.loading));
      const response = await fetch('/api/method/allimquran.trial_lifecycle.my_trials', {credentials:'same-origin',cache:'no-store'});
      if ([401, 403].includes(response.status)) {
        content.replaceChildren(node('p', copy.guest), link(copy.signin, '/login?redirect-to=' + encodeURIComponent('/my-trial-lesson?lang=' + lang)));
        return;
      }
      if (!response.ok) throw new Error('request');
      const data = await response.json();
      if (!Array.isArray(data.message)) throw new Error('data');
      content.replaceChildren();
      if (!data.message.length) content.append(node('p', copy.empty), node('p', copy.unlinked), bookLink());
      data.message.forEach(row => content.append(render(row)));
    } catch (_) {
      const error = node('p', copy ? copy.error : ({ru:'Не удалось загрузить урок.',ar:'تعذّر تحميل الدرس.'}[lang] || 'Could not load your lesson.'));
      const retry = node('button', copy ? copy.retry : ({ru:'Повторить',ar:'إعادة المحاولة'}[lang] || 'Try again'), 'trial-button');
      retry.type = 'button'; retry.addEventListener('click', load, {once:true});
      content.replaceChildren(error, retry);
    } finally { content.setAttribute('aria-busy', 'false'); }
  }
  load();
})();
