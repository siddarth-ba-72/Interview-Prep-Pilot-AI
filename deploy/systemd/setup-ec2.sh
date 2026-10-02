#!/usr/bin/env bash
# One-time setup script to run ON each EC2 instance before the first deploy.
# Usage: sudo ./setup-ec2.sh <service-name>
#   e.g. sudo ./setup-ec2.sh gateway
#
# Creates the /preppilot/<service>/{webapp,backup} dirs, a dedicated
# unprivileged "preppilot" run user, and installs the systemd unit
# (expected to already be copied alongside this script as <service>.service).

set -euo pipefail

SERVICE="${1:?Usage: sudo ./setup-ec2.sh <service-name>}"
BASE="/preppilot/$SERVICE"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! id -u preppilot >/dev/null 2>&1; then
  useradd --system --home-dir /preppilot --shell /usr/sbin/nologin preppilot
fi

mkdir -p "$BASE/webapp" "$BASE/backup"
touch "$BASE/.env"
chown -R preppilot:preppilot /preppilot
chmod 600 "$BASE/.env"

echo "Fill in $BASE/.env with this service's real environment variables."

cp "$SCRIPT_DIR/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE"

echo "Setup complete for $SERVICE."
echo "Next: copy a built app.jar into $BASE/webapp/app.jar, then run:"
echo "  sudo systemctl start $SERVICE"
