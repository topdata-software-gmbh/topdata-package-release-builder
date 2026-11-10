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
6.  Kopieren aller notwendigen Plugin-Dateien in ein temporäres Verzeichnis, wobei die eingebauten Entwicklungsmuster und alles aus `.sw-zip-blacklist` ausgeschlossen werden.
7.  Erstellen einer `release_info.txt`-Datei innerhalb des Pakets.
8.  Erstellen des finalen ZIP-Archivs im in Ihrer `.env`-Datei definierten `RELEASE_DIR`.
9.  Ausführung optionaler Schritte nach dem Build wie das Veröffentlichen von Handbüchern, Remote-Sync und Slack-Benachrichtigungen, falls konfiguriert.

## Kommandozeilenoptionen

Der Build-Prozess kann mit den folgenden Optionen angepasst werden:

| Option                 | Beschreibung                                                                                                |
|------------------------|-------------------------------------------------------------------------------------------------------------|
| `--output-dir <pfad>`  | Überschreibt das `RELEASE_DIR` aus Ihrer `.env`-Datei und speichert das Paket im angegebenen Pfad.            |
| `--source-dir <pfad>`  | Gibt das Quellverzeichnis des Plugins an. Standard ist das aktuelle Verzeichnis (`.`).                        |
| `--no-sync`            | Deaktiviert die Synchronisierung des Pakets zum Remote-Server, auch wenn rsync in `.env` konfiguriert ist. Unterdrückt **nicht** die Free-Branch-Veröffentlichung. |
| `--skip-free`          | Deaktiviert die gesamte Free-Branch-Arbeit, auch wenn `.topdata/build.yaml` sie aktiviert. Gibt eine Warnung aus. |
| `-s`, `--notify-slack` | Sendet nach einem erfolgreichen Build und Sync eine Benachrichtigung an den konfigurierten Slack-Kanal.       |
| `--version-increment`  | Überspringt die interaktive Versionsabfrage. Muss einer der Werte `none`, `patch`, `minor`, `major` sein.      |
| `--variant-prefix <str>`| Erstellt eine umbenannte Variante des Plugins mit dem angegebenen Präfix (z. B. "Free").                      |
| `--variant-suffix <str>`| Erstellt eine umbenannte Variante des Plugins mit dem angegebenen Suffix (z. B. "Pro").                       |
| `--with-foundation`    | Erzwingt die Injektion von `TopdataFoundationSW6`-Code, unabhängig von der `composer.json`-Abhängigkeit.     |
| `-v`, `--verbose`      | Aktiviert eine detaillierte, schrittweise Ausgabe des Build-Prozesses zum Debuggen.                           |
| `--require-compiled-assets` | Bricht den Build ab, wenn ein Asset-Target Quellen, aber kein kompiliertes Ergebnis hat. Standardmäßig aus, da die meisten Topdata-Plugins handgeschriebenes Twig/CSS ohne Build-Schritt ausliefern. |
| `--rebaseline-assets`    | Verwirft die gespeicherte Asset-Basislinie und übernimmt die aktuelle ohne Vergleich. Ausstieg für Quelländerungen, die legitim byte-identische Ausgabe erzeugen. |
| `--debug`              | Aktiviert zusätzliche Debug-Ausgaben, insbesondere für die Asset-Überprüfung (gibt die Inhalts-Hashes jeder Entscheidung aus). |

### Beispiel

Um eine Patch-Version eines Plugins zu erstellen, eine "Free"-Variante zu erzeugen und Slack zu benachrichtigen, ohne interaktive Abfragen:

```bash
sw-build --version-increment patch --variant-prefix Free --notify-slack
```

### Free-Branch-Veröffentlichung

Enthält das Plugin-Repository eine committete `.topdata/build.yaml` mit einem `free`-Mapping,
veröffentlicht jeder Build zusätzlich die Variante `Free<PluginName>` auf dem Remote-Branch
`origin/main-free` (oder `free.branch`):

1. Der Payload wird in einem temporären Verzeichnis erzeugt und mit `Free` umbenannt; die
   Foundation-Injektion wird genau wie beim bezahlten Build angewendet.
2. Der erste Build erzeugt einen Commits ohne Vorgänger. Jeder weitere Build hängt genau einen
   Commit an die zuletzt veröffentlichte Spitze an — `git pull` im Shop reicht, ein Reset ist
   nie nötig. Es wird nie erzwungen gepusht und nie Historie umgeschrieben.
3. Ein Build ohne Inhaltsänderung (auch wenn sich nur der `Created`-Zeitstempel in
   `release_info.txt` ändert) erzeugt keinen Commit.
4. Der Arbeitsbaum muss sauber sein. Bei uncommitteten Änderungen bricht der Build ab, bevor
   Uploads oder Benachrichtigungen stattfinden.
5. `zip: true` erzeugt zusätzlich ein Free-ZIP und nutzt den normalen Upload-/Slack-Pfad;
   `--no-sync` hält das ZIP lokal, veröffentlicht aber weiterhin den Branch.

`--skip-free` ist der einzige Weg, die Free-Arbeit zu überspringen; der bezahlte Release läuft
weiter und es wird eine Warnung ausgegeben.

### Free-Flag verwalten

Das Manifest muss nicht von Hand geschrieben werden. Die folgenden Befehle bearbeiten
`.topdata/build.yaml` im Plugin-Verzeichnis, ohne einen Build, Commit oder Push auszulösen:

```bash
sw-build free enable [--branch main-free] [--zip]
sw-build free disable
sw-build free status
```

- `enable` legt die Datei mit `free: {}` an (bzw. ergänzt den `free`-Schlüssel) und behält
  andere Schlüssel bei. `--branch` wird vor dem Schreiben validiert, `--zip`/`--no-zip`
  setzt die ZIP-Option.
- `disable` entfernt den `free`-Schlüssel und löscht die Datei samt leerem `.topdata/`, wenn
  nichts anderes übrig bleibt.
- `status` zeigt an, ob die Funktion aktiv ist, welcher Branch verwendet wird und ob ein ZIP
  erzeugt wird.

Die Änderung an der committeten Datei muss anschließend selbst committet werden.

### Selbst-Upgrade

`sw-build` kann seine eigene Installation aktualisieren, indem es den konfigurierten
Git-Remote pullt und das Paket erneut editierbar installiert:

```bash
sw-build self-upgrade          # läuft bei unsauberem Arbeitsbaum nicht
sw-build self-upgrade --force  # stasht vorher lokale Änderungen (inkl. untracked)
```

- Funktioniert nur bei einer Git-Installation des Release Builders. Ein fertiges Wheel hat
  keinen Upstream zum Pullen.
- Bei lokalen Änderungen bricht der Befehl ab, bevor etwas verändert wird. `--force` führt
  `git stash push --include-untracked` mit der Nachricht `sw-build self-upgrade` aus.
- Bringt der Pull neue Commits, werden die Abhängigkeiten in der Umgebung des laufenden
  `sw-build` (dem `.venv`-Launcher aus `scripts/install.sh`) mit `uv pip install --python
  <interpreter> -e .` neu installiert; ohne `uv` wird `pip` dieses Interpreters verwendet.
- Ist die Installation bereits aktuell, endet der Befehl erfolgreich, ohne etwas neu zu
  installieren.
- Starten Sie Ihren Befehl nach dem Upgrade erneut, damit der neue Code geladen wird.

## Hauptfunktionen im Detail

### Dateiausschluss

Das Tool schließt automatisch Dateien aus, die nicht für ein Produktions-Release vorgesehen sind. Die Ausschlussregeln stammen aus:
1.  Einer fest kodierten Liste gängiger Entwicklungsmuster (z. B. `.git`, `node_modules`, `tests`).
2.  Einer `.sw-zip-blacklist`-Datei im Hauptverzeichnis Ihres Plugins. Jede Zeile in dieser Datei wird als Ausschlussmuster behandelt. Kommentare können mit `#` hinzugefügt werden.

> **Hinweis:** `.gitignore`-Dateien werden **nicht** ausgewertet. Kompilierte Dateien unter `src/Resources/public/` sind normalerweise gitignored, und `.gitignore` zu befolgen würde genau diese Dateien aus dem Paket entfernen. Nutzen Sie `.sw-zip-blacklist`, um weitere Pfade auszuschließen.

### Asset-Überprüfung

Kompilierte Assets werden über **SHA-256-Inhalts-Hashes** geprüft, nicht über Dateizeitstempel. Clone, Pull und rsync schreiben die Änderungszeiten neu, ein Zeitstempelvergleich liefert also gerade für die Checkouts, die nie von Hand kompiliert wurden, eine willkürliche Antwort.

Geprüft werden drei Asset-Targets, jeweils Source-Verzeichnis und erwartete Ausgabe:

| Target | Quellen | Kompilierte Ausgabe |
|---|---|---|
| Administration JS | `src/Resources/app/administration/src` (`*.ts`, `*.js`) | `src/Resources/public/administration/js` |
| Storefront JS | `src/Resources/app/storefront/src` (`*.ts`, `*.js`) | `src/Resources/public/storefront/js` |
| Storefront CSS | `src/Resources/app/storefront/src` (`*.scss`, `*.css`) | `src/Resources/public/storefront/css` |

Ein Target mit Quellen, aber **ohne** kompilierte Ausgabe ist:

- ein **Fehler**, wenn ein anderes Target *desselben* Plugins kompiliert hat (wer kompiliert, muss alle Seiten kompilieren, für die Quellen existieren), oder wenn `--require-compiled-assets` gesetzt ist;
- andernfalls eine **Warnung** — die meisten Topdata-Plugins haben handgeschriebene `.js`/`.scss` unter `Resources/app` und gar keinen Build-Schritt; deren Release zu blockieren wäre falsch.

Sobald ein Target Quellen *und* Ausgabe hat, werden beide Hashes mit der Basislinie verglichen:

| Quellen | Ausgabe | Ergebnis |
|---|---|---|
| geändert | unverändert | **Fehler** — die Ausgabe kann kein Produkt dieser Quellen sein. Neu kompilieren. |
| geändert | geändert | Basislinie wird fortgeschrieben. Sie haben neu gebaut, das ist ein normales Release. |
| unverändert | geändert | Warnung — kompilierte Ausgabe hat sich ohne Quelländerung bewegt. |
| unverändert | unverändert | Geprüft. |

Der Ausgabe-Hash macht das entscheidbar: ein Neubau muss die Ausgabe bewegen. Prüft man nur, ob sich die Quellen geändert haben, lehnt man damit auch einen *korrekten* Neubau ab — und da die Basislinie nie über einen Fehler hinweg fortgeschrieben wird, wäre der Checkout danach nie wieder releasable. Erzeugt ein Neubau wirklich byte-identische Ausgabe (etwa eine reine Kommentaränderung), setzen Sie mit `--rebaseline-assets` bewusst eine neue Basislinie.

Nach einer **erfolgreichen** Prüfung werden die Quell- und Ausgabe-Hashes in `.git/sw-build/<plugin>/.sw-build-assets.json` festgehalten. Dieses Manifest ist **lokaler Zustand**: Es liegt im Git-Verzeichnis, erreicht also nie das Release-ZIP, wird von `git status` nie gesehen und kann nicht mit dem Checkout eines anderen Entwicklers kollidieren. Der erste Build in einem frischen Checkout legt eine Basislinie an; jeder spätere Build in demselben Checkout wird dagegen geprüft, und eine Änderung an einer Asset-Quelle ohne erneutes Kompilieren bricht den Release ab. Eine **fehlgeschlagene** Prüfung lässt die vorherige Basislinie unverändert, damit ein ignorierter Fehler niemals veraltete Ausgaben freigibt.

Der in `release_info.txt` geschriebene und mitgelieferte Datensatz enthält ebenfalls den Asset-Status, die erkannte Node-Version und den Lockfile-Digest.

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
