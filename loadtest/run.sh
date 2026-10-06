#!/usr/bin/env bash
#
# Runs a load test of PrepPilot end to end, on the isolated stack with the fake LLM:
# starts Docker and the stack (rebuilt from your current code), configures the fake LLM, runs
# the Playwright user journeys, and saves timings, AI-call stats, container CPU/memory and
# backend errors to loadtest/results/<time>-<profile>/.
#
# It never calls OpenAI and never touches the Atlas database. Run with --help for options.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
E2E_DIR="$ROOT_DIR/e2e"
COMPOSE=(docker compose -f "$SCRIPT_DIR/docker-compose.yml")
FAKE_LLM_URL="http://localhost:8090"
STACK_PORTS="3000 8080 8090 27019"

usage() {
  cat <<'EOF'
Usage: loadtest/run.sh [profile] [options]

Profiles (each user is a real browser; one session = one Learn, Test or Mock Interview journey):
  smoke      3 users x 1 session, short pauses       ~2 min   checks that everything works
  standard   10 users x 3 sessions (default)          ~5 min   everyday load test
  stress     20 users x 2 sessions, short pauses      ~5 min   finds where it starts to slow down
  soak       5 users x 30 sessions, long pauses       ~40 min  finds leaks and slow degradation
  chaos      10 users x 2 sessions with AI failures   ~4 min   errors, 429s, dropped streams, bad JSON
             (some sessions are expected to fail; the point is to see which, and what users saw)

Load:
  --users N            concurrent users (browsers)
  --rounds N           sessions each user runs
  --think MS           average pause between user actions, in ms
  --journey NAME       learn | test | interview | all (default: all)

Fake LLM (applied for this run; see loadtest/README.md):
  --ai-speed X         1 = real gpt-4o-mini speed, 0.1 = 10x faster, 0 = instant (default 1)
  --error-rate X       share of AI calls answered with a 500 (0-1)
  --rate-limit-rate X  share answered with a 429
  --drop-rate X        share of streams cut off halfway
  --bad-json-rate X    share of JSON replies that are malformed
  --slow-rate X        share of AI calls that start 3-8x slower (default 0.02)

Checks:
  --max-p95 NAME=MS    fail the run if a step's p95 is above MS, e.g. --max-p95 learn.first_token=2000
                       (repeatable; step names are printed in the timing table)

Stack:
  --no-build           don't rebuild images (faster, but tests the last build, not your current code)
  --fresh              wipe the test database before starting
  --down               stop the stack when the run ends (default: leave it running)

Exit code: 0 if every session passed and every --max-p95 held, 1 otherwise, 2 for setup errors.
EOF
}

# ------------------------------------------------------------------------------- output

if [ -t 1 ]; then
  BOLD=$'\033[1m' DIM=$'\033[2m' RED=$'\033[31m' GREEN=$'\033[32m' YELLOW=$'\033[33m' RESET=$'\033[0m'
else
  BOLD='' DIM='' RED='' GREEN='' YELLOW='' RESET=''
fi

step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RESET"; }
info() { printf '    %s\n' "$1"; }
warn() { printf '%s    warning: %s%s\n' "$YELLOW" "$1" "$RESET"; }
die() { printf '\n%serror: %s%s\n' "$RED" "$1" "$RESET" >&2; exit 2; }
plural() { if [ "$1" = 1 ]; then echo "1 $2"; else echo "$1 ${2}s"; fi; }

# ------------------------------------------------------------------------------- arguments

profile=standard
users='' rounds='' think='' journey=all
ai_speed='' error_rate='' rate_limit_rate='' drop_rate='' bad_json_rate='' slow_rate=''
build=1 fresh=0 down_after=0
gates=()

need_value() { [ $# -ge 2 ] && [ -n "$2" ] || die "$1 needs a value (see --help)"; }

while [ $# -gt 0 ]; do
  case "$1" in
    smoke|standard|stress|soak|chaos) profile=$1 ;;
    --users) need_value "$@"; users=$2; shift ;;
    --rounds) need_value "$@"; rounds=$2; shift ;;
    --think) need_value "$@"; think=$2; shift ;;
    --journey) need_value "$@"; journey=$2; shift ;;
    --ai-speed) need_value "$@"; ai_speed=$2; shift ;;
    --error-rate) need_value "$@"; error_rate=$2; shift ;;
    --rate-limit-rate) need_value "$@"; rate_limit_rate=$2; shift ;;
    --drop-rate) need_value "$@"; drop_rate=$2; shift ;;
    --bad-json-rate) need_value "$@"; bad_json_rate=$2; shift ;;
    --slow-rate) need_value "$@"; slow_rate=$2; shift ;;
    --max-p95) need_value "$@"; gates+=("$2"); shift ;;
    --no-build) build=0 ;;
    --fresh) fresh=1 ;;
    --down) down_after=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
  shift
done

# Profile defaults: users rounds think error rate_limit drop bad_json slow
case "$profile" in
  smoke)    set -- 3  1  500  0   0    0    0   0.02 ;;
  standard) set -- 10 3  2000 0   0    0    0   0.02 ;;
  stress)   set -- 20 2  500  0   0    0    0   0.02 ;;
  soak)     set -- 5  30 3000 0   0    0    0   0.02 ;;
  chaos)    set -- 10 2  1000 0.1 0.05 0.05 0.1 0.2 ;;
esac
users=${users:-$1} rounds=${rounds:-$2} think=${think:-$3}
error_rate=${error_rate:-$4} rate_limit_rate=${rate_limit_rate:-$5} drop_rate=${drop_rate:-$6}
bad_json_rate=${bad_json_rate:-$7} slow_rate=${slow_rate:-$8} ai_speed=${ai_speed:-1}

is_int() { [[ $1 =~ ^[0-9]+$ ]] && [ "$1" -gt 0 ]; }
is_number() { [[ $1 =~ ^[0-9]+(\.[0-9]+)?$ ]]; }
is_rate() { is_number "$1" && awk -v r="$1" 'BEGIN { exit !(r <= 1) }'; }

is_int "$users" || die "--users must be a positive whole number"
is_int "$rounds" || die "--rounds must be a positive whole number"
[[ $think =~ ^[0-9]+$ ]] || die "--think must be a whole number of milliseconds"
is_number "$ai_speed" || die "--ai-speed must be a number like 1 or 0.1"
for pair in "error-rate:$error_rate" "rate-limit-rate:$rate_limit_rate" "drop-rate:$drop_rate" \
            "bad-json-rate:$bad_json_rate" "slow-rate:$slow_rate"; do
  is_rate "${pair#*:}" || die "--${pair%%:*} must be between 0 and 1"
done
for gate in ${gates[@]+"${gates[@]}"}; do
  [[ $gate =~ ^[a-z_.]+=[0-9]+$ ]] || die "--max-p95 expects NAME=MS, e.g. learn.first_token=2000 (got '$gate')"
done

case "$journey" in
  all) journey_count=3; grep_args=() ;;
  learn) journey_count=1; grep_args=(--grep "studies a topic in Learn Mode") ;;
  test) journey_count=1; grep_args=(--grep "candidate takes a test") ;;
  interview) journey_count=1; grep_args=(--grep "candidate does a mock interview") ;;
  *) die "--journey must be learn, test, interview or all" ;;
esac

# Playwright repeats each journey; spread users x rounds sessions over the selected journeys.
sessions=$((users * rounds))
repeat_each=$(((sessions + journey_count - 1) / journey_count))
sessions=$((repeat_each * journey_count))

RESULTS="$SCRIPT_DIR/results/$(date +%Y%m%d-%H%M%S)-$profile"
mkdir -p "$RESULTS"

SAMPLER_PID=''
FAKE_LLM_KNOBS='["latency_scale","error_rate","rate_limit_rate","stream_drop_rate","bad_json_rate","slow_rate"]'
previous_fake_config=''

stop_resource_sampler() {
  if [ -n "$SAMPLER_PID" ]; then
    kill "$SAMPLER_PID" 2>/dev/null || true
    wait "$SAMPLER_PID" 2>/dev/null || true
    SAMPLER_PID=''
  fi
}

# Put the fake LLM back the way it was, so a chaos run doesn't leak into the next `npm test`.
restore_fake_llm() {
  if [ -n "$previous_fake_config" ]; then
    curl -fsS -X PATCH "$FAKE_LLM_URL/admin/config" -H 'content-type: application/json' \
      -d "$previous_fake_config" >/dev/null 2>&1 || true
    previous_fake_config=''
  fi
}

on_exit() {
  stop_resource_sampler
  restore_fake_llm
}
trap on_exit EXIT

# ------------------------------------------------------------------------------- steps

ensure_docker() {
  command -v docker >/dev/null || die "Docker is not installed."
  docker info >/dev/null 2>&1 && return
  if [ "$(uname)" = Darwin ] && [ -d /Applications/Docker.app ]; then
    step "Starting Docker Desktop"
    open -a Docker
    local _
    for _ in $(seq 1 60); do
      docker info >/dev/null 2>&1 && return
      sleep 3
    done
  fi
  die "Docker is not running. Start it and run this again."
}

ensure_playwright() {
  command -v npm >/dev/null || die "Node.js and npm are required for the browser journeys."
  if [ ! -d "$E2E_DIR/node_modules/@playwright/test" ]; then
    step "Installing the Playwright test dependencies"
    (cd "$E2E_DIR" && npm ci --no-audit --no-fund) || die "npm ci failed in e2e/"
  fi
  # A no-op when Chromium is already installed.
  (cd "$E2E_DIR" && npx playwright install chromium >"$RESULTS/playwright-install.log" 2>&1) ||
    die "Could not install Chromium for Playwright; see $RESULTS/playwright-install.log"
}

stack_running() {
  [ -n "$("${COMPOSE[@]}" ps -q --status running 2>/dev/null)" ]
}

check_ports() {
  stack_running && return
  local port owner
  for port in $STACK_PORTS; do
    owner=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR == 2 { print $1 " (pid " $2 ")" }' || true)
    if [ -n "$owner" ]; then
      die "port $port is in use by $owner. The test stack needs ports $STACK_PORTS; stop the regular docker-compose.yml stack or 'npm run dev' first."
    fi
  done
}

start_stack() {
  if [ "$fresh" = 1 ]; then
    step "Wiping the test database"
    "${COMPOSE[@]}" down -v >>"$RESULTS/compose.log" 2>&1 || die "could not stop the stack; see $RESULTS/compose.log"
  fi
  local args=(up -d --wait)
  if [ "$build" = 1 ]; then
    args+=(--build)
    step "Building and starting the stack from your current code (the first build takes a few minutes)"
  else
    step "Starting the stack"
  fi
  if ! "${COMPOSE[@]}" "${args[@]}" >>"$RESULTS/compose.log" 2>&1; then
    tail -n 20 "$RESULTS/compose.log" >&2
    die "the stack did not become healthy; full log: $RESULTS/compose.log"
  fi
  info "frontend http://localhost:3000 · gateway :8080 · fake LLM :8090 · MongoDB :27019"
}

configure_fake_llm() {
  step "Configuring the fake LLM"
  local config
  previous_fake_config=$(curl -fsS "$FAKE_LLM_URL/admin/config" 2>/dev/null |
    node -e 'let s = ""; process.stdin.on("data", (d) => (s += d)).on("end", () => {
      const config = JSON.parse(s), keys = JSON.parse(process.argv[1])
      console.log(JSON.stringify(Object.fromEntries(keys.map((k) => [k, config[k]]))))
    })' "$FAKE_LLM_KNOBS" 2>/dev/null) || previous_fake_config=''
  config=$(printf '{"latency_scale": %s, "error_rate": %s, "rate_limit_rate": %s, "stream_drop_rate": %s, "bad_json_rate": %s, "slow_rate": %s}' \
    "$ai_speed" "$error_rate" "$rate_limit_rate" "$drop_rate" "$bad_json_rate" "$slow_rate")
  curl -fsS -X PATCH "$FAKE_LLM_URL/admin/config" -H 'content-type: application/json' -d "$config" \
    >"$RESULTS/fake-llm-config.json" || die "could not configure the fake LLM at $FAKE_LLM_URL"
  curl -fsS -X POST "$FAKE_LLM_URL/admin/reset-stats" >/dev/null
  info "speed x$ai_speed · errors $error_rate · 429s $rate_limit_rate · dropped streams $drop_rate · bad JSON $bad_json_rate · slow starts $slow_rate"
}

start_resource_sampler() {
  echo "time,container,cpu_percent,memory" >"$RESULTS/docker-stats.csv"
  (
    while true; do
      now=$(date +%H:%M:%S)
      docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' 2>/dev/null |
        grep '^preppilot-loadtest-' | sed "s/^/$now,/" >>"$RESULTS/docker-stats.csv" || true
      sleep 5
    done
  ) &
  SAMPLER_PID=$!
}

run_journeys() {
  step "Running $(plural "$sessions" session) with $(plural "$users" "concurrent user") (pause ~${think}ms between actions)"
  local cores
  cores=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)
  if [ "$users" -gt $((cores * 2)) ]; then
    warn "$users browsers on $cores CPU cores: the load generator itself may become the bottleneck and inflate timings."
  fi
  info "live output below; also saved to $RESULTS/playwright.log"
  echo

  set +e
  (
    cd "$E2E_DIR" &&
      LOAD_THINK_TIME_MS="$think" LOAD_SUMMARY_FILE="$RESULTS/summary.json" \
        npx playwright test --project=load --workers="$users" --repeat-each="$repeat_each" \
        --reporter=list,./support/timing-reporter.ts --output="$RESULTS/test-results" \
        ${grep_args[@]+"${grep_args[@]}"}
  ) 2>&1 | tee "$RESULTS/playwright.log"
  playwright_status=${PIPESTATUS[0]}
  set -e
}

collect_results() {
  step "Collecting results"
  curl -fsS "$FAKE_LLM_URL/stats" >"$RESULTS/fake-llm-stats.json" 2>/dev/null || echo '{}' >"$RESULTS/fake-llm-stats.json"
  "${COMPOSE[@]}" logs --no-color --since "$run_started_at" gateway user-service topic-service ai-service 2>/dev/null |
    grep -E ' ERROR |"level": ?"ERROR"|Traceback' >"$RESULTS/backend-errors.log" || true
  backend_errors=$(wc -l <"$RESULTS/backend-errors.log" | tr -d ' ')

  # Peak CPU and memory per container over the run.
  awk -F, '
    NR > 1 {
      name = $2; sub(/^preppilot-loadtest-/, "", name); sub(/-[0-9]+$/, "", name)
      cpu = $3; sub(/%/, "", cpu); cpu += 0
      split($4, parts, " / "); mem = parts[1]; mib = mem + 0
      if (mem ~ /GiB/) mib *= 1024; else if (mem ~ /KiB/) mib /= 1024
      if (cpu > peak_cpu[name]) peak_cpu[name] = cpu
      if (mib > peak_mem[name]) peak_mem[name] = mib
      seen[name] = 1
    }
    END { for (n in seen) printf "    %-14s %8.0f%% %10.0f MiB\n", n, peak_cpu[n], peak_mem[n] }
  ' "$RESULTS/docker-stats.csv" | sort >"$RESULTS/resources.txt"
}

check_gates() {
  gates_failed=0
  [ ${#gates[@]} -eq 0 ] && return 0
  [ -f "$RESULTS/summary.json" ] || { gates_failed=1; return 0; }
  node - "$RESULTS/summary.json" "${gates[@]}" <<'EOF' || gates_failed=1
const fs = require('fs')
const [file, ...gates] = process.argv.slice(2)
const metrics = Object.fromEntries(JSON.parse(fs.readFileSync(file, 'utf8')).metrics.map((m) => [m.metric, m]))
let failed = false
for (const gate of gates) {
  const [name, limit] = gate.split('=')
  const metric = metrics[name]
  if (!metric) {
    console.log(`    FAIL ${name}: no such step in this run (steps: ${Object.keys(metrics).join(', ')})`)
    failed = true
  } else if (metric.p95 > Number(limit)) {
    console.log(`    FAIL ${name}: p95 ${metric.p95}ms is above ${limit}ms`)
    failed = true
  } else {
    console.log(`    ok   ${name}: p95 ${metric.p95}ms (limit ${limit}ms)`)
  }
}
process.exit(failed ? 1 : 0)
EOF
}

print_summary() {
  step "Summary"
  node - "$RESULTS/summary.json" "$RESULTS/fake-llm-stats.json" <<'EOF' || true
const fs = require('fs')
const read = (file) => { try { return JSON.parse(fs.readFileSync(file, 'utf8')) } catch { return null } }
const [summary, llm] = process.argv.slice(2).map(read)
if (summary) {
  const passed = summary.outcomes.passed ?? 0
  const total = Object.values(summary.outcomes).reduce((a, b) => a + b, 0)
  console.log(`    ${'sessions'.padEnd(12)} ${passed} of ${total} passed`)
}
if (llm && llm.requests !== undefined) {
  const outcomes = Object.entries(llm.by_outcome).map(([k, v]) => `${k} ${v}`).join(', ')
  console.log(`    ${'AI calls'.padEnd(12)} ${llm.requests} (${outcomes}), peak ${llm.peak_in_flight} at once, ${llm.completion_tokens} tokens generated`)
  if (llm.by_scenario.unknown) {
    console.log(`    ${'WARNING'.padEnd(12)} ${llm.by_scenario.unknown} AI calls had prompts the fake LLM did not recognise; see loadtest/README.md`)
  }
}
EOF
  printf '    %-12s %s\n' "errors" "$backend_errors ERROR lines in the backend logs during the run (backend-errors.log)"
  if [ -s "$RESULTS/resources.txt" ]; then
    printf '    %-12s %s\n' "peak usage" "CPU and memory per container (sampled every ~5s):"
    sed 's/^    /                 /' "$RESULTS/resources.txt"
  fi
}

write_run_info() {
  local commit
  commit=$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)
  if [ -n "$(git -C "$ROOT_DIR" status --porcelain 2>/dev/null)" ]; then commit="$commit (with uncommitted changes)"; fi
  cat >"$RESULTS/run.txt" <<EOF
started      $(date '+%Y-%m-%d %H:%M:%S')
commit       $commit
profile      $profile
users        $users
rounds       $rounds (sessions: $sessions, journeys: $journey)
think time   ${think}ms
fake LLM     speed x$ai_speed, errors $error_rate, 429s $rate_limit_rate, dropped streams $drop_rate, bad JSON $bad_json_rate, slow $slow_rate
built        $([ "$build" = 1 ] && echo "yes, from current code" || echo "no (--no-build)")
EOF
}

# ------------------------------------------------------------------------------- main

printf '%sPrepPilot load test%s · profile %s · %s, %s each · journeys: %s\n' \
  "$BOLD" "$RESET" "$profile" "$(plural "$users" user)" "$(plural "$rounds" session)" "$journey"
info "results: ${RESULTS#$ROOT_DIR/}"

write_run_info
ensure_docker
ensure_playwright
check_ports
start_stack
configure_fake_llm
start_resource_sampler
run_started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_journeys
stop_resource_sampler
restore_fake_llm
collect_results
print_summary

if [ ${#gates[@]} -gt 0 ]; then
  step "Checks"
fi
check_gates

if [ "$down_after" = 1 ]; then
  step "Stopping the stack"
  "${COMPOSE[@]}" down >>"$RESULTS/compose.log" 2>&1
else
  printf '\n%sThe stack is still running. Stop it with: docker compose -f loadtest/docker-compose.yml down%s\n' "$DIM" "$RESET"
fi

echo
if [ "$playwright_status" -eq 0 ] && [ "$gates_failed" -eq 0 ]; then
  printf '%s%sPASSED%s  results in %s\n' "$BOLD" "$GREEN" "$RESET" "${RESULTS#$ROOT_DIR/}"
  exit 0
fi
printf '%s%sFAILED%s  ' "$BOLD" "$RED" "$RESET"
[ "$playwright_status" -ne 0 ] && printf 'some sessions failed (see Failures above). '
[ "$gates_failed" -ne 0 ] && printf 'a --max-p95 check failed. '
printf 'Results in %s\n' "${RESULTS#$ROOT_DIR/}"
exit 1
