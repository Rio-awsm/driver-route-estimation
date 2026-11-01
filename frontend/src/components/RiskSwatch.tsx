import { RISK_LEVELS } from '@/lib/risk'

export function RiskSwatch({ level }: { level: number }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block size-3 shrink-0 rounded-[3px]"
      style={{ backgroundColor: RISK_LEVELS[level].hex }}
    />
  )
}
