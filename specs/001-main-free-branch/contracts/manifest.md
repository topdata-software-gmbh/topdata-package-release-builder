# Contract: `.topdata/build.yaml` manifest

**Consumer**: `sw-build` on every build, before free work.
**Producer**: plugin repository maintainer; the file is committed to the plugin repository.

## Location

`<plugin-root>/.topdata/build.yaml`

The file is optional. Its absence means "free branch publishing is off".

## Schema

```yaml
free:
  branch: main-free   # optional string, default "main-free"
  zip: false          # optional boolean, default false
```

- The root document MUST be a mapping if the file exists and is non-empty.
- The `free` key is optional; when absent the feature is disabled.
- `free: null` and `free: {}` both mean "enabled with all defaults".
- Unknown keys are ignored.
- No other manifest file name or location is recognized.

## Validation

| Condition | Result |
|---|---|
| File absent | Feature disabled; build unchanged |
| File empty / comments only (`None` document) | Feature disabled |
| Root is a list, string, or scalar | Build aborts with a clear manifest error |
| `free` absent | Feature disabled |
| `free` is `null` or a mapping | Feature enabled |
| `free` is a list/string/number/bool | Build aborts with a clear manifest error |
| `branch` absent | `main-free` |
| `branch` empty, whitespace-padded, contains whitespace or `..` | Build aborts |
| `branch` rejected by `git check-ref-format refs/heads/<branch>` | Build aborts |
| `zip` absent | `false` |
| `zip` not a boolean | Build aborts |

## Error contract

- All manifest errors MUST be reported to the user with the offending path and a short reason.
- Manifest errors MUST result in a non-zero exit and MUST prevent manual publishing, uploads,
  and notifications.
- Manifest errors MUST NOT be silently downgraded to "disabled".

## Privacy / payload

- The manifest is build metadata, not plugin code. It MUST NOT appear in the release ZIP or the
  free branch payload.
- The manifest may be committed to the plugin repository; the clean-working-tree rule therefore
  applies to it like any other tracked file.
