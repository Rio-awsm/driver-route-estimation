import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Place, PlanRequest } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Field, FieldGroup, FieldLabel, FieldLegend, FieldSet } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Spinner } from '@/components/ui/spinner'
import { toLocalInputValue } from '@/lib/format'
import { PlaceInput } from './PlaceInput'

const INTERVALS = [10, 25, 50] as const
const HOUR_MS = 3_600_000

type Props = {
  busy: boolean
  onSubmit: (request: PlanRequest) => void
}

export function TripForm({ busy, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toLocalInputValue(new Date(Date.now() + HOUR_MS)))
  const [loadLb, setLoadLb] = useState('35000')
  const [intervalMiles, setIntervalMiles] = useState<PlanRequest['interval_miles']>(25)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!origin || !destination) return
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: Number(loadLb),
      interval_miles: intervalMiles,
    })
  }

  return (
    <form onSubmit={submit}>
      <FieldGroup className="gap-4">
        <PlaceInput id="origin" label="Origin" value={origin} onChange={setOrigin} />
        <PlaceInput id="destination" label="Destination" value={destination} onChange={setDestination} />
        <div className="grid gap-3 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="departure">Departure</FieldLabel>
            <Input
              id="departure"
              type="datetime-local"
              required
              value={departure}
              onChange={(event) => setDeparture(event.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="load">Load weight (lb)</FieldLabel>
            <Input
              id="load"
              type="number"
              required
              min={0}
              max={120000}
              step={500}
              value={loadLb}
              onChange={(event) => setLoadLb(event.target.value)}
            />
          </Field>
        </div>
        <FieldSet>
          <FieldLegend variant="label">Check weather every</FieldLegend>
          <RadioGroup
            className="flex gap-5"
            value={String(intervalMiles)}
            onValueChange={(value) => setIntervalMiles(Number(value) as PlanRequest['interval_miles'])}
          >
            {INTERVALS.map((miles) => (
              <Field key={miles} orientation="horizontal" className="w-auto">
                <RadioGroupItem value={String(miles)} id={`interval-${miles}`} />
                <FieldLabel htmlFor={`interval-${miles}`} className="font-normal">
                  {miles} mi
                </FieldLabel>
              </Field>
            ))}
          </RadioGroup>
        </FieldSet>
        <Button type="submit" disabled={busy || !origin || !destination}>
          {busy && <Spinner />}
          {busy ? 'Planning routes' : 'Plan routes'}
        </Button>
      </FieldGroup>
    </form>
  )
}
