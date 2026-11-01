import { MapLibreOverlay } from '@deck.gl/maplibre'
import { AttributionControl, LngLatBounds, Map as MapLibreMap, setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import type { Ref } from 'react'
import type { Plan } from '@/api/types'
import { buildFrames } from './heatmapFrames'
import { allRouteLayers, checkpointTooltip, heatLayers } from './layers'

setWorkerUrl(workerUrl)

const BASEMAP = 'https://tiles.openfreemap.org/styles/positron'
const WEATHER_CREDIT = 'Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a>'
const FIT_PADDING = { top: 40, bottom: 130, left: 40, right: 40 }

export type TripMapHandle = { setHour: (hour: number) => void }

type Props = {
  plan: Plan | null
  selectedRouteId: string | null
  onSelectRoute: (id: string) => void
  ref?: Ref<TripMapHandle>
}

type Engine = { map: MapLibreMap; overlay: MapLibreOverlay; firstLabelId: string }

export default function TripMap({ plan, selectedRouteId, onSelectRoute, ref }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const hourRef = useRef(0)
  const frameRequest = useRef(0)
  const [engine, setEngine] = useState<Engine | null>(null)
  const frames = useMemo(() => (plan ? buildFrames(plan.heatmap) : []), [plan])

  useEffect(() => {
    const map = new MapLibreMap({
      container: containerRef.current!,
      style: BASEMAP,
      center: [-98, 39],
      zoom: 3.4,
      attributionControl: false,
    })
    map.addControl(new AttributionControl({ compact: true, customAttribution: WEATHER_CREDIT }))
    const overlay = new MapLibreOverlay({ interleaved: true, layers: [], getTooltip: checkpointTooltip })
    map.addControl(overlay)
    map.once('load', () => {
      const firstLabel = map.getStyle().layers.find((layer) => layer.type === 'symbol')
      setEngine({ map, overlay, firstLabelId: firstLabel?.id ?? '' })
    })
    return () => {
      setEngine(null)
      map.remove()
    }
  }, [])

  const draw = useCallback(() => {
    if (!engine) return
    const layers =
      plan && selectedRouteId
        ? [
            ...heatLayers(plan, frames, hourRef.current, engine.firstLabelId),
            ...allRouteLayers(plan, selectedRouteId, onSelectRoute),
          ]
        : []
    engine.overlay.setProps({ layers })
  }, [engine, plan, selectedRouteId, frames, onSelectRoute])

  const latestDraw = useRef(draw)
  useEffect(() => {
    latestDraw.current = draw
    draw()
  }, [draw])

  useEffect(() => {
    if (!engine || !plan) return
    const bounds = new LngLatBounds()
    plan.routes.forEach((route) => {
      route.segments.forEach((segment) => segment.path.forEach((point) => bounds.extend(point)))
    })
    engine.map.fitBounds(bounds, { padding: FIT_PADDING, duration: 800 })
  }, [engine, plan])

  useImperativeHandle(ref, () => ({
    setHour(hour) {
      hourRef.current = hour
      cancelAnimationFrame(frameRequest.current)
      frameRequest.current = requestAnimationFrame(() => latestDraw.current())
    },
  }), [])

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="size-full" role="application" aria-label="Route and weather map" />
    </div>
  )
}
