var ABOUT = {
  back: 0,
  repository: 1,
  issue: 2,
  system: 3,
  english: 4,
  spanish: 5
}

var aboutOrder = ["back", "repository", "issue", "system", "en", "es"]

function aboutItem(index) {
  return index >= 0 && index < aboutOrder.length ? aboutOrder[index] : ""
}

function nextAboutCursor(index, direction) {
  return (index + direction + aboutOrder.length) % aboutOrder.length
}

function moveAboutCursor(index, dx, dy, language) {
  var selectedLanguageIndex = language === "en" ? ABOUT.english
    : language === "es" ? ABOUT.spanish : ABOUT.system

  if (dy > 0) {
    if (index === ABOUT.back) return ABOUT.repository
    if (index === ABOUT.repository) return ABOUT.issue
    if (index === ABOUT.issue) return selectedLanguageIndex
  } else if (dy < 0) {
    if (index === ABOUT.repository) return ABOUT.back
    if (index === ABOUT.issue) return ABOUT.repository
    if (index >= ABOUT.system && index <= ABOUT.spanish) return ABOUT.issue
  } else if (dx > 0 && index >= ABOUT.system && index <= ABOUT.spanish) {
    return index === ABOUT.spanish ? ABOUT.system : index + 1
  } else if (dx < 0 && index >= ABOUT.system && index <= ABOUT.spanish) {
    return index === ABOUT.system ? ABOUT.spanish : index - 1
  }
  return index
}
