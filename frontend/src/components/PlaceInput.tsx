import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronsUpDownIcon } from 'lucide-react'
import { useState } from 'react'
import { searchPlaces } from '@/api/client'
import type { Place } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Field, FieldLabel } from '@/components/ui/field'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useDebounced } from '@/lib/use-debounced'

const DEBOUNCE_MS = 250
const MIN_CHARS = 3

type Props = {
  id: string
  label: string
  value: Place | null
  onChange: (place: Place) => void
}

export function PlaceInput({ id, label, value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const term = useDebounced(query.trim(), DEBOUNCE_MS)
  const search = useQuery({
    queryKey: ['places', term],
    queryFn: ({ signal }) => searchPlaces(term, signal),
    enabled: term.length >= MIN_CHARS,
    placeholderData: keepPreviousData,
    retry: false,
  })
  const longEnough = query.trim().length >= MIN_CHARS
  const places = longEnough ? (search.data ?? []) : []

  function emptyMessage() {
    if (!longEnough) return `Type at least ${MIN_CHARS} letters`
    if (search.isError) return 'Address search is unavailable'
    if (search.isFetching || term !== query.trim()) return 'Searching…'
    return 'No places found'
  }

  function choose(place: Place) {
    onChange(place)
    setQuery('')
    setOpen(false)
  }

  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between font-normal"
          >
            <span className={value ? 'truncate' : 'truncate text-muted-foreground'}>
              {value?.label ?? 'City or address'}
            </span>
            <ChevronsUpDownIcon className="opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput placeholder="Search places" value={query} onValueChange={setQuery} />
            <CommandList>
              <CommandEmpty>{emptyMessage()}</CommandEmpty>
              {places.map((place) => (
                <CommandItem
                  key={`${place.lat},${place.lon}`}
                  value={`${place.lat},${place.lon}`}
                  onSelect={() => choose(place)}
                >
                  {place.label}
                </CommandItem>
              ))}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </Field>
  )
}
