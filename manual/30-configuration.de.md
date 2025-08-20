--- 
title: Konfiguration
---
# Konfiguration

Das `sw-build`-Tool wird über Umgebungsvariablen konfiguriert, die in einer `.env`-Datei im Hauptverzeichnis des Projekts definiert sind.

### Grundeinstellungen

| Variable      | Erforderlich | Beschreibung                                                                                                                                                                                            | Beispiel                                           |
|---------------|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------|
| `RELEASE_DIR` | **Ja**       | Der absolute Pfad zum lokalen Verzeichnis, in dem die finalen ZIP-Archive der Plugins gespeichert werden. Das Tool erstellt dieses Verzeichnis, falls es nicht existiert.                                    | `/home/user/shopware-releases`                     |
| `MANUALS_DIR` | Nein         | Der absolute Pfad zu einem lokalen Klon eines zentralen Git-Repositories für Handbücher. Wenn gesetzt, kopiert das Tool den `manual/`-Ordner des Plugins hierher, committet und pusht die Änderungen.        | `/home/user/development/sw6-plugin-manuals`        |

### Remote Sync (rsync)

Diese Einstellungen sind erforderlich, wenn Sie die automatische Remote-Sync-Funktion nutzen möchten.

| Variable                          | Erforderlich | Beschreibung                                                                                                                               | Beispiel                                             |
|-----------------------------------|--------------|--------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| `RSYNC_SSH_HOST`                  | Nein         | Der SSH-Host für den Remote-Server, einschließlich des Benutzernamens.                                                                     | `user@your-server.com`                               |
| `RSYNC_SSH_PORT`                  | Nein         | Der SSH-Port für den Remote-Server. Standard ist `22`.                                                                                     | `2222`                                               |
| `RSYNC_REMOTE_PATH_RELEASES_FOLDER` | Nein         | Der Basispfad auf dem Remote-Server, wo Plugin-Releases gespeichert werden sollen. Das Tool erstellt automatisch für jedes Plugin ein Unterverzeichnis. | `/var/www/releases/`                                 |

### Benachrichtigungen (Slack)

Diese Einstellungen werden zum Senden von Release-Benachrichtigungen verwendet.

| Variable            | Erforderlich | Beschreibung                                                                                                                            | Beispiel                                                           |
|---------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| `SLACK_WEBHOOK_URL` | Nein         | Die vollständige eingehende Webhook-URL, die von Slack bereitgestellt wird, um Nachrichten in einem bestimmten Kanal zu posten.           | `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX` |
| `DOWNLOAD_BASE_URL` | Nein         | Eine öffentliche Basis-URL, die verwendet wird, um einen Download-Link für die synchronisierte ZIP-Datei zu erstellen. Dieser Link wird zur Bequemlichkeit in die Slack-Benachrichtigung aufgenommen. | `https://downloads.example.com/plugins`                |

### Erweiterte Einstellungen

| Variable                      | Erforderlich | Beschreibung                                                                                                                                                                | Beispiel                                                   |
|-------------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| `FOUNDATION_PLUGIN_PATH`      | Nein         | Der absolute Pfad zu Ihrem lokalen Checkout des `topdata-foundation-sw6`-Plugins. Dies ist für die Foundation-Injection-Funktion erforderlich.                              | `/home/user/development/topdata-foundation-sw6`            |
| `DOCS_GENERATOR_PROJECT_PATH` | Nein         | Der absolute Pfad zu einem Dokumentationsgenerator-Projekt. Wenn gesetzt, wird nach einem Build eine hilfreiche Erinnerung zur Ausführung des Generators in der finalen Erfolgsmeldung angezeigt. | `/home/user/development/docs-generator`                    |
