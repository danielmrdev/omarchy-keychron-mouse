import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const context = { Qt: { locale: () => ({ uiLanguages: [], name: "en_US" }) } };
vm.runInNewContext(readFileSync(new URL("../plugin/i18n.js", import.meta.url), "utf8"), context);

test("English and Spanish catalogs have identical keys", () => {
  assert.deepEqual(Object.keys(context.catalogs.es).sort(), Object.keys(context.catalogs.en).sort());
});

test("every QML translation reference exists in the catalogs", () => {
  const qml = ["BarWidget.qml", "Panel.qml"]
    .map((name) => readFileSync(new URL(`../plugin/${name}`, import.meta.url), "utf8"))
    .join("\n");
  const used = new Set([...qml.matchAll(/\btr\("([^"]+)"/g)].map((match) => match[1]));
  for (const key of Object.values(context.helperMessageKeys)) used.add(key);
  for (const key of Object.values(context.helperPatternKeys)) used.add(key);
  for (const key of Object.keys(context.helperResultCodes)) used.add(key);
  assert.deepEqual([...used].sort(), Object.keys(context.catalogs.en).sort());
});

test("system locale accepts common Spanish locale forms", () => {
  for (const locale of ["es", "es-ES", "es_ES.UTF-8", "es.utf8"]) {
    assert.equal(context.languageFromLocale(locale), "es", locale);
  }
  assert.equal(context.languageFromLocale("fr_FR.UTF-8"), "en");
});

test("system resolution prefers Qt UI language over formatting locale", () => {
  context.Qt.locale = () => ({ uiLanguages: ["es-ES", "en-US"], name: "en_US" });
  assert.equal(context.systemLocaleName(), "es-ES");
  assert.equal(context.resolveLanguage(context.systemLocaleName(), "system"), "es");
});

test("explicit supported override wins; invalid values return to system", () => {
  assert.equal(context.resolveLanguage("es_ES", "en"), "en");
  assert.equal(context.resolveLanguage("en_US", "es"), "es");
  assert.equal(context.resolveLanguage("es_ES", "unsupported"), "es");
});

test("translation falls back to English, then exposes missing keys", () => {
  const spanish = context.catalogs.es.batteryUnavailable;
  delete context.catalogs.es.batteryUnavailable;
  assert.equal(context.t("batteryUnavailable", "es", "system"), "Battery: data unavailable");
  context.catalogs.es.batteryUnavailable = spanish;
  assert.equal(context.t("missingKey", "en", "en"), "⟦missing:missingKey⟧");
});

test("translation interpolates values and localizes helper results", () => {
  assert.equal(context.t("profile", "en", "en", [2, 5]), "Profile 2 / 5");
  assert.equal(context.t("profile", "es", "es", [2, 5]), "Perfil 2 / 5");
  assert.equal(
    context.translateHelperMessage("DPI ya estaba activo; no se escribió nada", "en", "en", "dpiAlreadyActive"),
    "DPI was already active; no write was sent."
  );
  assert.equal(context.translateHelperMessage("permission denied", "es", "es"), "permission denied");
  assert.equal(
    context.translateHelperMessage("cannot access /dev/hidraw2; check the receiver's uaccess ACL", "es", "es"),
    "No se puede acceder a /dev/hidraw2; revisa la ACL uaccess del dispositivo."
  );
  assert.equal(
    context.translateHelperMessage("no matching HID reply on report 0xb4", "es", "es"),
    "El ratón no respondió al informe HID 0xb4."
  );
});
