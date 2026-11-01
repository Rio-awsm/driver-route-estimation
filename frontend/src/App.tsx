import { useMutation } from '@tanstack/react-query'
import { TriangleAlertIcon } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import { createPlan } from '@/api/client'
import { Legend } from '@/components/Legend'
import { RouteList } from '@/components/RouteList'
import { TripForm } from '@/components/TripForm'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const TripMap = lazy(() => import('@/map/TripMap'))

export default function App() {
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const planMutation = useMutation({
    mutationFn: createPlan,
    onSuccess: (plan) => setSelectedRouteId(plan.recommended_route),
  })

  return (
    <div className="grid h-dvh grid-rows-[1fr_40dvh] md:grid-cols-[400px_1fr] md:grid-rows-1">
      <aside className="flex flex-col gap-4 overflow-y-auto border-r p-4">
        <h1 className="font-heading text-lg font-semibold">Weather-Aware Truck Routing</h1>
        <TripForm busy={planMutation.isPending} onSubmit={planMutation.mutate} />
        {planMutation.isPending && (
          <p role="status" className="text-sm text-muted-foreground">
            Checking routes and forecasts. Long trips can take up to a minute.
          </p>
        )}
        {planMutation.isError && (
          <Alert variant="destructive">
            <TriangleAlertIcon />
            <AlertTitle>Could not plan this trip</AlertTitle>
            <AlertDescription>{planMutation.error.message}</AlertDescription>
          </Alert>
        )}
        {planMutation.data && (
          <RouteList
            plan={planMutation.data}
            selectedRouteId={selectedRouteId}
            onSelect={setSelectedRouteId}
          />
        )}
      </aside>
      <main className="relative min-h-0 bg-muted">
        <Suspense>
          <TripMap
            plan={planMutation.data ?? null}
            selectedRouteId={selectedRouteId}
            onSelectRoute={setSelectedRouteId}
          />
        </Suspense>
        <Legend />
      </main>
    </div>
  )
}
