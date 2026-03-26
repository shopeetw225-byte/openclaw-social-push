---
name: account-matrix
description: Use when maintaining account ledgers, verification status, or preflight checks for multi-platform publishing accounts, especially before or after validating publishing workflows, without changing the publishing skill itself.
---

# Account Matrix

## Overview

This skill is a lightweight governance companion for publishing skills.

Use it to keep track of:

- which account is used for which platform
- which content shape has been verified
- what should be checked before a real publish

This skill does **not** publish content. It exists alongside publishing skills such as `social-push`.

## When to Use

Use this skill when you need to:

- create or update an account ledger
- record whether a platform/content shape is only wired, submit-tested, or fully verified
- check which account should be used before a real publish
- avoid mixing “workflow exists” with “real publish already succeeded”

Do **not** use this skill to drive browser automation or execute the actual publish flow.

## Install

This repository keeps `account-matrix/` as the source directory.

To use it as a standalone runtime skill, install it separately at:

```text
~/.openclaw/skills/account-matrix
```

Supported phase-1 install modes:

- symlink `account-matrix/` into `~/.openclaw/skills/account-matrix`
- copy `account-matrix/` into `~/.openclaw/skills/account-matrix`

If installed via copy, remember to re-copy after updates.

## Outputs

This skill maintains three artifacts:

- `templates/account-matrix.md`
- `templates/verification-matrix.md`
- `templates/preflight-checklist.md`

## Status Vocabulary

Use only these values in verification records:

| status | meaning |
|---|---|
| `workflow_only` | Workflow exists, but no page-level verification yet |
| `page_verified` | Page entry and controls verified |
| `submit_ok` | Submit action verified |
| `real_publish_ok` | Real publish confirmed successful |
| `submit_ok_filtered` | Submit succeeded, but platform/community filters removed the content |

## Naming Conventions

Recommended platform values:

- `zhihu`
- `reddit`
- `x`
- `threads`
- `facebook`
- `xiaohongshu`
- `weibo`
- `wechat-official-account`
- `juejin`
- `instagram`

Recommended content type values:

- `article`
- `column`
- `idea`
- `text_post`
- `image_post`
- `link_post`
- `longform`
- `short_post`

These values are intended to stay close to publishing-skill naming, but this skill does not import or depend on another skill's files.

## Preflight Rules

Before any real publish, check:

- platform
- account alias
- expected display name
- content type
- current verification status
- whether the planned publish exceeds the currently verified scope

If a row is only `workflow_only`, `page_verified`, or `submit_ok_filtered`, do not describe that path as “fully verified”.

## Working Style

When updating matrices:

- prefer appending evidence over rewriting history
- keep real account data out of templates unless the user explicitly wants a filled-in matrix
- use one canonical alias per account, such as `main`, `alt`, or `brand`
- keep notes short and factual

## Quick Reference

| task | file |
|---|---|
| record platform-account mapping | `templates/account-matrix.md` |
| record validation result | `templates/verification-matrix.md` |
| run publish prep checklist | `templates/preflight-checklist.md` |
