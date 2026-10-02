--- 
title: FAQ
---
# Frequently Asked Questions

**Q: My build failed with "Compiled assets are not release-ready". What should I do?**

A: `sw-build` compares your asset sources with the compiled output by **content hash**, not by timestamp. Two situations produce this error:

1. *An asset target has sources but no compiled output at all* — and your plugin already ships compiled assets elsewhere, so it clearly is supposed to compile. You have changed a source and not rebuilt.
2. *The sources changed but the compiled output did not* — you edited a source and have not recompiled since. If you **did** recompile and still see this, your rebuild produced byte-identical output; use `--rebaseline-assets` once to record the new baseline.

In both cases, run your asset build and run `sw-build` again.

If you see this for a plugin that genuinely has no build step at all, that is a `--require-compiled-assets` build; drop the flag for such plugins.

```bash
# For administration assets
./bin/build-administration.sh

# For storefront assets
./bin/build-storefront.sh
```

**Q: The tool isn't syncing my package to the remote server. Why?**

A: There are a few possible reasons:
1.  **Configuration:** Ensure that `RSYNC_SSH_HOST` and `RSYNC_REMOTE_PATH_RELEASES_FOLDER` are correctly set in your `.env` file.
2.  **`--no-sync` flag:** Check if you are running the command with the `--no-sync` flag, which explicitly disables the upload.
3.  **SSH Access:** Verify that you have passwordless SSH access (e.g., via SSH keys) to the configured host. The tool does not support interactive password prompts.

**Q: How do I control which files are included in the ZIP archive?**

A: Create a file named `.sw-zip-blacklist` in the root directory of your plugin. Add the names of files or directories you wish to exclude, one per line. You can use wildcards (e.g., `*.log`, `temp/*`).

**Q: Why do I need to set `FOUNDATION_PLUGIN_PATH`?**

A: The `FOUNDATION_PLUGIN_PATH` is required for the "Foundation Injection" feature. When `sw-build` needs to embed the foundation code, it needs to know where to find the source files on your local machine. This should be the path to your local clone of the `topdata-foundation-sw6` repository.

**Q: Can I create a "Pro" version and a "Free" version in one command?**

A: Not in a single command execution. The `--variant-prefix` and `--variant-suffix` options can be combined, but they will generate only one variant in addition to the original package. To create two different variants, you would run the command twice with different options:
```bash
# First, create the Free version
sw-build --variant-prefix Free

# Then, create the Pro version
sw-build --variant-suffix Pro
```
