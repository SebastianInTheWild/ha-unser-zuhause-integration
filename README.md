# Unser Zuhause – Integration

Legt die Sammelsensoren für das Dashboard „Unser Zuhause“ an. Die Dashboard-Strategy nutzt sie automatisch für die Status-Kacheln. Deshalb gehört diese Integration **vor** der Strategy installiert.

| Sensor | Inhalt |
|---|---|
| Lichter an | Anzahl eingeschalteter Lichter (Lichtgruppen zählen nicht doppelt) |
| Offene Rollos | Anzahl offener Rollos, Jalousien, Markisen … |
| Fenster & Türen | An, sobald ein Fenster oder eine Tür offen ist |
| Offene Fenster & Türen | Anzahl offener Fenster und Türen |
| Personen zu Hause | Anzahl anwesender Personen |
| Hausmodus | Auswahl, standardmäßig Anwesend und Abwesend (Werte aus einer Textdatei) |

Die Zähler und „Fenster & Türen“ führen im Attribut `entity_id` die gezählten Entitäten.

Nicht mitgezählt werden:

- ausgeblendete oder deaktivierte Entitäten
- Diagnose- und Konfigurations-Entitäten
- Entitäten oder Geräte mit dem Ausschluss-Label (Standard `no_dboard`)
- einzeln ausgeschlossene Entitäten

## Hausmodus

Die Modi stehen in `/config/unser_zuhause/hausmodus.txt`, ein Modus pro Zeile. Die Datei wird beim ersten Start angelegt. Änderungen übernimmt die Integration nach spätestens 30 Sekunden, ein Neustart ist nicht nötig. Zeilen mit `#` sind Kommentare.

```text
anwesend
abwesend
Urlaub
```

`anwesend` und `abwesend` werden je nach Sprache des Benutzers übersetzt: Deutsch „Anwesend/Abwesend“, Englisch „Home/Away“. Eigene Modi erscheinen genau so, wie sie in der Datei stehen. Der gewählte Modus bleibt über Neustarts erhalten. Fällt er aus der Datei heraus, gilt der erste Modus.

Die Datei bearbeitest du zum Beispiel mit dem File Editor oder Studio Code Server.

## Benachrichtigen

Die Aktion **Unser Zuhause: Benachrichtigen** (`unser_zuhause.notify`) schickt eine Push-Nachricht an Personen statt an einzelne Handys. Die Handys findet sie selbst: Jede Companion-App weiß, welcher Benutzer an ihr angemeldet ist, und die Person ist mit diesem Benutzer verknüpft. Bekommt jemand ein neues Handy, musst du keine Automation ändern.

```yaml
action: unser_zuhause.notify
data:
  persons:
    - person.sebastian
  title: Waschküche
  message: Die Waschmaschine ist fertig.
```

- `persons` leer lassen: Die Nachricht geht an alle Handys, an denen ein Benutzer angemeldet ist.
- Hat eine Person keinen Benutzer, nimmt die Aktion die Handys aus den Trackern der Person.
- `data` gibt Zusatzoptionen an die Companion-App weiter, zum Beispiel Ton, Priorität oder Aktionen.
- Die Antwort nennt die Dienste, an die gesendet wurde (`sent_to`).

## Sprachen

Die Integration ist auf Deutsch und Englisch übersetzt: Einrichtung, Einstellungen, Namen der Entitäten, die Standard-Modi und die Aktion „Benachrichtigen“. Welche Sprache erscheint, richtet sich nach dem Profil des jeweiligen Benutzers.

## Installation

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → URL dieses Repositories, Typ **Integration**
2. „Unser Zuhause“ herunterladen und Home Assistant neu starten
3. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Unser Zuhause“

## Einstellungen

Du kannst die Einstellungen an zwei Stellen ändern:

- in Home Assistant: Einstellungen → Geräte & Dienste → Unser Zuhause → **Konfigurieren**
- im Dashboard: Bearbeiten → Module & Pop-ups → **Unser Zuhause**

Einstellbar sind:

- das Ausschluss-Label
- einzelne Entitäten, die nicht mitzählen
- welche Rollo-Arten mitzählen (Standard: alles außer Garagentor, Tor, Tür, Klappe)
- welche Kontakt-Arten als Fenster oder Tür zählen (Standard: Fenster, Tür, Garagentor; die allgemeine Klasse „Öffnung“ nur bei Bedarf, z. B. melden Tankstellen-Sensoren „geöffnet“ damit)

## Lizenz

MIT · Autor: SebastianInTheWild
