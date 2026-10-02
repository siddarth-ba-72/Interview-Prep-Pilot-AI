# Backend deployment (GitHub Actions -> EC2)

## How it works

- `deploy-gateway.yml`, `deploy-user-service.yml`, `deploy-topic-service.yml`
  each trigger independently on pushes to `main` that touch their own module
  or the shared `cache-service` library (which all three depend on but which
  is never deployed by itself - it has no bootJar).
- All three call the shared `_deploy-service-reusable.yml` workflow, which:
  1. runs `./gradlew :<service>:test`
  2. runs `./gradlew :<service>:bootJar`
  3. uploads the jar as a build artifact
  4. scp's it to the matching EC2 instance into `/preppilot/<service>/webapp/app.jar.new`
  5. SSHes in, backs up the currently-running jar into
     `/preppilot/<service>/backup/app.jar`, promotes the new jar, and
     restarts the systemd unit.
- `rollback-service.yml` is a manual (`workflow_dispatch`) workflow that
  copies `backup/app.jar` back over `webapp/app.jar` and restarts - no
  rebuild required, for emergencies.

## One-time per-EC2-instance setup

On each of the 3 instances:

```bash
scp deploy/systemd/<service>.service deploy/systemd/setup-ec2.sh ec2-user@<host>:/tmp/
ssh ec2-user@<host>
sudo mv /tmp/<service>.service /tmp/setup-ec2.sh /tmp/
cd /tmp && sudo ./setup-ec2.sh <service>
# then edit /preppilot/<service>/.env with real secrets (JWT_SECRET, MONGODB_URI, etc.)
```

This creates:
```
/preppilot/<service>/webapp/   <- currently running app.jar
/preppilot/<service>/backup/   <- previous app.jar, used for rollback
/preppilot/<service>/.env      <- real runtime secrets, never committed
```
and installs/enables a systemd unit named `<service>` (e.g. `gateway`,
`user-service`, `topic-service`).

Also add the GitHub Actions deploy public key to `~/.ssh/authorized_keys`
for the SSH user on that instance.

## Required GitHub configuration

Create 3 GitHub Environments, one per service, each with these secrets:

| Environment | Secrets |
|---|---|
| `production-gateway` | `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY` |
| `production-user-service` | `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY` |
| `production-topic-service` | `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY` |

`EC2_SSH_KEY` is the private key whose public half is in that instance's
`authorized_keys`. Secret names are identical across environments by
design - the reusable workflow just reads `secrets.EC2_HOST` etc., and the
calling job's `environment:` determines which instance that resolves to.

Environments also let you add required reviewers/manual approval per
service if you want a gate before production deploys.

## Manual rollback

Actions tab -> "Rollback - Backend Service" -> Run workflow -> pick the
service. This restores the last backup jar and restarts the service.
