"use client"

import Image from "next/image"
import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion } from "motion/react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { HardFactsForm } from "../hardfacts/page"

type AnswerMap = Record<string, boolean>

type OnboardingImageCard = {
  id: string
  label: string
  images: string[]
}

type SearchProfileRequest = {
  hard_facts: HardFactsForm
  liked_images: OnboardingImageCard[]
  disliked_images: OnboardingImageCard[]
  top_k: number
}

const SWIPE_THRESHOLD = 120
const TOTAL_ONBOARDING_CARDS = 10
const SUBMITTING_MESSAGES = ["Analyzing your taste…", "Processing your preferences…", "Looking for hidden gems…", "Finding your perfect apartments…", "One moment please…", "Double-checking the recommendations…"]

export default function OnboardingPage() {
  const router = useRouter()
  const [cards, setCards] = useState<OnboardingImageCard[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<AnswerMap>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [imageIndex, setImageIndex] = useState(0)
  const [allDisliked, setAllDisliked] = useState(false)
  const [msgIndex, setMsgIndex] = useState(0)
  const [loadKey, setLoadKey] = useState(0)
  const [showIntro, setShowIntro] = useState(true)

  useEffect(() => {
    setImageIndex(0)
  }, [index])

  useEffect(() => {
    if (!isSubmitting) return
    setMsgIndex(0)
    const interval = setInterval(() => {
      setMsgIndex((i) => (i + 1) % SUBMITTING_MESSAGES.length)
    }, 2500)
    return () => clearInterval(interval)
  }, [isSubmitting])

  const current = cards[index]
  const total = TOTAL_ONBOARDING_CARDS
  const progress = useMemo(() => {
    return ((index + 1) / total) * 100
  }, [index, total])

  function buildSearchPayload(nextAnswers: AnswerMap): SearchProfileRequest {
    const likedImages = cards.filter((card) => nextAnswers[card.id] === true)
    const dislikedImages = cards.filter((card) => nextAnswers[card.id] === false)
    const hardFacts = JSON.parse(sessionStorage.getItem("hardFacts") ?? "{}")

    return {
      hard_facts: hardFacts,
      liked_images: likedImages,
      disliked_images: dislikedImages,
      top_k: 10,
    }
  }

  async function submitSearch(nextAnswers: AnswerMap) {
    const hasLike = Object.values(nextAnswers).some((v) => v === true)
    if (!hasLike) {
      setAllDisliked(true)
      return
    }

    const session = JSON.parse(sessionStorage.getItem("session") ?? "{}")
    const payload = {
      ...buildSearchPayload(nextAnswers),
      strategy: session.strategy ?? "gemini",
    }

    sessionStorage.setItem("onboardingAnswers", JSON.stringify(nextAnswers))
    sessionStorage.setItem("onboardingCardIds", JSON.stringify(cards.map((c) => c.id)))

    setIsSubmitting(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || ""
      const res = await fetch(`${apiUrl}/api/recommendations/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!res.ok) throw new Error("Failed to create recommendations")

      const recommendations = await res.json()
      sessionStorage.setItem("recommendations", JSON.stringify(recommendations))
      router.push("/feed")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleAnswer(value: boolean) {
    if (!current || isSubmitting) return

    const nextAnswers = { ...answers, [current.id]: value }
    setAnswers(nextAnswers)

    const isLast = index === total - 1
    if (isLast) {
      void submitSearch(nextAnswers)
      return
    }

    setIndex((prev) => prev + 1)
  }

  function handleRestart() {
    setAllDisliked(false)
    setAnswers({})
    setIndex(0)
    sessionStorage.removeItem("onboardingCards")
    setLoadKey((k) => k + 1)
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setIsLoading(true)
        setError(null)

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || ""

        let session = JSON.parse(sessionStorage.getItem("session") ?? "null")
        if (!session) {
          const sessionRes = await fetch(`${apiUrl}/api/session`)
          session = await sessionRes.json()
          if (!cancelled) sessionStorage.setItem("session", JSON.stringify(session))
        }

        const cachedCards = sessionStorage.getItem("onboardingCards")
        if (cachedCards) {
          if (!cancelled) setCards(JSON.parse(cachedCards) as OnboardingImageCard[])
        } else {
          const res = await fetch(`${apiUrl}/api/recommendations/onboarding`)
          if (!res.ok) throw new Error("Failed to load onboarding cards")
          const fetchedCards: OnboardingImageCard[] = await res.json()
          if (!cancelled) {
            sessionStorage.setItem("onboardingCards", JSON.stringify(fetchedCards))
            setCards(fetchedCards)
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Something went wrong")
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void load()
    return () => { cancelled = true }
  }, [loadKey])

  if (isLoading || isSubmitting || (!current && !error && !allDisliked)) {
    return (
      <main className="min-h-screen bg-white text-neutral-900">
        <div className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center gap-6 px-4 py-6">
          <div className="relative h-16 w-16">
            <div className="absolute inset-0 animate-spin rounded-full border-4 border-neutral-200 border-t-neutral-900" />
          </div>
          <div className="text-center">
            <p className="text-base font-medium text-neutral-900">
              {isSubmitting ? SUBMITTING_MESSAGES[msgIndex] : "Loading onboarding images…"}
            </p>
            {isSubmitting && (
              <p className="mt-1 text-sm text-neutral-500">This may take a few seconds</p>
            )}
          </div>
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

  if (allDisliked) {
    return (
      <main className="min-h-screen bg-white text-neutral-900">
        <div className="mx-auto flex min-h-screen w-full max-w-md flex-col items-center justify-center gap-6 px-4 py-6 text-center">
          <h1 className="text-2xl font-semibold">Nothing caught your eye?</h1>
          <p className="text-sm text-neutral-500">
            We need at least one apartment you like to generate recommendations. Give it another try!
          </p>
          <Button className="rounded-2xl px-8" onClick={handleRestart}>
            Start over
          </Button>
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
      <Dialog open={showIntro} onOpenChange={setShowIntro}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>How this works</DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-2 text-sm text-neutral-600">
                <p>You'll be shown a series of apartment listings. Swipe <strong>right</strong> to like or <strong>left</strong> to dislike each one.</p>
                <p>These are randomly selected and do not take your filters into account. They are purely here to understand your visual taste.</p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button className="w-full" onClick={() => setShowIntro(false)}>Got it, let's go</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
          <div className="relative h-[70vh] w-full">
            <AnimatePresence mode="wait">
              <motion.div
                key={current.id}
                className="absolute inset-0 overflow-hidden rounded-3xl"
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.18}
                onDragEnd={(_, info) => {
                  if (isSubmitting) return

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
                  src={current.images[imageIndex]}
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

            {current.images.length > 1 && (
              <div className="pointer-events-none absolute bottom-20 left-0 right-0 z-10 flex items-center justify-center gap-3">
                <button
                  className="pointer-events-auto rounded-full bg-white/80 px-3 py-1 text-lg font-medium text-neutral-900 backdrop-blur disabled:opacity-30"
                  onClick={() => setImageIndex((i) => Math.max(0, i - 1))}
                  disabled={imageIndex === 0}
                >
                  ‹
                </button>
                <span className="rounded-full bg-white/80 px-2 py-1 text-xs text-neutral-600 backdrop-blur">
                  {imageIndex + 1} / {current.images.length}
                </span>
                <button
                  className="pointer-events-auto rounded-full bg-white/80 px-3 py-1 text-lg font-medium text-neutral-900 backdrop-blur disabled:opacity-30"
                  onClick={() => setImageIndex((i) => Math.min(current.images.length - 1, i + 1))}
                  disabled={imageIndex === current.images.length - 1}
                >
                  ›
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="mt-5 flex justify-between gap-3">
          <Button
            variant="outline"
            className="rounded-2xl border-neutral-300 bg-white text-neutral-900 hover:bg-neutral-100 flex-1"
            onClick={() => handleAnswer(false)}
            disabled={isSubmitting}
          >
            No
          </Button>

          <Button className="rounded-2xl flex-1" onClick={() => handleAnswer(true)} disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Yes"}
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
