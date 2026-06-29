---
description: Build, push, and redeploy the ChronoLog backend to the GCP VM
argument-hint: <version, e.g. v1.0.2>
model: sonnet
allowed-tools: Bash(scripts/deploy-backend.sh:*), Bash(git*), Read, Edit
---

Deploy the backend to the Google Cloud VM by running the deploy script.

Version to deploy: $ARGUMENTS

Steps:
1. If no version was given, look at the current tag in `docker-compose.yml`
   (`image: mukund146/chronologbackend:vX.Y.Z`) and propose the next patch version, then ask
   the author to confirm before deploying.
2. Confirm `scripts/.env.deploy` exists. If it does not, tell the author to copy
   `scripts/.env.deploy.example` to `scripts/.env.deploy` and fill it in — do NOT proceed.
3. Run: `scripts/deploy-backend.sh <version>` and stream the output. This builds the image,
   pushes to Docker Hub, bumps the tag in `docker-compose.yml`, copies it to the VM, and
   restarts the container.
4. If it fails, report exactly which step failed (build / push / scp / ssh / compose) and stop —
   do not retry blindly.
5. On success, the script will have modified `docker-compose.yml` (the tag bump). Show the diff
   and commit it on the current branch with a message like `chore: deploy backend <version>`.
6. Print the deployed version and remind the author to sanity-check https://chronologtracker.com.

This deploys to PRODUCTION. Treat it as outward-facing: confirm the version before running.
