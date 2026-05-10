"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Property } from "@/types/property"
import { PropertyCard } from "@/components/property-card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"

type Ratings = Record<string, number>

export default function FeedPage() {
  const router = useRouter()
  const [recommendations, setRecommendations] = useState<Property[]>([])
  const [ratings, setRatings] = useState<Ratings>({})
  const [submitted, setSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showIntro, setShowIntro] = useState(true)

  function handleDoAgain() {
    sessionStorage.clear()
    router.push("/hardfacts")
  }

  useEffect(() => {
    const stored = sessionStorage.getItem("recommendations")
    if (stored) {
      try {
        setRecommendations(JSON.parse(stored))
      } catch (e) {
        console.error("Failed to parse recommendations", e)
      }
    }
  }, [])

  function handleRate(objectId: string, rating: number) {
    setRatings((prev) => ({ ...prev, [objectId]: rating }))
  }

  async function handleSubmit() {
    const session = JSON.parse(sessionStorage.getItem("session") ?? "{}")
    const hardFacts = JSON.parse(sessionStorage.getItem("hardFacts") ?? "{}")
    const answers: Record<string, boolean> = JSON.parse(
      sessionStorage.getItem("onboardingAnswers") ?? "{}"
    )
    const cardIds: string[] = JSON.parse(
      sessionStorage.getItem("onboardingCardIds") ?? "[]"
    )

    const likedObjectIds = cardIds.filter((id) => answers[id] === true)
    const dislikedObjectIds = cardIds.filter((id) => answers[id] === false)
    const skippedObjectIds = cardIds.filter((id) => answers[id] === undefined)

    const ratingsList = recommendations.map((p, i) => ({
      position: i + 1,
      object_id: p.object_id,
      rating: ratings[p.object_id] ?? 0,
    }))

    const payload = {
      strategy: session.strategy ?? "gemini",
      hard_facts: hardFacts,
      liked_object_ids: likedObjectIds,
      disliked_object_ids: dislikedObjectIds,
      skipped_object_ids: skippedObjectIds,
      ratings: ratingsList,
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || ""
      const res = await fetch(`${apiUrl}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error("Failed to submit feedback")
      setSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setIsSubmitting(false)
    }
  }

  const ratedCount = recommendations.filter((p) => ratings[p.object_id] !== undefined).length
  const allRated = ratedCount === recommendations.length && recommendations.length > 0

  if (submitted) {
    const session = JSON.parse(sessionStorage.getItem("session") ?? "{}")
    const strategy: string = session.strategy ?? "unknown"
    return (
      <div className="max-w-xl mx-auto p-6 text-center space-y-4 pt-20">
        <h1 className="text-2xl font-bold">Thank you!</h1>
        <p className="text-muted-foreground">Your feedback has been recorded.</p>
        <p className="text-sm text-muted-foreground">
          Recommender used: <span className="font-mono font-medium text-foreground">{strategy}</span>
        </p>
        <Button onClick={handleDoAgain}>Do again</Button>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">
      <Dialog open={showIntro} onOpenChange={setShowIntro}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rate your recommendations</DialogTitle>
            <DialogDescription asChild>
              <div className="space-y-2 text-sm text-neutral-600">
                <p>Below are apartments selected just for you. Please rate each one to help us evaluate how well the recommender performed.</p>
                <p>The filters you set earlier define a minimum number of rooms and a maximum price. Please do not rate based on those. <strong>Focus on whether the style and feel of the apartment appeals to you.</strong></p>
                <p>Due to the small dataset, please also ignore the location when rating.</p>
                <p className="text-neutral-400 text-xs">Images are sourced from ImmoScout24 and shown exactly as they appear in the original listing.</p>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button className="w-full" onClick={() => setShowIntro(false)}>Got it, start rating</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Recommended for you</h1>
        <span className="text-sm text-muted-foreground">{ratedCount} / {recommendations.length} rated</span>
      </div>

      {recommendations.length === 0 && (
        <p className="text-sm text-muted-foreground">No recommendations found.</p>
      )}

      {recommendations.map((property, index) => (
        <PropertyCard
          key={`${property.object_id}-${index}`}
          property={property}
          rating={ratings[property.object_id]}
          onRate={(r) => handleRate(property.object_id, r)}
        />
      ))}

      {recommendations.length > 0 && (
        <div className="sticky bottom-6 pt-2">
          {error && <p className="text-sm text-destructive mb-2">{error}</p>}
          <Button
            className="w-full"
            disabled={!allRated || isSubmitting}
            onClick={handleSubmit}
          >
            {isSubmitting ? "Submitting…" : allRated ? "Submit Feedback" : `Rate all recommendations to submit (${ratedCount}/${recommendations.length})`}
          </Button>
        </div>
      )}

    </div>
  )
}
