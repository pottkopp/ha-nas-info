# NAS-Info (Home Assistant Integration)

Meldet die Belegung aller beim **Supervisor** eingebundenen **Netzwerkspeicher**
(CIFS/SMB und NFS) als Sensoren.

Kein MQTT, kein Add-on, keine externen Pakete: die Integration spricht die
Supervisor-Schnittstelle direkt an (HTTP mit dem Supervisor-Token). Die
mitgelieferte Bibliothek `aiohasupervisor` bildet den Endpunkt für die
Mount-Belegung nämlich nicht ab.

## Voraussetzungen

- Home Assistant OS oder Home Assistant Supervised (nur dort gibt es den Supervisor)
- Home Assistant 2026.4.0 oder neuer
- Der Netzwerkspeicher muss beim Supervisor gemeldet sein (Einstellungen -> Systeme -> Speicher)

## Installation

**HACS**: HACS -> Einstellungen -> Custom repositories ->
`https://github.com/pottkopp/ha-nas-info`, Kategorie **Integration** -> NAS-Info
installieren -> Home Assistant **neu starten**.

**Manuell**: `custom_components/nas_info` nach
`/config/custom_components/nas_info` kopieren und neu starten.

## Einrichten

Einstellungen -> Gerate & Dienste -> Integration hinzufügen -> **NAS-Info**.
Es gibt genau einen Eintrag: er überwacht alle gemeldeten Netzwerkspeicher.

## Geräte

Der Supervisor legt pro Netzwerkspeicher bereits ein Gerät an (Name =
Mount-Name, mit einem Mount-Binärschalter). NAS-Info hängt seine Sensoren an
**genau dieses Gerät** an — es entsteht kein zweites Gerät mit demselben Namen.

## Sensoren pro Speicher

Gesamt, Belegt, Frei, Auslastung (%), Status, Server, Freigabe,
Schreibgeschützt, Zuletzt geprüft. Beispiel-Entität:
`sensor.speicherpott_belegt`.

## Optionen (Integration -> NAS-Info -> Optionen)

| Option | Standard | Wirkung |
| --- | --- | --- |
| Aktualisierungsintervall | 300 s | 30–86400 s |
| Diese Speicher ignorieren | leer | Namen ohne Sensoren |
| Anzeige der Speichermengen | Automatisch | `auto`, `Immer GB`, `Rohwerte in Bytes` |

Änderungen wirken ohne Neustart.

### Die 0,5-Regel

Bei `Automatisch` wechselt die Einheit nach unten, wenn der Wert unter 0,5 einer
Einheit fällt: 400 MB zeigt `400 MB` (nicht `0,4 GB`), 513 MB zeigt `0,5 GB`.
Der Zustand ist dabei Text mit zugehöriger Einheit und kann nicht in
Langzeitstatistik (Mittelwert/Summe) benutzt werden — dafür `Rohwerte in Bytes`
oder `Immer GB` wählen.

## Fehlerbilder

- **„Der Supervisor meldet keine Netzwerkspeicher"**: es existiert kein CIFS/NFS-Mount.
- **„Der Supervisor ist nicht erreichbar"**: Supervisor-Antwort fehlgeschlagen, Details
  im Core-Log.
- **Gesamt/Belegt/Frei ohne Wert**: `host/disks/<name>/usage` liefert nichts (z. B.
  Server offline); im Core-Log steht eine Warnung mit dem Mount-Namen. Die
  Messung des Supervisors wartet im Zweifel bis zu 60 s auf den Dateisystem-Probe.
- **Integration nicht in der Liste**: Core neu starten, nicht nur HACS aktualisieren.

## deinstallieren

Eintrag entfernen — die NAS-Info-Entitäten verschwinden, das Mount-Gerät des
Supervisors bleibt erhalten.
