import QtQuick
import qs.Commons
import qs.Ui
import "i18n.js" as I18n
import "PanelNavigation.js" as Navigation

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
  property string currentPage: "mouse"

  // Keep in sync with manifest.json.
  readonly property string pluginName: "Keychron M7 8K"
  readonly property string pluginVersion: "0.1.0"
  readonly property string pluginAuthor: "Daniel"
  readonly property string projectUrl: "https://github.com/danielmrdev/omarchy-keychron-mouse"
  readonly property string issueUrl: projectUrl + "/issues"
  readonly property string systemLocaleName: I18n.systemLocaleName()
  readonly property string uiLanguage: hostWidget && typeof hostWidget.uiLanguage === "string"
    ? I18n.normalizeOverride(hostWidget.uiLanguage)
    : "system"
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

  function tr(key, replacements) {
    return I18n.t(key, systemLocaleName, uiLanguage, replacements)
  }

  function displayMessage(message, code) {
    return I18n.translateHelperMessage(message, systemLocaleName, uiLanguage, code)
  }

  function transportLabel() {
    if (!snapshot) return ""
    if (snapshot.transport === "USB (cable)") return tr("connectedWired")
    if (snapshot.transport === "2.4 GHz") return tr("connectedWireless")
    return String(snapshot.transport)
  }

  function setUiLanguage(language) {
    if (hostWidget && typeof hostWidget.setUiLanguage === "function")
      hostWidget.setUiLanguage(language)
  }

  function showAbout() {
    currentPage = "about"
    cursorIndex = Navigation.ABOUT.back
    cursorActive = true
  }

  function showMouseControls() {
    currentPage = "mouse"
    cursorIndex = 8
    cursorActive = true
  }

  function currentDpi(connection) {
    if (!mouseStatus || !connection) return "—"
    return String(presets[connection.activeDpiStage - 1])
  }

  function batteryText() {
    if (!mouseStatus || typeof mouseStatus.batteryPercent !== "number") return tr("batteryUnavailable")
    return tr("batteryValue", [mouseStatus.batteryPercent,
      mouseStatus.batteryCharging ? tr("charging") : tr("notCharging")])
  }

  function syncPendingDpi() {
    if (!mouseStatus || !connections || connections.length === 0) return
    var stage = connections[0].activeDpiStage
    if (stage < 1 || stage > presets.length) return
    pendingDpi = presets[stage - 1]
    var presetIndex = presets.indexOf(pendingDpi)
    if (currentPage === "mouse") cursorIndex = presetIndex >= 0 ? presetIndex + 1 : 1
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
    if (currentPage === "about") {
      cursorIndex = Navigation.moveAboutCursor(cursorIndex, dx, dy, uiLanguage)
      return
    }

    if (dy > 0) {
      if (cursorIndex === 0) cursorIndex = 1
      else if (cursorIndex < 6) cursorIndex = 6
      else if (cursorIndex === 6) cursorIndex = 7
      else if (cursorIndex === 7) cursorIndex = 8
      else cursorIndex = 0
    } else if (dy < 0) {
      if (cursorIndex === 8) cursorIndex = 7
      else if (cursorIndex === 7) cursorIndex = 6
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
    if (currentPage === "about") {
      var aboutItem = Navigation.aboutItem(cursorIndex)
      if (aboutItem === "back") showMouseControls()
      else if (aboutItem === "repository") Qt.openUrlExternally(projectUrl)
      else if (aboutItem === "issue") Qt.openUrlExternally(issueUrl)
      else if (aboutItem === "system" || aboutItem === "en" || aboutItem === "es")
        setUiLanguage(aboutItem)
      return
    }

    if (cursorIndex === 0) toggleBatterySetting()
    else if (cursorIndex <= 5) selectDpi(cursorIndex - 1)
    else if (cursorIndex === 6) applyDpi()
    else if (cursorIndex === 7 && service && !busy) service.refresh(false)
    else if (cursorIndex === 8) showAbout()
  }

  function tabCursor(direction) {
    cursorActive = true
    if (currentPage === "about") cursorIndex = Navigation.nextAboutCursor(cursorIndex, direction)
    else cursorIndex = (cursorIndex + direction + 9) % 9
  }

  onServiceChanged: Qt.callLater(syncPendingDpi)
  onOpenedChanged: {
    if (!opened) return
    currentPage = "mouse"
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

      Loader {
        id: body
        width: parent.width
        sourceComponent: root.currentPage === "about" ? aboutPageComponent : mousePageComponent
      }

    Component {
      id: mousePageComponent

      Column {
        width: body.width
        spacing: Style.space(10)

        Row {
          width: parent.width
          height: aboutButton.implicitHeight

          Item {
            width: Math.max(0, parent.width - aboutButton.implicitWidth)
            height: aboutButton.implicitHeight
          }

          Button {
            id: aboutButton
            text: root.tr("about")
            fontFamily: root.fontFamily
            hasCursor: root.cursorActive && root.cursorIndex === 8
            onHovered: function(hovered) {
              if (hovered) { root.cursorIndex = 8; root.cursorActive = true }
            }
            onClicked: root.showAbout()
          }
        }

        Item {
          id: hero
          width: parent.width
          height: Math.max(mouseGlyph.implicitHeight, heroLabels.implicitHeight)

          Text {
            id: mouseGlyph
            textFormat: Text.PlainText
            text: "󰍽"
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.display
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }

          Column {
            id: heroLabels
            anchors.left: mouseGlyph.right
            anchors.leftMargin: Style.space(14)
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(2)

            Item {
              id: titleRow
              implicitWidth: titleText.implicitWidth + Style.space(8) + versionText.implicitWidth
              implicitHeight: Math.max(titleText.implicitHeight, versionText.implicitHeight)
              width: implicitWidth
              height: implicitHeight

              Text {
                id: titleText
                textFormat: Text.PlainText
                text: root.pluginName
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.title
                font.bold: true
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
              }
              Text {
                id: versionText
                textFormat: Text.PlainText
                text: "v" + root.pluginVersion
                color: Qt.darker(root.foreground, 1.4)
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                anchors.left: titleText.right
                anchors.leftMargin: Style.space(8)
                anchors.verticalCenter: parent.verticalCenter
              }
            }

            Text {
              textFormat: Text.PlainText
              text: (root.snapshot ? root.transportLabel() : root.tr("waitingForMouse")).toUpperCase()
              color: Qt.darker(root.foreground, 1.4)
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              font.bold: true
              font.letterSpacing: 1.2
              elide: Text.ElideRight
            }
          }
        }

        Toggle {
          width: parent.width
          label: root.tr("showBatteryInBar")
          description: root.tr("batterySettingDescription")
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
        PanelSectionHeader { text: root.tr("connectionBattery"); foreground: root.foreground; fontFamily: root.fontFamily }

        Column {
          width: parent.width
          spacing: Style.space(3)

          Text {
            textFormat: Text.PlainText
            text: root.snapshot ? root.tr("activeMode", root.transportLabel()) : root.tr("activeMode", "—")
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
          Text {
            textFormat: Text.PlainText
            text: root.snapshot ? root.batteryText() : root.tr("batteryEmpty")
            color: root.mouseStatus && root.mouseStatus.batteryPercent !== null && root.mouseStatus.batteryPercent <= 15
              ? Color.urgent : root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
            wrapMode: Text.Wrap
            width: parent.width
          }
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader { text: root.tr("dpiShared"); foreground: root.foreground; fontFamily: root.fontFamily }
        Text {
          textFormat: Text.PlainText
          text: root.snapshot && root.snapshot.transport === "USB (cable)"
            ? root.tr("cableDpiNote") : root.tr("sharedDpiNote")
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
            text: root.mouseStatus ? root.tr("profile", [root.mouseStatus.onboardProfile, root.mouseStatus.onboardProfileCount]) : ""
            color: Color.muted
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
        }

        Text {
          textFormat: Text.PlainText
          text: root.tr("applyWarning")
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
            text: root.pendingDpi > 0 ? root.tr("applyDpi", root.pendingDpi) : root.tr("applyDpiGeneric")
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
            text: root.tr("refresh")
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
          text: root.service && root.service.applying ? root.tr("applying")
            : root.service && root.service.snapshot ? root.tr("updatingStatus") : root.tr("readingStatus")
          color: Color.accent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
        Text {
          visible: !!(root.service && root.service.resultText)
          textFormat: Text.PlainText
          text: root.service
            ? root.displayMessage(root.service.resultText, root.service.resultCode) : ""
          color: Color.accent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }
        Text {
          visible: !!(root.service && root.service.errorText)
          textFormat: Text.PlainText
          text: root.service ? root.displayMessage(root.service.errorText) : ""
          color: Color.urgent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader { text: root.tr("buttonsReadOnly"); foreground: root.foreground; fontFamily: root.fontFamily }
        Text {
          textFormat: Text.PlainText
          text: root.tr("remapPending")
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

    Component {
      id: aboutPageComponent

      Column {
        width: body.width
        spacing: Style.space(10)

        Row {
          width: parent.width
          height: Math.max(aboutPageTitle.implicitHeight, backButton.implicitHeight)
          spacing: Style.space(6)

          Text {
            id: aboutPageTitle
            textFormat: Text.PlainText
            text: root.tr("about")
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.title
            font.bold: true
            width: Math.max(0, parent.width - backButton.implicitWidth - parent.spacing)
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
          }

          Button {
            id: backButton
            text: root.tr("backToMouse")
            fontFamily: root.fontFamily
            hasCursor: root.cursorActive && root.cursorIndex === Navigation.ABOUT.back
            onHovered: function(hovered) {
              if (hovered) { root.cursorIndex = Navigation.ABOUT.back; root.cursorActive = true }
            }
            onClicked: root.showMouseControls()
          }
        }

        Item {
          width: parent.width
          height: Math.max(aboutGlyph.implicitHeight, aboutLabels.implicitHeight)

          Text {
            id: aboutGlyph
            textFormat: Text.PlainText
            text: "󰍽"
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.font.display
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }

          Column {
            id: aboutLabels
            anchors.left: aboutGlyph.right
            anchors.leftMargin: Style.space(14)
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(2)

            Item {
              width: parent.width
              height: Math.max(aboutTitle.implicitHeight, aboutVersion.implicitHeight)

              Text {
                id: aboutTitle
                textFormat: Text.PlainText
                text: root.pluginName
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.title
                font.bold: true
                width: Math.max(0, parent.width - aboutVersion.implicitWidth - Style.space(8))
                elide: Text.ElideRight
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
              }

              Text {
                id: aboutVersion
                textFormat: Text.PlainText
                text: "v" + root.pluginVersion
                color: root.foreground
                opacity: 0.6
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
              }
            }

            Text {
              textFormat: Text.PlainText
              text: root.tr("developerBy", root.pluginAuthor)
              color: Color.foreground
              opacity: 0.6
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              elide: Text.ElideRight
              width: parent.width
            }
          }
        }

        Text {
          textFormat: Text.PlainText
          text: root.tr("aboutSummary")
          color: Color.foreground
          opacity: 0.6
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader {
          text: root.tr("helpLinks")
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        Column {
          width: parent.width
          spacing: Style.space(4)

          Button {
            width: parent.width
            text: root.tr("projectRepository")
            fontFamily: root.fontFamily
            hasCursor: root.cursorActive && root.cursorIndex === Navigation.ABOUT.repository
            onHovered: function(hovered) {
              if (hovered) { root.cursorIndex = Navigation.ABOUT.repository; root.cursorActive = true }
            }
            onClicked: Qt.openUrlExternally(root.projectUrl)
          }

          Button {
            width: parent.width
            text: root.tr("reportIssue")
            fontFamily: root.fontFamily
            hasCursor: root.cursorActive && root.cursorIndex === Navigation.ABOUT.issue
            onHovered: function(hovered) {
              if (hovered) { root.cursorIndex = Navigation.ABOUT.issue; root.cursorActive = true }
            }
            onClicked: Qt.openUrlExternally(root.issueUrl)
          }
        }

        PanelSeparator { width: parent.width }
        PanelSectionHeader {
          text: root.tr("interfaceLanguage")
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        ButtonGroup {
          options: [
            { value: "system", label: root.tr("languageSystem") },
            { value: "en", label: root.tr("languageEnglish") },
            { value: "es", label: root.tr("languageSpanish") }
          ]
          value: root.uiLanguage
          foreground: root.foreground
          fontFamily: root.fontFamily
          fontSize: Style.font.bodySmall
          focusable: false
          cursorIndex: root.cursorActive
            && root.cursorIndex >= Navigation.ABOUT.system
            && root.cursorIndex <= Navigation.ABOUT.spanish
            ? root.cursorIndex - Navigation.ABOUT.system : -1
          onHovered: function(index, hovered) {
            if (hovered) {
              root.cursorIndex = Navigation.ABOUT.system + index
              root.cursorActive = true
            }
          }
          onChanged: function(language) { root.setUiLanguage(language) }
        }

        Text {
          textFormat: Text.PlainText
          text: root.tr("languageHelp")
          color: Color.foreground
          opacity: 0.6
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.Wrap
          width: parent.width
        }
      }
    }
    }
  }
}
