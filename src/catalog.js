export function selectLessons(lessons, { query = '', topic = 'All', sort = 'field' } = {}) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return lessons.filter(lesson => {
    const text = [lesson.title, lesson.subtitle, lesson.topic, lesson.question, lesson.idea].join(' ').toLocaleLowerCase();
    return (topic === 'All' || lesson.topic === topic) && words.every(word => text.includes(word));
  }).sort((a, b) => sort === 'newest' ? b.published.localeCompare(a.published) || b.order - a.order || a.id.localeCompare(b.id) : a.order - b.order || a.id.localeCompare(b.id));
}

export function latestLesson(lessons) {
  return selectLessons(lessons, { sort: 'newest' })[0] || null;
}
