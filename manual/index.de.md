--- 
title: Einleitung
---
# Einleitung

Willkommen zum Benutzerhandbuch für den Topdata Package Release Builder.

Dieses Tool, aufgerufen über den Befehl `sw-build`, wurde entwickelt, um den Prozess der Paketierung eines Shopware 6 Plugins für die Veröffentlichung vollständig zu automatisieren. Es nimmt ein Quellverzeichnis, schließt entwicklungsrelevante Dateien intelligent aus, kümmert sich um die Versionserhöhung und erzeugt ein sauberes, veröffentlichungsbereites ZIP-Archiv.

Über die grundlegende Paketierung hinaus bietet es leistungsstarke Funktionen, um Ihren gesamten Release-Workflow zu optimieren, darunter:
*   Automatische Injektion der `TopdataFoundationSW6`-Abhängigkeit.
*   Erstellung umbenannter Plugin-Varianten (z. B. für kostenlose oder Pro-Versionen).
*   Deployment auf einen Remote-Server via `rsync`.
*   Benachrichtigungen an einen Slack-Kanal.
*   Veröffentlichung von Benutzerhandbüchern in einem dedizierten Git-Repository.

Diese Anleitung führt Sie durch die Installation, Konfiguration und Nutzung all seiner Funktionen.
