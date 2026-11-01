import type { Layer, PickingInfo } from '@deck.gl/core'
import { BitmapLayer, PathLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import type { Checkpoint, Plan, Route, Segment } from '@/api/types'
import { formatClock, formatDuration } from '@/lib/format'
import { RISK_LEVELS } from '@/lib/risk'

const HEAT_OPACITY = 0.7
const WHITE: [number, number, number] = [255, 255, 255]
const TOOLTIP_WIDTH = 220
const TOOLTIP_HEIGHT = 120
const TOOLTIP_STYLE = {
  backgroundColor: '#1f2933',
  borderRadius: '6px',
  color: '#ffffff',
  fontFamily: 'var(--font-sans)',
  fontSize: '12px',
  lineHeight: '1.5',
  padding: '8px 10px',
  width: `${TOOLTIP_WIDTH}px`,
}

export function heatLayers(plan: Plan, frames: ImageData[], hour: number, beforeId: string): Layer[] {
  const lower = Math.min(Math.floor(hour), frames.length - 1)
  const upper = Math.min(lower + 1, frames.length - 1)
  const shared = {
    bounds: plan.heatmap.bounds,
    beforeId,
    _imageCoordinateSystem: 'lnglat' as const,
  }
  return [
    new BitmapLayer({ ...shared, id: 'heat-lower', image: frames[lower], opacity: HEAT_OPACITY }),
    new BitmapLayer({
      ...shared,
      id: 'heat-upper',
      image: frames[upper],
      opacity: HEAT_OPACITY * (hour - lower),
    }),
  ]
}

function routeLabel(route: Route) {
  return `${route.id}: ${formatDuration(route.duration_s)}, ${route.severe_miles.toFixed(0)} severe mi`
}

function routeLayers(route: Route, selected: boolean, onSelect: (id: string) => void): Layer[] {
  const alpha = selected ? 255 : 110
  const pickRoute = () => onSelect(route.id)
  const middle = route.checkpoints[Math.floor(route.checkpoints.length / 2)]
  return [
    new PathLayer<Segment>({
      id: `casing-${route.id}`,
      data: route.segments,
      getPath: (segment) => segment.path,
      getColor: [...WHITE, alpha],
      getWidth: selected ? 9 : 6,
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
    }),
    new PathLayer<Segment>({
      id: `line-${route.id}`,
      data: route.segments,
      getPath: (segment) => segment.path,
      getColor: (segment) => [...RISK_LEVELS[segment.risk].rgb, alpha],
      getWidth: selected ? 6 : 3,
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
      pickable: true,
      onClick: pickRoute,
    }),
    new ScatterplotLayer<Checkpoint>({
      id: `checkpoints-${route.id}`,
      data: route.checkpoints,
      getPosition: (checkpoint) => [checkpoint.lon, checkpoint.lat],
      getFillColor: (checkpoint) => [...RISK_LEVELS[checkpoint.risk].rgb, alpha],
      getLineColor: [...WHITE, alpha],
      getRadius: selected ? 5 : 3,
      radiusUnits: 'pixels',
      lineWidthUnits: 'pixels',
      getLineWidth: 1.5,
      stroked: true,
      pickable: true,
      onClick: pickRoute,
    }),
    new TextLayer<Route>({
      id: `label-${route.id}`,
      data: [route],
      getText: routeLabel,
      getPosition: () => [middle.lon, middle.lat],
      getSize: selected ? 14 : 12,
      getColor: [31, 41, 51, 255],
      fontFamily: 'system-ui, sans-serif',
      fontWeight: selected ? 700 : 500,
      background: true,
      getBackgroundColor: [255, 255, 255, 235],
      backgroundPadding: [6, 3],
      getPixelOffset: [0, -18],
      pickable: true,
      onClick: pickRoute,
    }),
  ]
}

export function allRouteLayers(plan: Plan, selectedId: string, onSelect: (id: string) => void) {
  const ordered = [...plan.routes].sort(
    (a, b) => Number(a.id === selectedId) - Number(b.id === selectedId),
  )
  return ordered.flatMap((route) => routeLayers(route, route.id === selectedId, onSelect))
}

export function checkpointTooltip({ object, layer, viewport, x, y }: PickingInfo) {
  if (!object || !layer?.id.startsWith('checkpoints-')) return null
  const checkpoint = object as Checkpoint
  return {
    style: {
      ...TOOLTIP_STYLE,
      marginLeft: viewport && x > viewport.width - TOOLTIP_WIDTH ? `-${TOOLTIP_WIDTH}px` : '0',
      marginTop: viewport && y > viewport.height - TOOLTIP_HEIGHT ? `-${TOOLTIP_HEIGHT}px` : '0',
    },
    html: `
      <strong>${checkpoint.risk_label}</strong> at mile ${checkpoint.mile.toFixed(0)}<br/>
      ETA ${formatClock(checkpoint.eta)}<br/>
      Wind ${checkpoint.wind_mph.toFixed(0)} mph, gusts ${checkpoint.gust_mph.toFixed(0)}<br/>
      Rain ${checkpoint.rain_in_hr.toFixed(2)} in/hr, snow ${checkpoint.snow_in_hr.toFixed(2)} in/hr
    `,
  }
}
