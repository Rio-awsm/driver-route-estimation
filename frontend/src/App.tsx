import { useQuery } from '@tanstack/react-query'
import { checkHealth } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function App() {
  const health = useQuery({ queryKey: ['health'], queryFn: checkHealth, retry: false })

  return (
    <main className="flex min-h-dvh items-center justify-center bg-muted p-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Weather-Aware Truck Routing</CardTitle>
          <CardDescription>Frontend setup check</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          {health.isPending && <Badge variant="secondary">Checking API</Badge>}
          {health.isError && <Badge variant="destructive">API unreachable</Badge>}
          {health.isSuccess && <Badge>API connected</Badge>}
          <Button size="sm" onClick={() => health.refetch()}>
            Check again
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}
