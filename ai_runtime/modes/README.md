# AI Mode Profiles

Mode profiles let you keep shared credentials in the normal root `.env` and switch the AI stack as one bundle.

## Local setup

```bash
cp ai_runtime/modes/openai.env.example ai_runtime/modes/openai.env
cp ai_runtime/modes/opensource.env.example ai_runtime/modes/opensource.env
```

Edit the copied `.env` files for local endpoints and keys. These copied files are ignored by git.

## Option 1: select from `.env`

Put one of these lines in the root `.env`:

```env
AI_MODE=openai
```

or:

```env
AI_MODE=opensource
```

The provider runtime loads `ai_runtime/modes/<AI_MODE>.env` first, then falls back to the shared `.env` values.

## Option 2: select at process start

```bash
scripts/run_ai_mode.sh opensource -- python3 -m uvicorn pre_application_valuation.api:app --reload --port 8010
```

The wrapper loads root `.env`, then the selected mode profile, then runs the command.
