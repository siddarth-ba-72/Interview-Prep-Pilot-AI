import fs from 'node:fs'
import path from 'node:path'
import type { FullConfig, Reporter, TestCase, TestResult } from '@playwright/test/reporter'

interface Options {
  outputFile?: string
}

/**
 * Collects the timings tests record through the `metrics` fixture and prints count, p50, p90,
 * p95 and max per metric when the run ends. Also writes them as JSON, for comparing runs.
 * Prints nothing when no test recorded a timing.
 */
export default class TimingReporter implements Reporter {
  private readonly samples = new Map<string, number[]>()
  private readonly outcomes = new Map<string, number>()
  private readonly failures = new Map<string, number>()
  private startedAt = Date.now()
  private workers = 1
  private readonly outputFile: string

  constructor(options: Options = {}) {
    // LOAD_SUMMARY_FILE lets loadtest/run.sh put each run's results in its own folder.
    this.outputFile = process.env.LOAD_SUMMARY_FILE ?? options.outputFile ?? 'load-results/summary.json'
  }

  onBegin(config: FullConfig): void {
    this.startedAt = Date.now()
    this.workers = config.workers
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    this.outcomes.set(result.status, (this.outcomes.get(result.status) ?? 0) + 1)
    if (result.status === 'failed' || result.status === 'timedOut') {
      // First line of the error, without colour codes, so the same failure groups together.
      const reason = (result.error?.message ?? result.status).replace(/\u001b\[[0-9;]*m/g, '').split('\n')[0].trim()
      const key = `${test.title}: ${reason}`
      this.failures.set(key, (this.failures.get(key) ?? 0) + 1)
    }
    for (const attachment of result.attachments) {
      if (attachment.name !== 'metrics' || !attachment.body) continue
      const values = JSON.parse(attachment.body.toString()) as Record<string, number[]>
      for (const [name, list] of Object.entries(values)) {
        const all = this.samples.get(name) ?? []
        all.push(...list)
        this.samples.set(name, all)
      }
    }
  }

  onEnd(): void {
    if (this.samples.size === 0 && this.failures.size === 0) return

    const durationSeconds = (Date.now() - this.startedAt) / 1000
    const rows = [...this.samples.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, values]) => {
        const sorted = [...values].sort((a, b) => a - b)
        return {
          metric: name,
          count: sorted.length,
          p50: percentile(sorted, 50),
          p90: percentile(sorted, 90),
          p95: percentile(sorted, 95),
          max: sorted[sorted.length - 1],
        }
      })

    const outcomes = Object.fromEntries(this.outcomes)
    const header = ['metric', 'count', 'p50', 'p90', 'p95', 'max']
    const table = [header, ...rows.map((r) => [r.metric, String(r.count), ms(r.p50), ms(r.p90), ms(r.p95), ms(r.max)])]
    const widths = header.map((_, column) => Math.max(...table.map((row) => row[column].length)))
    const line = (row: string[]) => row.map((cell, i) => (i === 0 ? cell.padEnd(widths[i]) : cell.padStart(widths[i]))).join('   ')

    console.log(`\nTimings over ${durationSeconds.toFixed(0)}s with ${this.workers} worker(s); tests: ${JSON.stringify(outcomes)}\n`)
    console.log(line(table[0]))
    console.log(widths.map((w) => '-'.repeat(w)).join('   '))
    for (const row of table.slice(1)) console.log(line(row))

    const failures = [...this.failures.entries()].sort(([, a], [, b]) => b - a).map(([reason, count]) => ({ count, reason }))
    if (failures.length > 0) {
      console.log('\nFailures:')
      for (const { count, reason } of failures) console.log(`  ${String(count).padStart(3)} x ${reason}`)
    }

    const file = path.resolve(this.outputFile)
    fs.mkdirSync(path.dirname(file), { recursive: true })
    fs.writeFileSync(
      file,
      JSON.stringify(
        { finishedAt: new Date().toISOString(), durationSeconds, workers: this.workers, outcomes, metrics: rows, failures },
        null,
        2,
      ),
    )
    console.log(`\nWritten to ${path.relative(process.cwd(), file)}\n`)
  }
}

function percentile(sorted: number[], p: number): number {
  const rank = Math.ceil((p / 100) * sorted.length)
  return sorted[Math.min(sorted.length, Math.max(rank, 1)) - 1]
}

function ms(value: number): string {
  return value >= 10_000 ? `${(value / 1000).toFixed(1)}s` : `${value}ms`
}
