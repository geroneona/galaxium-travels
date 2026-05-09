---
name: vulnerabilities
description: Use this skill to address vulnerabilities.
---

# Skill Instructions

Check `vulnerabilities.md` file. This is a place where user can list reported vulnerabilities that need to be addressed with priority.

Always start by updating all direct dependencies to their latest available versions.
`npx npm-check-updates` outputs the available updates. 
If a major direct dependency update is available, inform the user and ask if he wants to go ahead with updating it, because there may be refactoring needed to adopt the new major version. Present a migration plan for this update. If the migration looks risky or time consuming, it will be done later, for now latest minor/patch version of the same major version shold be applied.

Do not update `@types/node`.

Run `npm audit` to check for more dependencies, try to fix those too.

Run `npm ls --all` to understand the path through dependency tree to the vulnerable package.

Npm overrides are only allowed for minor and patch version updates and only if the vulnerability cannot be fixed by direct dependency updates.
Report back to the user list of vulnerabilities (package, version, CVE, severity) that can be fixed by overrides and ask if we wants to go ahead with it. 
Overriding MAJOR version is FORBIDDEN.

for each fixed vulnerability add in `vulnerabilities.md`:
 * a checkmark
 * a concise explanation how it was fixed

for each vulnerability that can not be fixed add in `vulnerabilities.md` a concise explanation why it can not be fixed.

Test that everything is still working fine by running the tests described in the testing skill.

