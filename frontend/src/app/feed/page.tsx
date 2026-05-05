"use client"

import { useEffect, useState } from "react"
import { Property } from "@/types/property"
import { PropertyCard } from "@/components/property-card"
import { Button } from "@/components/ui/button"

type Ratings = Record<string, number>

export default function FeedPage() {
  const [recommendations, setRecommendations] = useState<Property[]>([])
  const [ratings, setRatings] = useState<Ratings>({})
  const [submitted, setSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      seed: session.seed ?? 42,
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
    return (
      <div className="max-w-xl mx-auto p-6 text-center space-y-4 pt-20">
        <h1 className="text-2xl font-bold">Thank you!</h1>
        <p className="text-muted-foreground">Your feedback has been recorded.</p>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">

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
