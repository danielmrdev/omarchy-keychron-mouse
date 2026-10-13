var catalogs = {
  en: {
    batteryUnavailable: "Battery: data unavailable",
    batteryValue: "Battery: %1% · %2",
    charging: "charging",
    notCharging: "not charging",
    connectedWired: "M7 connected by cable",
    connectedWireless: "Ultra-Link 8K · M7 linked",
    waitingForMouse: "Waiting for M7 status",
    showBatteryInBar: "Show battery in bar",
    batterySettingDescription: "Show the percentage and charging indicator.",
    connectionBattery: "CONNECTION & BATTERY",
    activeMode: "Active mode: %1",
    batteryEmpty: "Battery: —",
    dpiShared: "DPI · SHARED",
    cableDpiNote: "Wired mode is read-only; applying DPI is limited to the 2.4 GHz receiver.",
    sharedDpiNote: "The protocol applies one stage across USB, 2.4 GHz, and Bluetooth. Close Keychron Launcher before changing DPI.",
    profile: "Profile %1 / %2",
    applyWarning: "Applying changes the active DPI stage for all three modes. Close Keychron Launcher before applying.",
    applyDpi: "Apply %1 DPI",
    applyDpiGeneric: "Apply DPI",
    refresh: "Refresh",
    applying: "Applying…",
    updatingStatus: "Refreshing status…",
    readingStatus: "Reading status…",
    buttonsReadOnly: "BUTTONS · READ-ONLY",
    remapPending: "Button remapping has not been physically validated on this M7.",
    about: "About",
    backToMouse: "Back to mouse controls",
    aboutSummary: "Status, battery, and DPI controls for Keychron M7 8K.",
    developerBy: "Developer · %1",
    helpLinks: "HELP & LINKS",
    projectRepository: "Project repository",
    reportIssue: "Report a problem",
    interfaceLanguage: "INTERFACE LANGUAGE",
    languageHelp: "Choose System to follow your desktop language.",
    languageSystem: "System",
    languageEnglish: "English",
    languageSpanish: "Español",
    dpiAlreadyActive: "DPI was already active; no write was sent.",
    dpiApplied: "DPI applied and confirmed by two reads.",
    dpiAppliedNoAck: "DPI confirmed by two reads; no ACK received.",
    dpiUnconfirmed: "Could not confirm the requested DPI; current state is uncertain.",
    responseTooLarge: "Helper response exceeds the allowed size.",
    readStatusFailed: "Could not read mouse status.",
    confirmDpiFailed: "Could not confirm the DPI change.",
    hidPermission: "Cannot access %1; check the device's uaccess ACL.",
    hidTimeout: "The mouse did not answer HID report %1.",
    hidQueueBusy: "Pending HID reports did not drain; no new report was sent.",
    deviceNotFound: "No compatible device found: %1.",
    ambiguousDevice: "Multiple matching Keychron interfaces found; refusing to guess.",
    configInterfaceMissing: "%1 found, but its required configuration interface is missing.",
    unsupportedProtocol: "Unsupported protocol version %1; expected version 4.",
    mouseNotConfirmed: "Connected M7 8K could not be confirmed; no further queries were sent.",
    dpiPresetMismatch: "DPI %1 is not among the receiver-reported presets; no write was sent."
  },
  es: {
    batteryUnavailable: "Batería: dato no disponible",
    batteryValue: "Batería: %1% · %2",
    charging: "cargando",
    notCharging: "no está cargando",
    connectedWired: "M7 conectado por cable",
    connectedWireless: "Ultra-Link 8K · M7 enlazado",
    waitingForMouse: "Esperando lectura del M7",
    showBatteryInBar: "Mostrar batería en la barra",
    batterySettingDescription: "Mostrar porcentaje e indicador de carga.",
    connectionBattery: "CONEXIÓN Y BATERÍA",
    activeMode: "Modo activo: %1",
    batteryEmpty: "Batería: —",
    dpiShared: "DPI · COMPARTIDO",
    cableDpiNote: "La lectura por cable es posible, pero solo se puede aplicar DPI con el receptor de 2,4 GHz.",
    sharedDpiNote: "El protocolo aplica una etapa a USB, 2,4 GHz y Bluetooth. Cierra Keychron Launcher antes de cambiar el DPI.",
    profile: "Perfil %1 / %2",
    applyWarning: "Aplicar cambia la etapa activa de DPI en los tres modos. Cierra Keychron Launcher antes de aplicar.",
    applyDpi: "Aplicar %1 DPI",
    applyDpiGeneric: "Aplicar DPI",
    refresh: "Actualizar",
    applying: "Aplicando…",
    updatingStatus: "Actualizando estado…",
    readingStatus: "Leyendo estado…",
    buttonsReadOnly: "BOTONES · SOLO LECTURA",
    remapPending: "El remapeo aún no se ha validado físicamente en este M7.",
    about: "Acerca de",
    backToMouse: "Volver a controles del ratón",
    aboutSummary: "Estado, batería y control de DPI para Keychron M7 8K.",
    developerBy: "Desarrollador · %1",
    helpLinks: "AYUDA Y ENLACES",
    projectRepository: "Repositorio del proyecto",
    reportIssue: "Informar de un problema",
    interfaceLanguage: "IDIOMA DE LA INTERFAZ",
    languageHelp: "Elige Sistema para seguir el idioma del escritorio.",
    languageSystem: "Sistema",
    languageEnglish: "English",
    languageSpanish: "Español",
    dpiAlreadyActive: "El DPI ya estaba activo; no se escribió nada.",
    dpiApplied: "DPI aplicado y confirmado en dos lecturas.",
    dpiAppliedNoAck: "DPI confirmado en dos lecturas; no se recibió ACK.",
    dpiUnconfirmed: "No se pudo confirmar el DPI solicitado; el estado actual es incierto.",
    responseTooLarge: "La respuesta del helper supera el tamaño permitido.",
    readStatusFailed: "No se pudo leer el estado del ratón.",
    confirmDpiFailed: "No se pudo confirmar el cambio de DPI.",
    hidPermission: "No se puede acceder a %1; revisa la ACL uaccess del dispositivo.",
    hidTimeout: "El ratón no respondió al informe HID %1.",
    hidQueueBusy: "La cola de informes HID no se vació; no se envió otro informe.",
    deviceNotFound: "No se ha encontrado el dispositivo compatible: %1.",
    ambiguousDevice: "Se han encontrado varias interfaces Keychron coincidentes; no se selecciona ninguna sin certeza.",
    configInterfaceMissing: "Se ha encontrado %1, pero falta la interfaz de configuración necesaria.",
    unsupportedProtocol: "Versión de protocolo no compatible: %1 (se esperaba la versión 4).",
    mouseNotConfirmed: "No se ha podido confirmar el M7 8K conectado; no se han enviado más consultas.",
    dpiPresetMismatch: "El DPI %1 no figura entre los valores indicados por el receptor; no se ha escrito nada."
  }
}

var helperResultCodes = {
  dpiAlreadyActive: true,
  dpiApplied: true,
  dpiAppliedNoAck: true,
  dpiUnconfirmed: true
}

var helperPatternKeys = {
  hidPermission: "hidPermission",
  hidTimeout: "hidTimeout",
  hidQueueBusy: "hidQueueBusy",
  deviceNotFound: "deviceNotFound",
  ambiguousDevice: "ambiguousDevice",
  configInterfaceMissing: "configInterfaceMissing",
  unsupportedProtocol: "unsupportedProtocol",
  mouseNotConfirmed: "mouseNotConfirmed",
  dpiPresetMismatch: "dpiPresetMismatch"
}

var helperMessageKeys = {
  "La respuesta del helper supera el límite permitido.": "responseTooLarge",
  "No se pudo leer el estado del ratón.": "readStatusFailed",
  "No se pudo confirmar el cambio de DPI.": "confirmDpiFailed"
}

function systemLocaleName() {
  try {
    var locale = Qt.locale()
    if (locale && locale.uiLanguages && locale.uiLanguages.length > 0)
      return String(locale.uiLanguages[0])
    return locale ? String(locale.name || "") : ""
  } catch (error) {
    return ""
  }
}

function languageFromLocale(localeName) {
  var raw = String(localeName || "").toLowerCase().replace(/-/g, "_")
  var language = raw.split("@")[0].split(".")[0].split("_")[0]
  return language === "es" ? "es" : "en"
}

function normalizeOverride(value) {
  var language = String(value || "system").toLowerCase()
  return language === "en" || language === "es" ? language : "system"
}

function resolveLanguage(localeName, override) {
  var selected = normalizeOverride(override)
  return selected === "system" ? languageFromLocale(localeName) : selected
}

function t(key, localeName, override, replacements) {
  var language = resolveLanguage(localeName, override)
  var value = catalogs[language][key]
  if (value === undefined) value = catalogs.en[key]
  if (value === undefined) return "⟦missing:" + key + "⟧"

  var values = Array.isArray(replacements) ? replacements
    : replacements === undefined || replacements === null ? [] : [replacements]
  for (var i = 0; i < values.length; i++)
    value = value.replace(new RegExp("%" + (i + 1), "g"), String(values[i]))
  return value
}

function translateHelperMessage(message, localeName, override, resultCode) {
  if (helperResultCodes[resultCode]) return t(resultCode, localeName, override)

  var text = String(message || "")
  var key = helperMessageKeys[text]
  if (key) return t(key, localeName, override)

  var match = text.match(/^cannot access (.+); check (?:the receiver's|the wired M7's) uaccess ACL$/)
  if (match) return t(helperPatternKeys.hidPermission, localeName, override, match[1])
  match = text.match(/^no matching HID reply on report (0x[0-9a-f]{2})$/i)
  if (match) return t(helperPatternKeys.hidTimeout, localeName, override, match[1])
  if (text === "HID input queue did not drain; refusing to send another report")
    return t(helperPatternKeys.hidQueueBusy, localeName, override)
  if (text === "multiple matching Keychron config interfaces; refusing to guess")
    return t(helperPatternKeys.ambiguousDevice, localeName, override)

  match = text.match(/^(.+) 3434:[0-9a-f]{4} not found$/i)
  if (match) return t(helperPatternKeys.deviceNotFound, localeName, override, match[1])
  match = text.match(/^(.+) found, but no matching 0xFFC1 config interface$/)
  if (match) return t(helperPatternKeys.configInterfaceMissing, localeName, override, match[1])
  match = text.match(/^unsupported (?:receiver|wired M7) protocol v([0-9]+); expected v4$/)
  if (match) return t(helperPatternKeys.unsupportedProtocol, localeName, override, match[1])
  if (text === "connected M7 8K (3434:d056) not confirmed; no further queries sent")
    return t(helperPatternKeys.mouseNotConfirmed, localeName, override)
  match = text.match(/^DPI ([0-9]+) is not one of the receiver's reported presets; no write sent$/)
  if (match) return t(helperPatternKeys.dpiPresetMismatch, localeName, override, match[1])

  return text
}
