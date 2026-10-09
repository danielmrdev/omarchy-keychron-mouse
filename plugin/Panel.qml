import QtQuick
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "danielmrdev.omarchy-keychron-mouse"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  property var service: null
  property int pendingDpi: -1
  property int cursorIndex: 0
  property bool cursorActive: false

  readonly property color foreground: Color.popups.text
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property var snapshot: service ? service.snapshot : null
  readonly property var mouseStatus: snapshot ? snapshot.status : null
  readonly property var presets: mouseStatus ? mouseStatus.dpiPresets : []
  readonly property var connections: mouseStatus ? mouseStatus.connections : []
  readonly property var buttonMappings: snapshot ? snapshot.buttons : []
  readonly property bool busy: service ? service.busy : false
  readonly property bool showBatteryInBar: hostWidget && typeof hostWidget.showBatteryInBar === "boolean"
    ? hostWidget.showBatteryInBar
    : true

  function currentDpi(connection) {
    if (!mouseStatus || !connection) return "—"
    return String(presets[connection.activeDpiStage - 1])
  }

  function batteryText() {
    if (!mouseStatus || typeof mouseStatus.batteryPercent !== "number") return "Batería: dato no disponible"
    return "Batería: " + mouseStatus.batteryPercent + "% · "
      + (mouseStatus.batteryCharging ? "cargando" : "no cargando")
  }

  function syncPendingDpi() {
    if (!mouseStatus || !connections || connections.length === 0) return
    var stage = connections[0].activeDpiStage
    if (stage < 1 || stage > presets.length) return
    pendingDpi = presets[stage - 1]
    var presetIndex = presets.indexOf(pendingDpi)
    cursorIndex = presetIndex >= 0 ? presetIndex + 1 : 1
  }

  function selectDpi(index) {
    if (index < 0 || index >= presets.length) return
    pendingDpi = presets[index]
    cursorIndex = index + 1
    cursorActive = true
  }

  function toggleBatterySetting() {
    if (hostWidget && typeof hostWidget.setShowBatteryInBar === "function")
      hostWidget.setShowBatteryInBar(!showBatteryInBar)
  }

  function needsDpiApply() {
    if (!mouseStatus || pendingDpi < 0) return false
    for (var i = 0; i < connections.length; i++) {
      if (currentDpi(connections[i]) !== String(pendingDpi)) return true
    }
    return false
  }

  function applyDpi() {
    if (service && !busy && needsDpiApply()) service.applyDpi(pendingDpi)
  }

  function moveCursor(dx, dy) {
    cursorActive = true
    if (dy > 0) {
      if (cursorIndex === 0) cursorIndex = 1
      else if (cursorIndex < 6) cursorIndex = 6
      else if (cursorIndex === 6) cursorIndex = 7
      else cursorIndex = 0
    } else if (dy < 0) {
      if (cursorIndex === 7) cursorIndex = 6
      else if (cursorIndex === 6) cursorIndex = 1
      else cursorIndex = 0
    } else if (dx > 0) {
      if (cursorIndex > 0 && cursorIndex < 5) cursorIndex++
      else if (cursorIndex === 6) cursorIndex = 7
    } else if (dx < 0) {
      if (cursorIndex > 1 && cursorIndex <= 5) cursorIndex--
      else if (cursorIndex === 6) cursorIndex = 5
      else if (cursorIndex === 7) cursorIndex = 6
    }
  }

  function activateCursor() {
    if (cursorIndex === 0) toggleBatterySetting()
    else if (cursorIndex <= 5) selectDpi(cursorIndex - 1)
    else if (cursorIndex === 6) applyDpi()
    else if (cursorIndex === 7 && service && !busy) service.refresh(false)
  }

  function tabCursor(direction) {
    cursorActive = true
    cursorIndex = (cursorIndex + direction + 8) % 8
  }

  onServiceChanged: Qt.callLater(syncPendingDpi)
  onOpenedChanged: {
    if (!opened) return
    cursorActive = false
    if (service) service.refresh(false)
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  Connections {
    target: root.service
    function onSnapshotChanged() { root.syncPendingDpi() }
  }

  KeyboardPanel {
    id: popup
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: popup.fittedContentWidth(Style.space(390))
    contentHeight: popup.fittedContentHeight(body.implicitHeight, Style.space(620))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onMoveRequested: function(dx, dy) { root.moveCursor(dx, dy) }
      onActivateRequested: root.activateCursor()
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.tabCursor(direction) }

      Column {
        id: body
        width: parent.width
        spacing: Style.space(10)

        PanelHero {
          title: "Keychron M7 8K"
          meta: root.snapshot
            ? (root.snapshot.transport === "USB (cable)" ? "M7 conectado por cable" : "Ultra-Link 8K · M7 enlazado")
            : "Esperando lectura del M7"
          foreground: root.foreground
          fontFamily: root.fontFamily
          iconComponent: Component {
            Text {
              textFormat: Text.PlainText
              text: "󰍽"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.display
            }
          }
        }

        Toggle {
          width: parent.width
          label: "Mostrar batería en barra"
          description: "Porcentaje y rayo cuando está cargando."
          checked: root.showBatteryInBar
          hasCursor: root.cursorActive && root.cursorIndex === 0
          foreground: root.foreground
          fontFamily: root.fontFamily
          enabled: !!root.hostWidget && typeof root.hostWidget.setShowBatteryInBar === "function"
          onHovered: function(hovered) {
            if (hovered) { root.cursorIndex = 0; root.cursorActive = true }
          }
          onClicked: root.toggleBatterySetting()
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader { text: "CONEXIÓN Y BATERÍA"; foreground: root.foreground; fontFamily: root.fontFamily }

        Column {
          width: parent.width
          spacing: Style.space(3)

          Text {
            textFormat: Text.PlainText
            text: root.snapshot ? "Modo activo: " + root.snapshot.transport : "Modo activo: —"
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
          Text {
            textFormat: Text.PlainText
            text: root.snapshot ? root.batteryText() : "Batería: —"
            color: root.mouseStatus && root.mouseStatus.batteryPercent !== null && root.mouseStatus.batteryPercent <= 15
              ? Color.urgent : root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.Wrap
            width: parent.width
          }
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader { text: "DPI · COMPARTIDO"; foreground: root.foreground; fontFamily: root.fontFamily }
        Text {
          textFormat: Text.PlainText
          text: root.snapshot && root.snapshot.transport === "USB (cable)"
            ? "Lectura por cable; aplicar DPI sigue limitado al receptor 2,4 GHz."
            : "El protocolo aplica una sola etapa a USB, 2,4 GHz y Bluetooth. Cierra Launcher antes de cambiar DPI."
          color: Color.muted
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }

        Row {
          id: presetRow
          width: parent.width
          spacing: Style.space(4)

          Repeater {
            model: root.presets
            delegate: Button {
              required property int index
              required property int modelData
              width: (presetRow.width - presetRow.spacing * 4) / 5
              text: String(modelData)
              fontFamily: root.fontFamily
              fontSize: Style.font.bodySmall
              horizontalPadding: Style.space(4)
              selected: root.pendingDpi === modelData
              hasCursor: root.cursorActive && root.cursorIndex === index + 1
              enabled: !!root.mouseStatus && !root.busy
              onHovered: function(hovered) {
                if (hovered) { root.cursorIndex = index + 1; root.cursorActive = true }
              }
              onClicked: root.selectDpi(index)
            }
          }
        }

        Column {
          width: parent.width
          spacing: Style.space(2)

          Repeater {
            model: root.connections
            delegate: Text {
              required property var modelData
              textFormat: Text.PlainText
              text: modelData.name + " · " + root.currentDpi(modelData) + " DPI · " + modelData.pollingHz + " Hz"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall
            }
          }

          Text {
            visible: !!root.mouseStatus
            textFormat: Text.PlainText
            text: root.mouseStatus ? "Perfil " + root.mouseStatus.onboardProfile + " / " + root.mouseStatus.onboardProfileCount : ""
            color: Color.muted
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
        }

        Text {
          textFormat: Text.PlainText
          text: "Aplicar cambia la etapa activa en los tres modos. Cierra Launcher antes de aplicar."
          color: Color.muted
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }

        Row {
          width: parent.width
          spacing: Style.space(6)

          Button {
            id: applyButton
            width: parent.width - refreshButton.implicitWidth - parent.spacing
            text: root.pendingDpi > 0 ? "Aplicar " + root.pendingDpi + " DPI" : "Aplicar DPI"
            fontFamily: root.fontFamily
            selected: true
            hasCursor: root.cursorActive && root.cursorIndex === 6
            enabled: !!root.mouseStatus && root.snapshot.transport === "2.4 GHz"
              && !root.busy && root.needsDpiApply()
            onHovered: function(hovered) {
              if (hovered) { root.cursorIndex = 6; root.cursorActive = true }
            }
            onClicked: root.applyDpi()
          }
          Button {
            id: refreshButton
            text: "Actualizar"
            fontFamily: root.fontFamily
            hasCursor: root.cursorActive && root.cursorIndex === 7
            enabled: !!root.service && !root.busy
            onHovered: function(hovered) {
              if (hovered) { root.cursorIndex = 7; root.cursorActive = true }
            }
            onClicked: if (root.service) root.service.refresh(false)
          }
        }

        Text {
          visible: root.busy
          textFormat: Text.PlainText
          text: root.service && root.service.applying ? "Aplicando…"
            : root.service && root.service.snapshot ? "Actualizando estado…" : "Leyendo estado…"
          color: Color.accent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
        Text {
          visible: !!(root.service && root.service.resultText)
          textFormat: Text.PlainText
          text: root.service ? root.service.resultText : ""
          color: Color.accent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }
        Text {
          visible: !!(root.service && root.service.errorText)
          textFormat: Text.PlainText
          text: root.service ? root.service.errorText : ""
          color: Color.urgent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader { text: "BOTONES · SOLO LECTURA"; foreground: root.foreground; fontFamily: root.fontFamily }
        Text {
          textFormat: Text.PlainText
          text: "Remapeo pendiente de validar físicamente en este M7."
          color: Color.muted
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }

        Grid {
          id: buttonGrid
          width: parent.width
          columns: 2
          columnSpacing: Style.space(12)
          rowSpacing: Style.space(3)

          Repeater {
            model: root.buttonMappings
            delegate: Item {
              required property var modelData
              width: (buttonGrid.width - buttonGrid.columnSpacing) / 2
              height: Style.space(22)

              Row {
                anchors.fill: parent
                spacing: Style.space(4)
                Text {
                  textFormat: Text.PlainText
                  width: parent.width * 0.47
                  text: modelData.name
                  color: root.foreground
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  elide: Text.ElideRight
                  verticalAlignment: Text.AlignVCenter
                }
                Text {
                  textFormat: Text.PlainText
                  width: parent.width * 0.53 - parent.spacing
                  text: modelData.action
                  color: Color.muted
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  elide: Text.ElideRight
                  horizontalAlignment: Text.AlignRight
                  verticalAlignment: Text.AlignVCenter
                }
              }
            }
          }
        }
      }
    }
  }
}
