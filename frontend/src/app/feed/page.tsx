"use client"

import { useState } from "react"
import { properties } from "@/data/mock-properties"
import { PropertyCard } from "@/components/property-card"

export default function FeedPage() {
  const [saved, setSaved] = useState<string[]>([])

  function handleSave(id: string) {
    setSaved([...saved, id])
  }

  return (
    <div className="max-w-xl mx-auto p-6 space-y-6">

      <h1 className="text-2xl font-bold">Recommended for you</h1>

      {properties.map((property) => (
        <PropertyCard
          key={property.id}
          property={property}
          onSave={handleSave}
        />
      ))}

    </div>
  )
}
