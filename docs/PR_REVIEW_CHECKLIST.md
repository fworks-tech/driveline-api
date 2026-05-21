# PR Review Checklist

Use this checklist when preparing a pull request description or reviewing changes before merge.

## Scope

- [ ] The PR title matches the issue or feature being delivered.
- [ ] The PR only includes changes needed for the stated issue.
- [ ] Unrelated refactors or fixes are split into follow-up work.

## Functionality

- [ ] The main user-facing flow still works.
- [ ] Error handling paths are covered or documented.
- [ ] Any new config values are documented in `.env.example` and the docs.
- [ ] Any new runtime service dependencies are documented in the setup guide.

## Docker / Local Development

- [ ] `docker compose up --build` is documented if the repo supports Compose.
- [ ] Required services are listed with their ports and environment variables.
- [ ] Health checks or liveness endpoints are documented for container startup.
- [ ] Troubleshooting steps are included for common Windows and Docker Desktop issues.

## Testing

- [ ] Relevant tests were run locally.
- [ ] The test command is included in the PR description.
- [ ] New or changed behavior has test coverage.
- [ ] Coverage or skipped-test implications are explained if relevant.

## Documentation

- [ ] `README.md` reflects the current setup.
- [ ] `docs/LOCAL_DEVELOPMENT.md` is updated when the local setup changes.
- [ ] Any API contract changes are reflected in the frontend integration docs.
- [ ] Follow-up work is captured as linked issues when needed.# PR Review Checklist

Use this checklist when preparing a pull request description or reviewing changes before merge.

## Scope

- [ ] The PR title matches the issue or feature being delivered.
- [ ] The PR only includes changes needed for the stated issue.
- [ ] Unrelated refactors or fixes are split into follow-up work.

## Functionality

- [ ] The main user-facing flow still works.
- [ ] Error handling paths are covered or documented.
- [ ] Any new config values are documented in `.env.example` and the docs.
- [ ] Any new runtime service dependencies are documented in the setup guide.

## Docker / Local Development

- [ ] `docker compose up --build` is documented if the repo supports Compose.
- [ ] Required services are listed with their ports and environment variables.
- [ ] Health checks or liveness endpoints are documented for container startup.
- [ ] Troubleshooting steps are included for common Windows and Docker Desktop issues.

## Testing

- [ ] Relevant tests were run locally.
- [ ] The test command is included in the PR description.
- [ ] New or changed behavior has test coverage.
- [ ] Coverage or skipped-test implications are explained if relevant.

## Documentation

- [ ] `README.md` reflects the current setup.
- [ ] `docs/LOCAL_DEVELOPMENT.md` is updated when the local setup changes.
- [ ] Any API contract changes are reflected in the frontend integration docs.
- [ ] Follow-up work is captured as linked issues when needed.