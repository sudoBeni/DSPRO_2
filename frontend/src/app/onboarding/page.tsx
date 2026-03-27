"use client"

import Image from "next/image"
import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion } from "motion/react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

type AnswerMap = Record<string, boolean>

type OnboardingImageCard = {
  id: string
  label: string
  base64: string
}

const SWIPE_THRESHOLD = 120

export default function OnboardingPage() {
  const router = useRouter()
  const [cards, setCards] = useState<OnboardingImageCard[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<AnswerMap>({})

  const current = cards[index]
  const total = cards.length
  const progress = useMemo(() => {
    if (total === 0) return 0
    return ((index + 1) / total) * 100
  }, [index, total])

  function handleAnswer(value: boolean) {
    if (!current) return

    const nextAnswers = {
      ...answers,
      [current.id]: value,
    }

    setAnswers(nextAnswers)

    const isLast = index === total - 1
    if (isLast) {
      sessionStorage.setItem("onboardingAnswers", JSON.stringify(nextAnswers))
      router.push("/feed")
      return
    }

    setIndex((prev) => prev + 1)
  }

  function handleSkip() {
    if (!current) return

    const isLast = index === total - 1
    if (isLast) {
      sessionStorage.setItem("onboardingAnswers", JSON.stringify(answers))
      router.push("/feed")
      return
    }

    setIndex((prev) => prev + 1)
  }

  useEffect(() => {
    async function loadOnboardingCards() {
      try {
        setIsLoading(true)
        setError(null)

        const res = await fetch("http://localhost:8000/api/recommendations/onboarding")

        if (!res.ok) {
          throw new Error("Failed to load onboarding cards")
        }

        const data: OnboardingImageCard[] = await res.json()
        setCards(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong")
      } finally {
        setIsLoading(false)
      }
    }

    loadOnboardingCards()
  }, [])

  if (isLoading) {
    return (
      <main className="min-h-screen bg-white text-neutral-900">
        <div className="mx-auto flex min-h-screen w-full max-w-md items-center justify-center px-4 py-6">
          <p className="text-sm text-neutral-500">Loading onboarding images...</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen bg-white text-neutral-900">
        <div className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center gap-4 px-4 py-6 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <Button onClick={() => window.location.reload()}>Try again</Button>
        </div>
      </main>
    )
  }

  if (!current) {
    return (
      <main className="min-h-screen bg-white text-neutral-900">
        <div className="mx-auto flex min-h-screen w-full max-w-md items-center justify-center px-4 py-6">
          <p className="text-sm text-neutral-500">No onboarding images available.</p>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-white text-neutral-900">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col px-4 py-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="text-sm text-neutral-500">Style onboarding</p>
            <h1 className="text-2xl font-semibold">What do you like?</h1>
          </div>
          <Badge variant="secondary" className="rounded-full">
            {index + 1} / {total}
          </Badge>
        </div>

        <div className="mb-5 h-2 w-full overflow-hidden rounded-full bg-neutral-200">
          <div
            className="h-full rounded-full bg-neutral-900 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="relative flex flex-1 items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={current.id}
              className="relative h-[70vh] w-full overflow-hidden rounded-3xl"
              drag="x"
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.18}
              onDragEnd={(_, info) => {
                if (info.offset.x > SWIPE_THRESHOLD) {
                  handleAnswer(true)
                } else if (info.offset.x < -SWIPE_THRESHOLD) {
                  handleAnswer(false)
                }
              }}
              initial={{ opacity: 0, scale: 0.96, y: 18 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.22 }}
              whileDrag={{ rotate: 8, scale: 1.02 }}
            >
              <Image
                src={current.base64}
                alt={current.label}
                fill
                priority
                className="object-cover"
              />

              <div className="absolute inset-0 bg-gradient-to-t from-white/30 via-white/10 to-transparent" />

              <div className="absolute left-4 top-4">
                <Badge className="rounded-full border border-neutral-200 bg-white/80 text-neutral-900 backdrop-blur">
                  Swipe right if you like it
                </Badge>
              </div>

              <div className="absolute bottom-0 left-0 right-0 p-5">
                <p className="text-sm uppercase tracking-[0.2em] text-neutral-600">
                  Style preference
                </p>
                <h2 className="mt-2 text-3xl font-semibold text-neutral-900">{current.label}</h2>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-3">
          <Button
            variant="outline"
            className="rounded-2xl border-neutral-300 bg-white text-neutral-900 hover:bg-neutral-100"
            onClick={() => handleAnswer(false)}
          >
            No
          </Button>

          <Button
            variant="ghost"
            className="rounded-2xl text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
            onClick={handleSkip}
          >
            Skip
          </Button>

          <Button className="rounded-2xl" onClick={() => handleAnswer(true)}>
            Yes
          </Button>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-neutral-600">
          <span>Left = dislike</span>
          <span>Right = like</span>
        </div>
      </div>
    </main>
  )
}
