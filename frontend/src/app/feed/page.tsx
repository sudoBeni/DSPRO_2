"use client"

import { useEffect, useState } from "react"
import { Property } from "@/types/property"
import { PropertyCard } from "@/components/property-card"

export default function FeedPage() {
  const [saved, setSaved] = useState<string[]>([])
  const [recommendations, setRecommendations] = useState<Property[]>([])

  useEffect(() => {
    const stored = sessionStorage.getItem("recommendations")
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        setRecommendations(parsed)
      } catch (e) {
        console.error("Failed to parse recommendations", e)
      }
    }
  }, [])

  function handleSave(id: string) {
    setSaved([...saved, id])
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">

      <h1 className="text-2xl font-bold">Recommended for you</h1>

      {recommendations.length === 0 && (
        <p className="text-sm text-muted-foreground">No recommendations found.</p>
      )}
      {recommendations.map((property) => (
        <PropertyCard
          key={property.object_id}
          property={property}
          onSave={handleSave}
        />
      ))}

    </div>
  )
}
