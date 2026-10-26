"""Tests: Sensoren, Ausschlüsse, Einstellungen und WebSocket."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.unser_zuhause.const import DEFAULT_OPTIONS, DOMAIN


def _sensor(hass: HomeAssistant, key: str, platform: str = "sensor"):
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"test_{key}")
    assert entity_id, key
    return hass.states.get(entity_id)


async def _setup(hass: HomeAssistant, options=None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test", options=options or dict(DEFAULT_OPTIONS))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_counts(hass: HomeAssistant) -> None:
    hass.states.async_set("light.wohnzimmer", "on")
    hass.states.async_set("light.kueche", "off")
    hass.states.async_set("light.gruppe", "on", {"entity_id": ["light.wohnzimmer"]})
    hass.states.async_set("cover.bad", "open", {"device_class": "shutter"})
    hass.states.async_set("cover.garage", "open", {"device_class": "garage"})
    hass.states.async_set("cover.ohne", "opening")
    hass.states.async_set("binary_sensor.fenster", "on", {"device_class": "window"})
    hass.states.async_set("binary_sensor.bewegung", "on", {"device_class": "motion"})
    # Tankerkönig: „Tankstelle geöffnet“ hat die allgemeine Klasse opening → zählt standardmäßig nicht
    hass.states.async_set("binary_sensor.tankstelle_status", "on", {"device_class": "opening"})
    hass.states.async_set("person.a", "home")
    hass.states.async_set("person.b", "not_home")
    await _setup(hass)

    lights = _sensor(hass, "lights_on")
    assert lights.state == "1"
    assert lights.attributes["entity_id"] == ["light.wohnzimmer"]
    assert _sensor(hass, "covers_open").state == "2"  # Garage zählt standardmäßig nicht
    assert _sensor(hass, "openings_count").state == "1"
    assert _sensor(hass, "openings_open", "binary_sensor").state == "on"
    assert _sensor(hass, "persons_home").state == "1"

    # Live-Aktualisierung
    hass.states.async_set("binary_sensor.fenster", "off", {"device_class": "window"})
    hass.states.async_set("light.kueche", "on")
    await hass.async_block_till_done()
    assert _sensor(hass, "openings_open", "binary_sensor").state == "off"
    assert _sensor(hass, "lights_on").state == "2"


async def test_exclusions(hass: HomeAssistant) -> None:
    label = lr.async_get(hass).async_create("no_dboard")
    ent_reg = er.async_get(hass)
    hidden = ent_reg.async_get_or_create("light", "test", "versteckt", suggested_object_id="versteckt")
    ent_reg.async_update_entity(hidden.entity_id, hidden_by=er.RegistryEntryHider.USER)
    labelled = ent_reg.async_get_or_create("light", "test", "label", suggested_object_id="mit_label")
    ent_reg.async_update_entity(labelled.entity_id, labels={label.label_id})
    for entity_id in ("light.versteckt", "light.mit_label", "light.normal", "light.einzeln"):
        hass.states.async_set(entity_id, "on")
    await _setup(hass, {**DEFAULT_OPTIONS, "exclude_label": label.label_id, "exclude_entities": ["light.einzeln"]})
    assert _sensor(hass, "lights_on").attributes["entity_id"] == ["light.normal"]

    # Label nachträglich entfernen → zählt wieder mit
    ent_reg.async_update_entity(labelled.entity_id, labels=set())
    await hass.async_block_till_done()
    assert _sensor(hass, "lights_on").attributes["entity_id"] == ["light.mit_label", "light.normal"]


async def test_config_and_options_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"cover_classes": ["shutter"], "opening_classes": ["window"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.options["cover_classes"] == ["shutter"]
    await hass.async_block_till_done()

    # Nur eine Einrichtung
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert again["type"] is FlowResultType.ABORT

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"cover_classes": ["shutter", "garage"], "opening_classes": ["window", "door"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["opening_classes"] == ["window", "door"]


async def test_websocket(hass: HomeAssistant, hass_ws_client) -> None:
    hass.states.async_set("cover.garage", "open", {"device_class": "garage"})
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "unser_zuhause/get_options"})
    msg = await client.receive_json()
    assert msg["success"]
    assert "garage" in msg["result"]["cover_classes"]
    assert msg["result"]["options"]["exclude_label"] == "no_dboard"

    await client.send_json_auto_id({"type": "unser_zuhause/set_options", "cover_classes": ["garage"]})
    msg = await client.receive_json()
    assert msg["success"]
    await hass.async_block_till_done()
    assert entry.options["cover_classes"] == ["garage"]
    assert entry.options["exclude_label"] == "no_dboard"  # Rest bleibt erhalten
    assert _sensor(hass, "covers_open").state == "1"  # nach Neuladen mit neuer Einstellung


async def test_house_mode(hass: HomeAssistant) -> None:
    from pathlib import Path

    from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SERVICE_SELECT_OPTION

    from custom_components.unser_zuhause.select import UzHouseModeSelect

    path = Path(hass.config.path(DOMAIN, "hausmodus.txt"))
    path.unlink(missing_ok=True)  # Test-Konfigordner bleibt zwischen Läufen bestehen
    await _setup(hass)
    assert path.exists()  # Datei mit Standardwerten angelegt
    state = _sensor(hass, "house_mode", "select")
    assert state.attributes["options"] == ["anwesend", "abwesend"]
    assert state.state == "anwesend"

    await hass.services.async_call(
        SELECT_DOMAIN, SERVICE_SELECT_OPTION, {"entity_id": state.entity_id, "option": "abwesend"}, blocking=True
    )
    assert _sensor(hass, "house_mode", "select").state == "abwesend"

    # Eigene Modi über die Textdatei (Kommentare und Leerzeilen werden ignoriert)
    await hass.async_add_executor_job(
        path.write_text, "# Kommentar\nanwesend\n\nUrlaub\nanwesend\n", "utf-8"
    )
    entity = next(
        e for e in hass.data["entity_components"]["select"].entities if isinstance(e, UzHouseModeSelect)
    )
    entity._mtime = -1  # wie nach Ablauf des 30-Sekunden-Takts
    await entity._async_check_file()
    state = _sensor(hass, "house_mode", "select")
    assert state.attributes["options"] == ["anwesend", "Urlaub"]
    assert state.state == "anwesend"  # "abwesend" gibt es nicht mehr → erster Modus
    path.unlink(missing_ok=True)

    # Übersetzungen Deutsch/Englisch für die mitgelieferten Modi
    import json

    base = Path(__file__).parent.parent / "custom_components" / DOMAIN / "translations"
    de = json.loads((base / "de.json").read_text(encoding="utf-8"))
    en = json.loads((base / "en.json").read_text(encoding="utf-8"))
    assert de["entity"]["select"]["house_mode"]["state"] == {"anwesend": "Anwesend", "abwesend": "Abwesend"}
    assert en["entity"]["select"]["house_mode"]["state"] == {"anwesend": "Home", "abwesend": "Away"}


async def test_translations_complete() -> None:
    """Deutsch und Englisch haben dieselben Schlüssel wie strings.json."""
    import json
    from pathlib import Path

    root = Path(__file__).parent.parent / "custom_components" / DOMAIN

    def keys(node, prefix=""):
        if isinstance(node, dict):
            return set().union(*(keys(v, f"{prefix}{k}.") for k, v in node.items())) if node else set()
        return {prefix}

    base = keys(json.loads((root / "strings.json").read_text(encoding="utf-8")))
    for lang in ("de", "en"):
        assert keys(json.loads((root / "translations" / f"{lang}.json").read_text(encoding="utf-8"))) == base, lang


async def test_notify_persons(hass: HomeAssistant) -> None:
    """Push an Personen: Handys über den angemeldeten Benutzer, sonst über die Tracker der Person."""
    from homeassistant.helpers import device_registry as dr

    from pytest_homeassistant_custom_component.common import async_mock_service

    await _setup(hass)
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    phones = {}
    for key, name, user in (("a", "iPhone Anna", "user_a"), ("b", "Pixel Ben", "user_b"), ("c", "Gast-Handy", None)):
        entry = MockConfigEntry(domain="mobile_app", entry_id=f"app_{key}", title=name,
                                data={"device_name": name, "user_id": user})
        entry.add_to_hass(hass)
        dev = dev_reg.async_get_or_create(config_entry_id=entry.entry_id, identifiers={("mobile_app", key)}, name=name)
        ent_reg.async_get_or_create("device_tracker", "mobile_app", key, suggested_object_id=f"phone_{key}",
                                    config_entry=entry, device_id=dev.id)
        phones[key] = async_mock_service(hass, "notify", f"mobile_app_{name.lower().replace(' ', '_').replace('-', '_')}")
    hass.states.async_set("person.anna", "home", {"user_id": "user_a"})
    hass.states.async_set("person.gast", "home", {"device_trackers": ["device_tracker.phone_c"]})

    async def send(**data):
        return await hass.services.async_call(DOMAIN, "notify", data, blocking=True, return_response=True)

    res = await send(message="Hallo", title="Test", persons=["person.anna"])
    assert res == {"sent_to": ["notify.mobile_app_iphone_anna"]}
    assert phones["a"][0].data == {"message": "Hallo", "title": "Test"}
    assert not phones["b"] and not phones["c"]

    # Person ohne Benutzer → über ihren Tracker
    res = await send(message="Hi", persons=["person.gast"])
    assert res == {"sent_to": ["notify.mobile_app_gast_handy"]}

    # Ohne Personen: alle Handys mit angemeldetem Benutzer
    res = await send(message="An alle", data={"push": {"sound": "default"}})
    assert res == {"sent_to": ["notify.mobile_app_iphone_anna", "notify.mobile_app_pixel_ben"]}
    assert phones["b"][0].data["data"] == {"push": {"sound": "default"}}

    # Unbekannte Person: keine Nachricht, kein Fehler
    assert await send(message="x", persons=["person.niemand"]) == {"sent_to": []}


async def test_report_sensor(hass: HomeAssistant) -> None:
    """Bericht eines Agenten landet im Sensor (Zeitpunkt + Titel/Text) und bleibt nach Neustart erhalten."""
    await _setup(hass)
    state = _sensor(hass, "energy_coach")
    assert state.state == "unknown"
    await hass.services.async_call(
        DOMAIN, "set_report", {"report": "energy_coach", "title": "⚡ Woche", "message": "Alles gut."}, blocking=True
    )
    await hass.async_block_till_done()
    state = _sensor(hass, "energy_coach")
    assert state.attributes["title"] == "⚡ Woche"
    assert state.attributes["message"] == "Alles gut."
    assert state.state not in ("unknown", "unavailable")
