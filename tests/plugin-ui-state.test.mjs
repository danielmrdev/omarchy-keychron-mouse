import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

function loadPluginScript(name) {
  const context = {};
  vm.runInNewContext(readFileSync(new URL(`../plugin/${name}`, import.meta.url), "utf8"), context);
  return context;
}

const navigation = loadPluginScript("PanelNavigation.js");
const settings = loadPluginScript("widget-settings.js");

test("About cursor order follows visible controls", () => {
  const expected = ["back", "repository", "issue", "system", "en", "es"];
  assert.deepEqual(expected.map((_, index) => navigation.aboutItem(index)), expected);
  assert.equal(navigation.aboutItem(-1), "");
  assert.equal(navigation.nextAboutCursor(0, 1), navigation.ABOUT.repository);
  assert.equal(navigation.nextAboutCursor(0, -1), navigation.ABOUT.spanish);
});

test("About arrow navigation follows layout and selected language", () => {
  assert.equal(navigation.moveAboutCursor(navigation.ABOUT.back, 0, 1, "system"), navigation.ABOUT.repository);
  assert.equal(navigation.moveAboutCursor(navigation.ABOUT.issue, 0, 1, "en"), navigation.ABOUT.english);
  assert.equal(navigation.moveAboutCursor(navigation.ABOUT.spanish, 0, -1, "es"), navigation.ABOUT.issue);
  assert.equal(navigation.moveAboutCursor(navigation.ABOUT.system, 1, 0, "system"), navigation.ABOUT.english);
  assert.equal(navigation.moveAboutCursor(navigation.ABOUT.system, -1, 0, "system"), navigation.ABOUT.spanish);
});

test("language preference update preserves other widget settings and survives JSON reload", () => {
  const current = {
    id: "danielmrdev.omarchy-keychron-mouse",
    showBatteryInBar: false,
    uiLanguage: "system"
  };
  const updated = settings.updatedEntry(current, current.id, "uiLanguage", "es");

  assert.deepEqual(
    JSON.parse(JSON.stringify(updated)),
    {
      id: current.id,
      showBatteryInBar: false,
      uiLanguage: "es"
    }
  );
  assert.equal(JSON.parse(JSON.stringify(updated)).uiLanguage, "es");
  assert.deepEqual(
    JSON.parse(JSON.stringify(settings.updatedEntry(null, current.id, "uiLanguage", "en"))),
    { id: current.id, uiLanguage: "en" }
  );
});
