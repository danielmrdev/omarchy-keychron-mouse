import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "daniel.keychron-m7"

  readonly property var deviceService: bar && bar.shell && typeof bar.shell.serviceFor === "function"
    ? bar.shell.serviceFor(moduleName)
    : null
  readonly property var mouseStatus: deviceService && deviceService.snapshot
    ? deviceService.snapshot.status
    : null
  readonly property bool showBatteryInBar: setting("showBatteryInBar", true) === true
  readonly property bool batteryPercentAvailable: mouseStatus
    && typeof mouseStatus.batteryPercent === "number"
    && mouseStatus.batteryPercent >= 0
    && mouseStatus.batteryPercent <= 100
  readonly property bool batteryCharging: mouseStatus && mouseStatus.batteryCharging === true
  readonly property bool batteryLabelVisible: showBatteryInBar
    && (batteryPercentAvailable || batteryCharging)
  readonly property string mouseGlyph: "󰍽"
  readonly property string chargingGlyph: ""
  readonly property string batteryText: {
    var text = batteryPercentAvailable ? String(mouseStatus.batteryPercent) + "%" : ""
    if (batteryCharging) text += (text === "" ? "" : "\u2009") + chargingGlyph
    return text
  }
  readonly property string barMarkup: {
    var icon = '<span style="font-size:' + Style.bar.iconFont + 'px">' + mouseGlyph + '</span>'
    if (!batteryLabelVisible) return icon
    var battery = '<span style="font-size:' + Style.font.body + 'px">' + batteryText + '</span>'
    return vertical ? icon + '<br/>' + battery : icon + ' ' + battery
  }
  readonly property string barTooltip: {
    var text = "Keychron M7 8K"
    if (showBatteryInBar && batteryPercentAvailable) text += " · " + mouseStatus.batteryPercent + "%"
    if (showBatteryInBar && batteryCharging) text += " · cargando"
    return text
  }

  function setShowBatteryInBar(enabled) {
    var entry = { id: moduleName }
    for (var key in settings) if (key !== "id") entry[key] = settings[key]
    entry.showBatteryInBar = enabled === true
    settings = entry
    if (bar && bar.shell && typeof bar.shell.updateEntryInline === "function")
      bar.shell.updateEntryInline(moduleName, entry)
  }

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("anchorItem" in target) target.anchorItem = panelAnchor
    if ("hostWidget" in target) target.hostWidget = root
    if ("service" in target) target.service = root.deviceService
  }

  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property bool popoutSwitchClosing: panelLoader.item
    ? panelLoader.item.popoutSwitchClosing === true
    : false

  function open() {
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function closeForPopoutSwitch() {
    if (panelLoader.item && typeof panelLoader.item.closeForPopoutSwitch === "function")
      panelLoader.item.closeForPopoutSwitch()
  }

  function toggle() {
    if (panelLoader.item) panelLoader.item.toggle()
  }

  implicitWidth: vertical
    ? (bar ? bar.barSize : Style.bar.sizeVertical)
    : barLabel.implicitWidth
  implicitHeight: vertical
    ? Math.max(Style.bar.iconSlot, barLabel.implicitHeight)
    : (bar ? bar.barSize : Style.bar.sizeHorizontal)
  readonly property real openPanelIndicatorWidth: implicitWidth
  readonly property real openPanelIndicatorHeight: implicitHeight

  onBarChanged: Qt.callLater(injectPanel)
  onDeviceServiceChanged: Qt.callLater(injectPanel)
  Component.onCompleted: Qt.callLater(injectPanel)

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: Qt.callLater(root.injectPanel)
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    hasVisualContent: true
    labelVisible: false
    active: panelLoader.item ? panelLoader.item.opened : false
    useActiveColor: false
    tooltipText: root.barTooltip
    onPressed: function(buttonCode) {
      if (buttonCode === Qt.LeftButton) root.toggle()
    }
  }

  Item {
    id: panelAnchor
    width: root.vertical ? root.width : Style.bar.iconSlot
    height: root.vertical ? Style.bar.iconSlot : root.height
  }

  Text {
    id: barLabel
    anchors.centerIn: parent
    textFormat: Text.RichText
    text: root.barMarkup
    color: root.bar ? root.bar.barForeground : Color.foreground
    font.family: root.bar ? root.bar.fontFamily : Style.font.family
    font.pixelSize: Style.bar.iconFont
    renderType: Text.NativeRendering
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    wrapMode: Text.NoWrap
  }
}
