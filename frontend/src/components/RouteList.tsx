import { ChevronsUpDownIcon, CircleCheckIcon, TriangleAlertIcon } from 'lucide-react'
import { cn } from 'cn'
import type { Plan, Route } from '@/api/types'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatClock, formatDuration } from '@/lib/format'
import { RiskSwatch } from './RiskSwatch'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium tabular-nums">{value}</dd>
    </div>
  )
}

function CheckpointTable({ route }: { route: Route }) {
  return (
    <Collapsible className="border-t">
      <CollapsibleTrigger asChild>
        <Button variant="ghost" size="sm" className="w-full justify-between rounded-none">
          {route.checkpoints.length} checkpoints
          <ChevronsUpDownIcon className="opacity-50" />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="max-h-72 overflow-y-auto border-t">
          <Table className="text-xs tabular-nums">
            <TableHeader>
              <TableRow>
                <TableHead>Mile</TableHead>
                <TableHead>ETA</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Wind</TableHead>
                <TableHead>Rain</TableHead>
                <TableHead>Snow</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {route.checkpoints.map((checkpoint) => (
                <TableRow key={checkpoint.mile}>
                  <TableCell>{checkpoint.mile.toFixed(0)}</TableCell>
                  <TableCell>{formatClock(checkpoint.eta)}</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1.5">
                      <RiskSwatch level={checkpoint.risk} />
                      {checkpoint.risk_label}
                    </span>
                  </TableCell>
                  <TableCell>{checkpoint.wind_mph.toFixed(0)}</TableCell>
                  <TableCell>{checkpoint.rain_in_hr.toFixed(2)}</TableCell>
                  <TableCell>{checkpoint.snow_in_hr.toFixed(2)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

type CardProps = {
  route: Route
  recommended: boolean
  selected: boolean
  onSelect: () => void
}

function RouteCard({ route, recommended, selected, onSelect }: CardProps) {
  return (
    <Card className={cn('gap-0 py-0', selected && 'ring-2 ring-primary')}>
      <button
        type="button"
        aria-pressed={selected}
        onClick={onSelect}
        className="flex w-full cursor-pointer flex-col gap-2 rounded-xl p-3.5 text-left text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <span className="flex items-center gap-2 font-medium">
          Route {route.id}
          {recommended && <Badge>Recommended</Badge>}
        </span>
        <span className="text-muted-foreground">
          {formatDuration(route.duration_s)} · {route.distance_miles.toFixed(0)} mi · arrives{' '}
          {formatClock(route.arrival)}
        </span>
        <dl className="grid grid-cols-4 gap-2">
          <Stat label="No Travel" value={`${route.no_travel_miles.toFixed(0)} mi`} />
          <Stat label="Severe" value={`${route.severe_miles.toFixed(0)} mi`} />
          <Stat label="High" value={`${route.high_miles.toFixed(0)} mi`} />
          <Stat label="Avg risk" value={route.average_risk.toFixed(2)} />
        </dl>
      </button>
      {selected && <CheckpointTable route={route} />}
    </Card>
  )
}

type Props = {
  plan: Plan
  selectedRouteId: string | null
  onSelect: (id: string) => void
}

export function RouteList({ plan, selectedRouteId, onSelect }: Props) {
  return (
    <section aria-label="Route options" className="flex flex-col gap-3">
      <Alert variant={plan.blocked ? 'destructive' : 'default'}>
        {plan.blocked ? <TriangleAlertIcon /> : <CircleCheckIcon />}
        <AlertTitle>{plan.blocked ? 'No safe route' : 'Recommendation'}</AlertTitle>
        <AlertDescription>{plan.reason}</AlertDescription>
      </Alert>
      {plan.routes.length < 3 && (
        <p className="text-sm text-muted-foreground">
          {plan.routes.length === 1
            ? 'Only 1 truck route was found for this trip.'
            : `Only ${plan.routes.length} distinct truck routes were found for this trip.`}
        </p>
      )}
      {plan.routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          recommended={route.id === plan.recommended_route}
          selected={route.id === selectedRouteId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
    </section>
  )
}
