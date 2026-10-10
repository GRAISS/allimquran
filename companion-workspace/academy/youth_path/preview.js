(() => {
  'use strict';
  const courses = window.ALLIM_COURSES;
  const $ = id => document.getElementById(id);
  const text = (tag, value, className) => { const el = document.createElement(tag); el.textContent = value; if (className) el.className = className; return el; };
  const button = (label, action) => { const el = text('button', label); el.type = 'button'; el.addEventListener('click', action); return el; };
  const key = 'allim-youth-review-v1';
  let saved = {passed: {}, last: null, age: 'kids'}, current, active;
  try { const data = JSON.parse(localStorage.getItem(key)); if (data && typeof data.passed === 'object' && data.passed !== null) saved = {...saved, ...data}; } catch (_) { $('storage').textContent = 'Сохранение недоступно. Упражнения работают до закрытия страницы.'; }
  function persist() { try { localStorage.setItem(key, JSON.stringify(saved)); } catch (_) { $('storage').textContent = 'Результат этой попытки не сохранён: хранилище браузера недоступно.'; } }
  const allLessons = c => c.chapters.flatMap(ch => ch.lessons);
  function drawCatalog() {
    $('catalog').replaceChildren();
    courses.forEach((c, i) => {
      const ls = allLessons(c), n = ls.filter(l => saved.passed[l.id]).length;
      const card = text('section', '', 'card');
      card.append(text('span', `ЭТАП ${i+1} · ${ls.length} УРОКОВ`, 'eyebrow'), text('h2', c.title), text('p', c.short_introduction), text('p', c.prerequisite, 'note'));
      const meter = document.createElement('progress'); meter.max = ls.length; meter.value = n; meter.setAttribute('aria-label', 'Пройденные упражнения курса');
      card.append(meter, text('p', `Упражнения: ${n} из ${ls.length} · только этот браузер`, 'count'), button('Открыть этап '+(i+1), () => open(c, ls[0])));
      $('catalog').append(card);
    });
    $('continue').hidden = !courses.some(c => allLessons(c).some(l => l.id === saved.last));
  }
  function navigation() {
    $('lessons').replaceChildren();
    current.chapters.forEach(ch => {
      $('lessons').append(text('h3', ch.title));
      ch.lessons.forEach(l => { const b = button((saved.passed[l.id] ? '✓ ' : '') + l.title, () => open(current, l)); if (active.id === l.id) b.setAttribute('aria-current', 'step'); $('lessons').append(b); });
    });
  }
  function open(c, l) {
    current = c; active = l; saved.last = l.id; persist(); $('workspace').hidden = false; navigation(); drawCatalog();
    const article = $('lesson'); article.replaceChildren();
    article.append(text('p', `${c.title} · около ${l.minutes} минут`, 'eyebrow'), text('h2', l.title), text('p', l[saved.age === 'teens' ? 'teens' : 'kids'], 'coach'));
    const body = document.createElement('div'); body.innerHTML = l.html; article.append(body); // Generated, escaped course content; never user input.
    const quiz = document.createElement('form'); quiz.className = 'quiz'; quiz.append(text('h3', 'Проверь, что заметил'));
    const feedback = [];
    l.questions.forEach((q, i) => {
      const fs = document.createElement('fieldset'); fs.append(text('legend', `${i+1}. ${q.prompt}`));
      q.options.forEach((option, j) => { const label = document.createElement('label'); const input = document.createElement('input'); input.type = 'radio'; input.name = 'q'+i; input.value = j; input.required = true; const value = text('bdi', option); value.dir = 'auto'; label.append(input, value); fs.append(label); });
      const hint = document.createElement('details'); hint.append(text('summary', 'Подсказка'), text('p', q.hint)); fs.append(hint);
      const f = text('p', '', 'feedback'); f.hidden = true; f.setAttribute('aria-live','polite'); fs.append(f); feedback.push(f); quiz.append(fs);
    });
    const submit = text('button','Проверить ответы'); submit.type='submit'; quiz.append(submit);
    const result = text('p',''); result.setAttribute('role','status'); quiz.append(result);
    quiz.addEventListener('submit', e => {
      e.preventDefault(); let correct = 0;
      l.questions.forEach((q,i) => { const chosen = quiz.querySelector(`input[name="q${i}"]:checked`); const ok = chosen && Number(chosen.value) === q.answer; if(ok) correct++; feedback[i].hidden=false; feedback[i].textContent=(ok ? 'Верно. ' : 'Попробуй ещё раз. ') + q.explanation; });
      if(correct === l.questions.length) { saved.passed[l.id]=true; persist(); result.textContent='Все ответы верны. Следующий шаг — практика с преподавателем.'; navigation(); drawCatalog(); }
      else result.textContent=`Верно: ${correct} из ${l.questions.length}. Разбери подсказку, измени ответ и проверь снова.`;
    });
    article.append(quiz);
    const actions = text('div','','actions');
    if(l.reference) { const link = text('a','Практика в Коране ↗'); link.href = `https://allimquran.com/learn?view=read&lang=ru&surah=${l.reference.surah}&ayah=${l.reference.ayah}`; actions.append(link); }
    const ls = allLessons(c), next = ls[ls.indexOf(l)+1];
    if(next) actions.append(button('Следующий урок',()=>open(c,next)));
    article.append(actions, text('p','Устная проверка проходит с преподавателем. Этот просмотр не отправляет ему ответы и не меняет результаты в академии.','note'));
    article.focus({preventScroll:true}); article.scrollIntoView({block:'start',behavior:'instant'});
  }
  if(!Array.isArray(courses) || !courses.length) { $('catalog').append(text('p','Материалы не загрузились. Обновите страницу.')); return; }
  $('age').value = saved.age === 'teens' ? 'teens' : 'kids';
  $('age').addEventListener('change', () => { saved.age=$('age').value;persist();if(active)open(current,active); });
  $('continue').addEventListener('click',()=>{ const c=courses.find(c=>allLessons(c).some(l=>l.id===saved.last));if(c)open(c,allLessons(c).find(l=>l.id===saved.last)); });
  drawCatalog();
})();
