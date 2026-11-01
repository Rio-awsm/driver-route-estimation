import { PauseIcon, PlayIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { formatClock } from '@/lib/format'

const MAX_HOUR = 48
const HOUR_MS = 3_600_000
const PLAY_HOURS_PER_SECOND = 4
const TICKS = [0, 12, 24, 36, 48]

type Props = {
  start: string
  onChange: (hour: number) => void
}

export function ForecastSlider({ start, onChange }: Props) {
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)
  const lastFrame = useRef(0)

  useEffect(() => {
    onChange(hour)
  }, [hour, onChange])

  useEffect(() => {
    if (!playing) return
    let request = requestAnimationFrame(function tick(now) {
      const elapsed = lastFrame.current ? (now - lastFrame.current) / 1000 : 0
      lastFrame.current = now
      setHour((current) => (current + elapsed * PLAY_HOURS_PER_SECOND) % MAX_HOUR)
      request = requestAnimationFrame(tick)
    })
    return () => {
      cancelAnimationFrame(request)
      lastFrame.current = 0
    }
  }, [playing])

  const moment = new Date(new Date(start).getTime() + hour * HOUR_MS)

  return (
    <div className="absolute inset-x-3 bottom-14 flex items-center gap-3 rounded-lg border bg-card/95 p-3 shadow-sm md:bottom-8">
      <Button
        size="icon"
        aria-label={playing ? 'Pause forecast' : 'Play forecast'}
        onClick={() => setPlaying(!playing)}
      >
        {playing ? <PauseIcon /> : <PlayIcon />}
      </Button>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="text-sm font-medium tabular-nums">
          +{Math.floor(hour)}h · {formatClock(moment)}
        </p>
        <Slider
          aria-label="Forecast hours after departure"
          aria-valuetext={`${Math.floor(hour)} hours after departure`}
          min={0}
          max={MAX_HOUR}
          step={0.1}
          value={[hour]}
          onValueChange={([value]) => {
            setPlaying(false)
            setHour(value)
          }}
        />
        <div aria-hidden="true" className="flex justify-between text-xs text-muted-foreground tabular-nums">
          {TICKS.map((tick) => (
            <span key={tick}>{tick}h</span>
          ))}
        </div>
      </div>
    </div>
  )
}
