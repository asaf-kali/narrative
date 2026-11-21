import { useCallback, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

/** Converts one URL search param to a typed value and back. `parse` returns undefined for junk input. */
export interface Codec<T> {
  parse: (raw: string) => T | undefined
  format: (value: T) => string
}

type Codecs<S> = { [K in keyof S]: Codec<S[K]> }

export const stringParam: Codec<string> = { parse: (raw) => raw, format: (v) => v }

export const boolParam: Codec<boolean> = {
  parse: (raw) => (raw === 'true' ? true : raw === 'false' ? false : undefined),
  format: String,
}

export const intParam: Codec<number> = {
  parse: (raw) => (/^\d+$/.test(raw) ? Number(raw) : undefined),
  format: String,
}

export function enumParam<T extends string>(allowed: readonly T[]): Codec<T> {
  return { parse: (raw) => allowed.find((a) => a === raw), format: (v) => v }
}

function nonEmpty<T>(values: T[]): T[] | undefined {
  return values.length > 0 ? values : undefined
}

/** Comma-separated, sorted list (order is not state); `allowed` drops unknown entries. Empty falls back to the default. */
export function listParam<T extends string>(allowed?: readonly T[]): Codec<T[]> {
  return {
    parse: (raw) => nonEmpty(raw.split(',').filter((v): v is T => v !== '' && (!allowed || allowed.includes(v as T)))),
    format: (v) => [...v].sort().join(','),
  }
}

export const intListParam: Codec<number[]> = {
  parse: (raw) => nonEmpty(raw.split(',').filter((v) => /^\d+$/.test(v)).map(Number)),
  format: (v) => [...v].sort((a, b) => a - b).join(','),
}

/**
 * Page state stored in the URL query, so a refresh or a shared link restores it.
 * Values equal to their default are left out of the URL. Updates replace the history entry.
 */
export function useUrlState<S extends object>(defaults: S, codecs: Codecs<S>): [S, (patch: Partial<S>) => void] {
  const [searchParams, setSearchParams] = useSearchParams()
  // Several updates in one event must compose, so build each on the latest params, not this render's.
  const latest = useRef(searchParams)
  latest.current = searchParams

  const state = useMemo(() => {
    const result = { ...defaults }
    for (const key of Object.keys(codecs) as (keyof S)[]) {
      const raw = searchParams.get(String(key))
      const parsed = raw === null ? undefined : codecs[key].parse(raw)
      if (parsed !== undefined) result[key] = parsed
    }
    return result
  }, [searchParams, defaults, codecs])

  const update = useCallback((patch: Partial<S>) => {
    const next = new URLSearchParams(latest.current)
    for (const key of Object.keys(patch) as (keyof S)[]) {
      const codec = codecs[key]
      const formatted = codec.format(patch[key] as S[keyof S])
      if (formatted === codec.format(defaults[key])) next.delete(String(key))
      else next.set(String(key), formatted)
    }
    latest.current = next
    setSearchParams(next, { replace: true })
  }, [defaults, codecs, setSearchParams])

  return [state, update]
}
