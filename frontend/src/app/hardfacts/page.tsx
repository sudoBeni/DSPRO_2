"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Check, ChevronsUpDown } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import POSTAL_CODE_OPTIONS from "@/data/postal_codes.json"

export type HardFactsForm = {
  location: string
  min_rooms: string
  max_rent_chf: string
}

const ROOM_OPTIONS = ["1", "1.5", "2", "2.5", "3", "3.5", "4", "4.5+"]
const RENT_OPTIONS = ["1500", "2000", "2500", "3000", "3500", "4000", "5000+"]

const triggerClass =
  "h-11 w-full justify-between rounded-xl border border-neutral-300 bg-white px-3 text-sm font-normal shadow-none hover:bg-neutral-50"

export default function HardFactsPage() {
  const router = useRouter()

  const [openLocation, setOpenLocation] = useState(false)
  const [openRooms, setOpenRooms] = useState(false)
  const [openRent, setOpenRent] = useState(false)

  const [form, setForm] = useState<HardFactsForm>({
    location: "",
    min_rooms: "",
    max_rent_chf: "",
  })

  const [error, setError] = useState<string | null>(null)

  function updateField<K extends keyof HardFactsForm>(key: K, value: HardFactsForm[K]) {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  const isValid = useMemo(() => {
    return form.location.trim() !== ""
  }, [form])

  const isMaxRooms = form.min_rooms === "4.5+"
  const isMinRent = form.max_rent_chf === "1500"

  function handleContinue() {
    setError(null)

    if (!form.location.trim()) {
      setError("Please select a location.")
      return
    }

    const payload = {
      location: form.location,
      min_rooms: form.min_rooms ? Number(form.min_rooms.replace("+", "")) : undefined,
      max_rent_chf: form.max_rent_chf
        ? Number(form.max_rent_chf.replace("+", ""))
        : undefined,
    }

    sessionStorage.setItem("hardFacts", JSON.stringify(payload))
    router.push("/onboarding")
  }

  return (
    <main className="min-h-screen bg-white text-neutral-900">
      <div className="mx-auto flex min-h-screen w-full max-w-xl flex-col justify-center px-4 py-8">
        <div className="mb-8">
          <p className="text-sm text-neutral-500">Real Estate Recommender</p>
          <h1 className="text-3xl font-semibold">Start with a few basics</h1>
          <p className="mt-2 text-sm text-neutral-600">
            Tell us your location, budget and room preferences.
          </p>
        </div>

        <div className="space-y-5 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          {/* LOCATION */}
          <div className="grid gap-2">
            <label className="text-sm font-medium">Location</label>

            <Popover open={openLocation} onOpenChange={setOpenLocation}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className={`${triggerClass} ${
                    openLocation ? "border-neutral-400 bg-neutral-50" : ""
                  } ${!form.location ? "text-neutral-400" : "text-neutral-900"}`}
                >
                  <span className="truncate">
                    {form.location || "Select a location"}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>

              <PopoverContent
                align="start"
                className="w-[var(--radix-popover-trigger-width)] rounded-xl border-neutral-300 bg-neutral-50 p-0"
              >
                <Command className="bg-neutral-50">
                  <CommandInput placeholder="Search postal code or city..." />
                  <CommandList>
                    <CommandEmpty>No location found.</CommandEmpty>

                    <CommandGroup>
                      {POSTAL_CODE_OPTIONS.map((option) => (
                        <CommandItem
                          key={option}
                          value={option}
                          className="cursor-pointer data-[selected=true]:bg-neutral-200"
                          onSelect={(value) => {
                            updateField("location", value)
                            setOpenLocation(false)
                          }}
                        >
                          <Check
                            className={`mr-2 h-4 w-4 ${
                              form.location === option
                                ? "opacity-100"
                                : "opacity-0"
                            }`}
                          />
                          {option}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* MINIMUM ROOMS */}
          <div className="grid gap-2">
            <label className="text-sm font-medium">Minimum rooms</label>

            <Popover open={openRooms} onOpenChange={setOpenRooms}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className={`${triggerClass} ${
                    openRooms ? "border-neutral-400 bg-neutral-50" : ""
                  } ${!form.min_rooms ? "text-neutral-400" : "text-neutral-900"}`}
                >
                  <span>{form.min_rooms || "No preference"}</span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>

              <PopoverContent
                align="start"
                className="w-[var(--radix-popover-trigger-width)] rounded-xl border-neutral-300 bg-neutral-50 p-0"
              >
                <Command className="bg-neutral-50">
                  <CommandList>
                    <CommandGroup>
                      {form.min_rooms !== "" && (
                        <CommandItem
                          value="none"
                          className="cursor-pointer data-[selected=true]:bg-neutral-200"
                          onSelect={() => {
                            updateField("min_rooms", "")
                            setOpenRooms(false)
                          }}
                        >
                          <Check className="mr-2 h-4 w-4 opacity-0" />
                          No preference
                        </CommandItem>
                      )}

                      {ROOM_OPTIONS.map((option) => {
                        const disabled = isMinRent && option === "4.5+"
                        return (
                          <CommandItem
                            key={option}
                            value={option}
                            disabled={disabled}
                            className={`cursor-pointer data-[selected=true]:bg-neutral-200 ${disabled ? "opacity-30 cursor-not-allowed" : ""}`}
                            onSelect={(value) => {
                              if (disabled) return
                              updateField("min_rooms", value)
                              setOpenRooms(false)
                            }}
                          >
                            <Check
                              className={`mr-2 h-4 w-4 ${
                                form.min_rooms === option
                                  ? "opacity-100"
                                  : "opacity-0"
                              }`}
                            />
                            {option}
                          </CommandItem>
                        )
                      })}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* MAX RENT */}
          <div className="grid gap-2">
            <label className="text-sm font-medium">Maximum rent (CHF)</label>

            <Popover open={openRent} onOpenChange={setOpenRent}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className={`${triggerClass} ${
                    openRent ? "border-neutral-400 bg-neutral-50" : ""
                  } ${!form.max_rent_chf ? "text-neutral-400" : "text-neutral-900"}`}
                >
                  <span>
                    {form.max_rent_chf
                      ? `CHF ${form.max_rent_chf}`
                      : "No preference"}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>

              <PopoverContent
                align="start"
                className="w-[var(--radix-popover-trigger-width)] rounded-xl border-neutral-300 bg-neutral-50 p-0"
              >
                <Command className="bg-neutral-50">
                  <CommandList>
                    <CommandGroup>
                      {form.max_rent_chf !== "" && (
                        <CommandItem
                          value="none"
                          className="cursor-pointer data-[selected=true]:bg-neutral-200"
                          onSelect={() => {
                            updateField("max_rent_chf", "")
                            setOpenRent(false)
                          }}
                        >
                          <Check className="mr-2 h-4 w-4 opacity-0" />
                          No preference
                        </CommandItem>
                      )}

                      {RENT_OPTIONS.map((option) => {
                        const disabled = isMaxRooms && option === "1500"
                        return (
                          <CommandItem
                            key={option}
                            value={option}
                            disabled={disabled}
                            className={`cursor-pointer data-[selected=true]:bg-neutral-200 ${disabled ? "opacity-30 cursor-not-allowed" : ""}`}
                            onSelect={(value) => {
                              if (disabled) return
                              updateField("max_rent_chf", value)
                              setOpenRent(false)
                            }}
                          >
                            <Check
                              className={`mr-2 h-4 w-4 ${
                                form.max_rent_chf === option
                                  ? "opacity-100"
                                  : "opacity-0"
                              }`}
                            />
                            CHF {option}
                          </CommandItem>
                        )
                      })}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <Button
            onClick={handleContinue}
            disabled={!isValid}
            className="w-full rounded-2xl disabled:bg-neutral-200 disabled:text-neutral-500 enabled:bg-black enabled:text-white enabled:hover:bg-neutral-800"
          >
            Continue to style preferences
          </Button>
        </div>
      </div>
    </main>
  )
}