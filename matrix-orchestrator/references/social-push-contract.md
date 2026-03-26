# Social Push Contract

This file defines the integration boundary between `matrix-orchestrator` and `social-push`.

## Purpose

`matrix-orchestrator` does not re-implement publishing workflows. It passes a normalized job payload to the publishing layer and converts the outcome into orchestrator-friendly result states.

## Required Inputs

At minimum, the dispatch layer should accept:

| field | meaning |
|---|---|
| `job_id` | Queue job identifier |
| `attempt_no` | Current attempt number |
| `platform` | Target platform |
| `account_alias` | Selected account alias |
| `content_type` | Content shape |
| `title` | Title if applicable |
| `body` | Body text if applicable |
| `media_paths` | Comma-separated or list of staged source media paths |
| `notes` | Optional runtime notes |

## Environment Assumptions

The publishing layer may expect:

- `OPENCLAW_BIN`
- `SKILL_ROOT`
- active browser attachment when `chrome-relay` is used
- optional `MATRIX_ORCHESTRATOR_ENABLE_DEFAULT_RUNNER=1` if you want the orchestrator to use its built-in OpenClaw dispatch path
- optional `MATRIX_ORCHESTRATOR_OPENCLAW_MODE=local` if you want that built-in runner to use embedded local mode instead of gateway mode
- optional `MATRIX_ORCHESTRATOR_OPENCLAW_AGENT`, `MATRIX_ORCHESTRATOR_OPENCLAW_SESSION_ID`, and `MATRIX_ORCHESTRATOR_OPENCLAW_TIMEOUT` for runner selection and timeout control
- when gateway mode is used, the target OpenClaw session must already have the intended `social-push` skill version installed; gateway mode does not automatically read this repo working tree

The orchestrator should not guess platform-specific browser refs. It should hand off structured publish intent.

## Expected Outputs

Normalized dispatch results should include:

| field | meaning |
|---|---|
| `ok` | Whether the dispatch succeeded |
| `result_status` | Orchestrator result code |
| `evidence` | URL, content id, API success, or page evidence |
| `notes` | Human-readable explanation |
| `jump_target` | Optional current page URL or other locator for operator follow-up |
| `observed_account` | Optional visible/current account identity observed by the runner |

Allowed `result_status` values:

- `publish_ok`
- `publish_filtered`
- `publish_failed`
- `runner_error`

`jump_target` and `observed_account` are optional. Legacy runner outputs without these fields remain valid.

## Mapping Guidance

Suggested mapping:

- real publish confirmed -> `publish_ok`
- content submitted then filtered/removed -> `publish_filtered`
- publish reached platform but failed validation or user-facing failure -> `publish_failed`
- orchestration/runtime exception -> `runner_error`

## Testing Guidance

Unit tests should not invoke live browser automation.

`dispatch_social_push.py` should therefore expose an injectable runner or callable so tests can simulate:

- successful publish
- filtered publish
- failed publish
- runtime error
