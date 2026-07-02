---
description: Delegate a prompt to the installed hermes-call CLI and return its JSON contract.
argument-hint: "<prompt>"
---

Run:

```bash
hermes-call --json --prompt "$ARGUMENTS"
```

Return the JSON contract to the host flow. For an explicit completion loop, use:

```bash
hermes-call --json --until-done --max-iterations 8 --prompt "$ARGUMENTS"
```

Pass a requested model with `-m <model>`. Do not call Hermes directly from the host plugin; `hermes-call`
owns session capture, cleanup, and the verified resume path documented in `docs/hermes-cli-contract.md`.
