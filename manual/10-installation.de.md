--- 
title: Installation
---
# Installationsanleitung

Befolgen Sie diese Schritte, um das `sw-build`-Tool auf Ihrem lokalen Entwicklungsrechner zu installieren.

## Voraussetzungen

- Python 3.8 oder neuer.
- `git` muss installiert und im PATH Ihres Systems verfügbar sein.
- `uv` (empfohlen) oder `pip` zur Verwaltung von Python-Paketen.
- `rsync` (erforderlich für die Remote-Sync-Funktion).
- (Optional) `pandoc` mit einer LaTeX-Engine wie `xelatex`, falls Sie das beiliegende `pdf.py`-Skript zur Erstellung von PDF-Handbüchern verwenden möchten.

## Schritt 1: Repository klonen

Klonen Sie zunächst das Projekt aus seinem Git-Repository an einen Ort auf Ihrem Rechner.

```bash
git clone git@github.com:topdata-software-gmbh/topdata-package-release-builder.git
cd topdata-package-release-builder
```

## Schritt 2: Virtuelle Umgebung einrichten

Es wird dringend empfohlen, eine virtuelle Umgebung zu verwenden, um die Abhängigkeiten des Tools zu isolieren.

```bash
# Die virtuelle Umgebung erstellen
uv venv

# Die virtuelle Umgebung aktivieren
source .venv/bin/activate
```
Sie müssen die Umgebung in jeder neuen Terminalsitzung aktivieren, bevor Sie den `sw-build`-Befehl verwenden.

## Schritt 3: Abhängigkeiten installieren

Installieren Sie die erforderlichen Python-Pakete mit `uv`. Der `-e`-Flag installiert das Projekt im "editierbaren" Modus, was für die Entwicklung praktisch ist.

```bash
uv pip install -e .
```

## Schritt 4: Konfigurationsdatei erstellen

Das Tool wird über eine `.env`-Datei im Hauptverzeichnis des Projekts konfiguriert. Kopieren Sie die Beispieldatei, um Ihre eigene lokale Konfiguration zu erstellen.

```bash
cp .env.example .env
```
Öffnen Sie nun die `.env`-Datei in einem Texteditor. **Sie müssen mindestens die Variable `RELEASE_DIR` setzen.** Dies ist das Verzeichnis, in dem alle erstellten Plugin-Pakete gespeichert werden.

Weitere Details zu allen verfügbaren Einstellungen finden Sie im Kapitel [Konfiguration](./30-configuration.de.md).

## Schritt 5: Installation überprüfen

Sie können überprüfen, ob das Tool korrekt installiert wurde, indem Sie den Hilfe-Befehl ausführen:

```bash
sw-build --help
```

Wenn die Installation erfolgreich war, sehen Sie eine Liste aller verfügbaren Befehle und Optionen. Sie sind nun bereit, das Tool zu verwenden.
