"""Konstanten der Integration Unser Zuhause."""

DOMAIN = "unser_zuhause"

CONF_EXCLUDE_LABEL = "exclude_label"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_COVER_CLASSES = "cover_classes"
CONF_OPENING_CLASSES = "opening_classes"

# Rollos ohne Geräteklasse zählen als "other"
COVER_CLASSES = ["shutter", "blind", "shade", "curtain", "awning", "window", "garage", "gate", "door", "damper", "other"]
OPENING_CLASSES = ["window", "door", "garage_door", "opening"]

DEFAULT_OPTIONS = {
    CONF_EXCLUDE_LABEL: "no_dboard",
    CONF_EXCLUDE_ENTITIES: [],
    CONF_COVER_CLASSES: ["shutter", "blind", "shade", "curtain", "awning", "window", "other"],
    # "opening" ist zu allgemein (z. B. Tankerkönig: Tankstelle geöffnet), daher nur auf Wunsch
    CONF_OPENING_CLASSES: ["window", "door", "garage_door"],
}

# Schlüssel der Sensoren (translation_key). Die Strategy findet die Sensoren darüber.
LIGHTS_ON = "lights_on"
COVERS_OPEN = "covers_open"
OPENINGS_OPEN = "openings_open"
OPENINGS_COUNT = "openings_count"
PERSONS_HOME = "persons_home"
HOUSE_MODE = "house_mode"

# Hausmodus: Werte stehen in <config>/unser_zuhause/hausmodus.txt (wird beim ersten Start angelegt)
HOUSE_MODES_FILE = "hausmodus.txt"
DEFAULT_HOUSE_MODES = ["anwesend", "abwesend"]

# Berichte von Agenten: je Bericht ein Sensor (translation_key), gefüllt über unser_zuhause.set_report
ENERGY_COACH = "energy_coach"
REPORTS = [ENERGY_COACH]
SERVICE_SET_REPORT = "set_report"

# Aktion unser_zuhause.notify: Push an Personen (Handys über den angemeldeten Benutzer)
SERVICE_NOTIFY = "notify"
