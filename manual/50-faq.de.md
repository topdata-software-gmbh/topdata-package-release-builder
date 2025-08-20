--- 
title: FAQ
---
# Häufig gestellte Fragen

**F: Mein Build ist mit der Meldung "Error: Compiled files are outdated" fehlgeschlagen. Was soll ich tun?**

A: Dieser Fehler bedeutet, dass die Quelldateien Ihrer Plugin-Assets (wie `.js`, `.ts` oder `.scss` in `src/Resources/app/`) neuer sind als die kompilierten Ausgabedateien (in `src/Resources/public/`). Dies geschieht normalerweise, wenn Sie Änderungen am Quellcode vorgenommen, aber den Shopware-Build-Befehl nicht ausgeführt haben.

Um dies zu beheben, führen Sie den entsprechenden Build-Befehl aus Ihrem Shopware-Hauptverzeichnis aus und versuchen Sie den `sw-build`-Befehl erneut.
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
