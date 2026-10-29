# NAS-Info (Home Assistant Integration)

Meldet die Belegung aller beim **Supervisor** eingebundenen **Netzwerkspeicher**
(CIFS/SMB und NFS) als Sensoren — pro Speicher ein eigenes Geraet mit dem Namen
des Speichers.

Kein MQTT, kein Add-on, keine externen Pakete: die Integration fragt den
Supervisor direkt ab (`aiohasupervisor`, das Home Assistant bereits mitbringt).

## Voraussetzungen

- Home Assistant OS oder Home Assistant Supervised (nur dort gibt es den Supervisor)
- Home Assistant **2026.4.0** oder neuer
- Minutensensorik: der Supervisor muss die Netzwerkspeicher melden (Einstellungen -> Systeme -> Speicher)

## Installation

**Empfohlen: HACS**
1. HACS -> Einstellungen -> Custom repositories -> `https://github.com/pottkopp/ha-nas-info`, Kategorie **Integration**.
2. NAS-Info installieren.
3. Home Assistant neu starten (nicht nur Core neu laden).

**Manuell**
`custom_components/nas_info` nach `/config/custom_components/nas_info` kopieren
und Home Assistant neu starten.

## Einrichten

Einstellungen -> Gerate & Dienste -> Integration hinzufügen -> **NAS-Info**.
Es gibt genau einen Eintrag: er ueberwacht alle gemeldeten Netzwerkspeicher.

## Optionen (Integration -> NAS-Info -> Optionen)

| Option | Standard | Wirkung |
| --- | --- | --- |
| Aktualisierungsintervall | 300 s | Abfrageintervall, 30–86400 s |
| Diese Speicher ignorieren | leer | Namen, die keine Sensoren bekommen |
| Anzeige der Speichermengen | Automatisch | `auto`, `Immer GB`, `Rohwerte in Bytes` |

Aenderungen wirken **ohne Neustart**.

## Sensoren pro Speicher

Gesamt, Belegt, Frei, Auslastung (%), Status, Server, Freigabe,
Schreibgeschuetzt, Zuletzt geprueft. Beispiel-Geraetename: `Speicherpott`,
Beispiel-Entitaet: `sensor.speicherpott_belegt`.

### Die 0,5-Regel

Bei `Automatisch` wechselt die Einheit nach unten, wenn der Wert unter 0,5 einer
Einheit faellt: 400 MB zeigt `400 MB` (nicht `0,4 GB`), 513 MB zeigt `0,5 GB`.
Dafuer ist der Zustand ein Text mit zugehoeriger Einheit — er kann nicht in
Langzeitstatistiken (Mittelwert/Summe) verwendet werden. Fuer Statistik `Rohwerte
in Bytes` oder `Immer GB` waehlen.

## Bekannte Grenzen

- Ein ignorierter oder entfernter Speicher hoert auf zu liefern; das Geraet bleibt
  bis zum Entfernen des Eintrags oder per Mülleimer-Symbol am Geraet bestehen.
- Kapazitaetsdaten kommen von `host/disks/<name>/usage`. Meldet der Supervisor hier
  nichts, bleiben Gesamt/Belegt/Frei ohne Wert, und im Core-Log steht eine Warnung
  mit dem Mount-Namen.

## deinstallieren

Eintrag der Integration entfernen — alle NAS-Info-Geraete und -Entitaeten werden
mit entfernt.
