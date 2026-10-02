--- 
title: FAQ
---
# Häufig gestellte Fragen

**F: Mein Build ist mit „Compiled assets are not release-ready" fehlgeschlagen. Was soll ich tun?**

A: `sw-build` vergleicht Ihre Asset-Quellen mit der kompilierten Ausgabe per **Inhalts-Hash**, nicht per Zeitstempel. Zwei Situationen lösen diesen Fehler aus:

1. *Ein Asset-Target hat Quellen, aber gar keine kompilierte Ausgabe* — und Ihr Plugin liefert an anderer Stelle bereits kompilierte Assets aus, es soll also kompilieren. Sie haben eine Quelle geändert ohne neu zu bauen.
2. *Die Quellen haben sich seit dem letzten geprüften Build in diesem Checkout geändert* — Sie haben eine Quelle editiert und seither nicht neu kompiliert.

Führen Sie in beiden Fällen Ihren Asset-Build aus und starten Sie `sw-build` erneut.

Wenn das bei einem Plugin ohne Build-Schritt auftritt, wurde mit `--require-compiled-assets` gebaut; lassen Sie das Flag für solche Plugins weg.

```bash
# Für Administration-Assets
./bin/build-administration.sh

# Für Storefront-Assets
./bin/build-storefront.sh
```

**F: Das Tool synchronisiert mein Paket nicht auf den Remote-Server. Warum?**

A: Dafür gibt es mehrere mögliche Gründe:
1.  **Konfiguration:** Stellen Sie sicher, dass `RSYNC_SSH_HOST` und `RSYNC_REMOTE_PATH_RELEASES_FOLDER` in Ihrer `.env`-Datei korrekt gesetzt sind.
2.  **`--no-sync`-Flag:** Überprüfen Sie, ob Sie den Befehl mit dem `--no-sync`-Flag ausführen, das den Upload explizit deaktiviert.
3.  **SSH-Zugriff:** Vergewissern Sie sich, dass Sie passwortlosen SSH-Zugriff (z. B. über SSH-Schlüssel) auf den konfigurierten Host haben. Das Tool unterstützt keine interaktiven Passwortabfragen.

**F: Wie kann ich steuern, welche Dateien in das ZIP-Archiv aufgenommen werden?**

A: Erstellen Sie eine Datei namens `.sw-zip-blacklist` im Hauptverzeichnis Ihres Plugins. Fügen Sie die Namen der Dateien oder Verzeichnisse, die Sie ausschließen möchten, zeilenweise hinzu. Sie können Platzhalter verwenden (z. B. `*.log`, `temp/*`).

**F: Warum muss ich `FOUNDATION_PLUGIN_PATH` setzen?**

A: Die Variable `FOUNDATION_PLUGIN_PATH` ist für die "Foundation Injection"-Funktion erforderlich. Wenn `sw-build` den Foundation-Code einbetten muss, muss es wissen, wo es die Quelldateien auf Ihrem lokalen Rechner finden kann. Dies sollte der Pfad zu Ihrem lokalen Klon des `topdata-foundation-sw6`-Repositories sein.

**F: Kann ich eine "Pro"-Version und eine "Free"-Version mit einem Befehl erstellen?**

A: Nicht in einer einzigen Befehlsausführung. Die Optionen `--variant-prefix` und `--variant-suffix` können zwar kombiniert werden, erzeugen aber nur eine Variante zusätzlich zum Originalpaket. Um zwei verschiedene Varianten zu erstellen, müssten Sie den Befehl zweimal mit unterschiedlichen Optionen ausführen:
```bash
# Zuerst die Free-Version erstellen
sw-build --variant-prefix Free

# Dann die Pro-Version erstellen
sw-build --variant-suffix Pro
```
