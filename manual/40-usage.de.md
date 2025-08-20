--- 
title: Anwendungsleitfaden
---
# Anwendungsleitfaden

Dieser Abschnitt behandelt die praktische Anwendung des `sw-build`-Befehls, seiner Optionen und Hauptfunktionen.

## Grundlegender Build-Prozess

Die einfachste Art, das Tool zu verwenden, besteht darin, in das Hauptverzeichnis des zu paketierenden Shopware 6 Plugins zu navigieren und den Befehl ohne Argumente auszuführen.

```bash
cd /pfad/zu/ihrem/plugin
sw-build
```

Dies löst den folgenden Prozess aus:
1.  Prüfung auf uncommittete Git-Änderungen und Abfrage, ob diese gestaged werden sollen.
2.  Überprüfung, ob kompilierte JS/CSS-Assets auf dem neuesten Stand sind.
3.  Lesen der `composer.json`, um den Plugin-Namen und die aktuelle Version zu erhalten.
4.  Anzeige einer interaktiven Abfrage zur Auswahl einer Versionserhöhung (Major, Minor, Patch oder Keine).
5.  Wenn eine Versionserhöhung ausgewählt wird, wird die `composer.json` aktualisiert, die Änderung committet, ein Git-Tag erstellt und beides zum Remote gepusht.
6.  Kopieren aller notwendigen Plugin-Dateien in ein temporäres Verzeichnis, wobei in `.sw-zip-blacklist` und `.gitignore` spezifizierte Dateien ausgeschlossen werden.
7.  Erstellen einer `release_info.txt`-Datei innerhalb des Pakets.
8.  Erstellen des finalen ZIP-Archivs im in Ihrer `.env`-Datei definierten `RELEASE_DIR`.
9.  Ausführung optionaler Schritte nach dem Build wie das Veröffentlichen von Handbüchern, Remote-Sync und Slack-Benachrichtigungen, falls konfiguriert.

## Kommandozeilenoptionen

Der Build-Prozess kann mit den folgenden Optionen angepasst werden:

| Option                 | Beschreibung                                                                                                |
|------------------------|-------------------------------------------------------------------------------------------------------------|
| `--output-dir <pfad>`  | Überschreibt das `RELEASE_DIR` aus Ihrer `.env`-Datei und speichert das Paket im angegebenen Pfad.            |
| `--source-dir <pfad>`  | Gibt das Quellverzeichnis des Plugins an. Standard ist das aktuelle Verzeichnis (`.`).                        |
| `--no-sync`            | Deaktiviert die Synchronisierung des Pakets zum Remote-Server, auch wenn rsync in `.env` konfiguriert ist.    |
| `-s`, `--notify-slack` | Sendet nach einem erfolgreichen Build und Sync eine Benachrichtigung an den konfigurierten Slack-Kanal.       |
| `--version-increment`  | Überspringt die interaktive Versionsabfrage. Muss einer der Werte `none`, `patch`, `minor`, `major` sein.      |
| `--variant-prefix <str>`| Erstellt eine umbenannte Variante des Plugins mit dem angegebenen Präfix (z. B. "Free").                      |
| `--variant-suffix <str>`| Erstellt eine umbenannte Variante des Plugins mit dem angegebenen Suffix (z. B. "Pro").                       |
| `--with-foundation`    | Erzwingt die Injektion von `TopdataFoundationSW6`-Code, unabhängig von der `composer.json`-Abhängigkeit.     |
| `-v`, `--verbose`      | Aktiviert eine detaillierte, schrittweise Ausgabe des Build-Prozesses zum Debuggen.                           |
| `--debug`              | Aktiviert zusätzliche Debug-Ausgaben, insbesondere für die Zeitstempel-Überprüfung kompilierter Assets.      |

### Beispiel

Um eine Patch-Version eines Plugins zu erstellen, eine "Free"-Variante zu erzeugen und Slack zu benachrichtigen, ohne interaktive Abfragen:

```bash
sw-build --version-increment patch --variant-prefix Free --notify-slack
```

## Hauptfunktionen im Detail

### Dateiausschluss

Das Tool schließt automatisch Dateien aus, die nicht für ein Produktions-Release vorgesehen sind. Die Ausschlussregeln stammen aus:
1.  Einer fest kodierten Liste gängiger Entwicklungsmuster (z. B. `.git`, `node_modules`, `tests`).
2.  Einer `.sw-zip-blacklist`-Datei im Hauptverzeichnis Ihres Plugins. Jede Zeile in dieser Datei wird als Ausschlussmuster behandelt. Kommentare können mit `#` hinzugefügt werden.
3.  Allen `.gitignore`-Dateien, die in der Verzeichnisstruktur des Plugins gefunden werden.

### Foundation Plugin Injection

Wenn Ihr Plugin von `topdata/topdata-foundation-sw6` abhängt, kann dieses Tool den erforderlichen Foundation-Code automatisch direkt in das ZIP-Paket Ihres Plugins einbetten. Dies macht Ihr Plugin eigenständig und vereinfacht die Installation für den Endbenutzer.

- **Automatischer Modus:** Das Tool prüft die `composer.json` Ihres Plugins. Wenn es die Foundation-Abhängigkeit findet, wird die Injektion automatisch aktiviert.
- **Manueller Modus:** Sie können die Injektion mit dem `--with-foundation`-Flag erzwingen.

Damit diese Funktion funktioniert, muss die Variable `FOUNDATION_PLUGIN_PATH` in Ihrer `.env`-Datei korrekt gesetzt sein.

### Erstellung umbenannter Varianten

Diese leistungsstarke Funktion ermöglicht es Ihnen, mit einem einzigen Build-Befehl eine zweite, umbenannte Version Ihres Plugins zu generieren. Sie ist ideal für die Erstellung von "Free"- oder "Pro"-Editionen eines Plugins.

Bei Verwendung von `--variant-prefix` oder `--variant-suffix` führt das Tool eine tiefgreifende Transformation durch:
- Es erstellt einen neuen Plugin-Namen (z. B. wird `MyPlugin` mit dem Präfix `Free` zu `FreeMyPlugin`).
- Es schreibt den PHP-Namespace um (z. B. wird `Topdata\MyPlugin` zu `Topdata\FreeMyPlugin`).
- Es aktualisiert den FQCN (Fully Qualified Class Name) des Plugins.
- Es modifiziert Labels und Beschreibungen in der `composer.json`, um die Variantenmarkierung hinzuzufügen (z. B. `[FREE] Mein Plugin`).
- Es benennt die Haupt-PHP-Datei des Plugins um.
- Es führt eine globale Suche und Ersetzung für den alten Namen und Namespace in allen PHP-, XML-, Twig- und JS-Dateien durch.

Das Original-Plugin wird immer zusammen mit der Variante erstellt. Beide ZIP-Dateien werden im Release-Verzeichnis abgelegt.
