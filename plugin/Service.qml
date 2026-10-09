import QtQuick
import Quickshell.Io

Item {
  id: root

  readonly property string helperPath: {
    var url = Qt.resolvedUrl("../helper/m7_hidraw.py").toString()
    return decodeURIComponent(url.replace(/^file:\/\//, ""))
  }
  readonly property bool busy: helper.running
  readonly property bool applying: helper.running && _operation === "set-dpi"
  property var snapshot: null
  property string errorText: ""
  property string resultText: ""
  property string _operation: ""
  property bool _preserveMessages: false
  property bool _retainSnapshot: false
  property bool _clearErrorOnSuccess: false
  readonly property int maxOutputChars: 8192
  readonly property int refreshIntervalMs: 60 * 1000

  function refresh(preserveMessages, retainSnapshot, clearErrorOnSuccess) {
    if (helper.running) return false
    _operation = "status"
    _preserveMessages = preserveMessages === true
    // Keep existing bar data until refresh completes; initial snapshot remains null.
    _retainSnapshot = retainSnapshot !== false
    _clearErrorOnSuccess = clearErrorOnSuccess === true
    if (!_preserveMessages) {
      errorText = ""
      resultText = ""
    }
    if (!_retainSnapshot) snapshot = null
    helper.command = ["python3", helperPath, "status"]
    helper.running = true
    return true
  }

  function applyDpi(dpi) {
    if (helper.running || !snapshot || snapshot.transport !== "2.4 GHz" || !snapshot.status) return false
    if (snapshot.status.dpiPresets.indexOf(dpi) === -1) return false

    _operation = "set-dpi"
    _preserveMessages = false
    errorText = ""
    resultText = ""
    helper.command = ["python3", helperPath, "set-dpi", "--dpi", String(dpi), "--confirm"]
    helper.running = true
    return true
  }

  function _validSnapshot(data) {
    if (!data || data.protocolVersion !== 4 || !data.device || !data.status) return false
    if (data.device.vendorId !== "0x3434" || data.mouse !== "Keychron M7 8K (3434:d056)") return false
    if (data.transport === "USB (cable)") {
      if (data.device.productId !== "0xd056" || data.receiver !== null) return false
    } else if (data.transport === "2.4 GHz") {
      if (data.device.productId !== "0xd028" || !data.receiver) return false
      if (data.receiver.vendorId !== "0x3434" || data.receiver.productId !== "0xd028") return false
    } else {
      return false
    }
    if (!Array.isArray(data.status.dpiPresets) || data.status.dpiPresets.length !== data.status.dpiStageCount) return false
    if (!Array.isArray(data.status.connections) || data.status.connections.length !== 3) return false
    if (!Array.isArray(data.buttons) || data.buttons.length !== 8) return false
    for (var i = 0; i < data.buttons.length; i++) {
      if (typeof data.buttons[i].name !== "string" || data.buttons[i].name.length > 32) return false
      if (typeof data.buttons[i].action !== "string" || data.buttons[i].action.length > 64) return false
    }
    return true
  }

  function _parseOutput(text) {
    if (text.length > maxOutputChars) throw new Error("La respuesta del helper supera el límite permitido.")
    return JSON.parse(text)
  }

  Component.onCompleted: Qt.callLater(function() { root.refresh(false, true, true) })

  Timer {
    interval: root.refreshIntervalMs
    repeat: true
    running: true
    onTriggered: root.refresh(true, true, true)
  }

  Process {
    id: helper
    running: false
    stdout: StdioCollector { id: helperOut; waitForEnd: true }
    stderr: StdioCollector { id: helperErr; waitForEnd: true }

    onExited: function(exitCode) {
      var operation = root._operation
      root._operation = ""
      var output = String(helperOut.text || "")
      var data = null
      try { data = root._parseOutput(output) } catch (error) {
        root.errorText = String(error)
      }

      if (operation === "status") {
        if (exitCode === 0 && root._validSnapshot(data)) {
          root.snapshot = data
          if (!root._preserveMessages || root._clearErrorOnSuccess) root.errorText = ""
        } else {
          if (!root._retainSnapshot) root.snapshot = null
          if (!root.errorText) {
            root.errorText = String((data && data.error) || helperErr.text || "No se pudo leer el estado del ratón.").trim()
          }
        }
        root._preserveMessages = false
        root._retainSnapshot = false
        root._clearErrorOnSuccess = false
        return
      }

      if (operation === "set-dpi") {
        if (data && typeof data.result === "string") root.resultText = data.result
        if (exitCode !== 0 || !data || data.ok !== true) {
          root.errorText = String((data && (data.error || data.result)) || helperErr.text || "No se pudo confirmar el cambio de DPI.").trim()
        }
        root._preserveMessages = true
        Qt.callLater(function() { root.refresh(true) })
      }
    }
  }
}
