--- 
title: Introduction
---
# Introduction

Welcome to the user manual for the Topdata Package Release Builder.

This tool, invoked via the `sw-build` command, is designed to completely automate the process of packaging a Shopware 6 plugin for release. It takes a source directory, intelligently excludes development-related files, handles version bumping, and produces a clean, release-ready ZIP archive.

Beyond basic packaging, it offers powerful features to streamline your entire release workflow, including:
*   Automatic injection of the `TopdataFoundationSW6` dependency.
*   Creation of renamed plugin variants (e.g., for free or pro versions).
*   Deployment to a remote server via `rsync`.
*   Notifications to a Slack channel.
*   Publishing of user manuals to a dedicated Git repository.

This guide will walk you through installation, configuration, and usage of all its features.
