import { RISK_LEVELS } from '@/lib/risk'
import { RiskSwatch } from './RiskSwatch'

export function Legend() {
  return (
    <ul
      aria-label="Risk levels"
      className="absolute top-3 right-3 flex flex-col gap-1 rounded-lg border bg-card/95 p-2.5 text-xs shadow-sm"
    >
      {RISK_LEVELS.map((level, index) => (
        <li key={level.label} className="flex items-center gap-2">
          <RiskSwatch level={index} />
          {level.label}
        </li>
      ))}
    </ul>
  )
}
