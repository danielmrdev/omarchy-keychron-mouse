function updatedEntry(settings, moduleName, key, value) {
  var entry = { id: moduleName }
  var current = settings || {}
  for (var name in current) if (name !== "id") entry[name] = current[name]
  entry[key] = value
  return entry
}
