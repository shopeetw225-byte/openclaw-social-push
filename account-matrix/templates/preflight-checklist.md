# Preflight Checklist Template

Use this checklist before a real publish.

## Target

- Platform: `<platform>`
- Account alias: `<account_alias>`
- Content type: `<content_type>`

## Account Check

- [ ] The current browser page is logged into the expected platform account
- [ ] The visible browser account name matches `display_name` from the account matrix
- [ ] The intended browser control mode matches the recorded `browser_profile`

## Verification Check

- [ ] A matching row exists in the verification matrix for this `platform + account_alias + content_type`
- [ ] The verification `status` has been reviewed
- [ ] If status is `workflow_only`, `page_verified`, or `submit_ok_filtered`, do not claim the path is fully verified
- [ ] If the planned publish exceeds the currently verified scope, note that risk before continuing

## Publish Readiness

- [ ] Title / body / media are prepared
- [ ] The correct platform-specific workflow has been selected
- [ ] The intended account is still active in the browser after final page load

## Result Summary

- Decision: `<go / no-go>`
- Reason: `<short summary>`
- Notes: `<optional notes>`
