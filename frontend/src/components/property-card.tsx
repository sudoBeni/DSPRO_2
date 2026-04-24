"use client"

import Image from "next/image"
import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Property } from "@/types/property"
import { ChevronLeft, ChevronRight, Heart } from "lucide-react"

type Props = {
  property: Property
  onSave?: (id: string) => void
}

export function PropertyCard({ property, onSave }: Props) {
  const imageNames = property.image_names ?? []
  const [activeImageIndex, setActiveImageIndex] = useState(0)

  const hasMultipleImages = imageNames.length > 1
  const currentImage = imageNames[activeImageIndex]

  function showPreviousImage() {
    setActiveImageIndex((prev) => {
      if (imageNames.length === 0) return 0
      return prev === 0 ? imageNames.length - 1 : prev - 1
    })
  }

  function showNextImage() {
    setActiveImageIndex((prev) => {
      if (imageNames.length === 0) return 0
      return prev === imageNames.length - 1 ? 0 : prev + 1
    })
  }

  return (
    <Card className="overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow">

      {/* Image */}
      <div className="relative h-64 w-full">
        <Image
          src={currentImage ? `/data/images/${currentImage}` : "/placeholder.jpg"}
          alt={property.short_description || "Property image"}
          fill
          className="object-cover"
        />
        <Badge className="absolute top-3 left-3 bg-black/70 backdrop-blur">
          {property.match_score}% Match
        </Badge>
        {hasMultipleImages && (
          <>
            <Button
              type="button"
              size="icon-sm"
              variant="secondary"
              className="absolute left-3 top-1/2 size-9 -translate-y-1/2 rounded-full bg-white/85 text-neutral-900 shadow-md hover:bg-white"
              onClick={showPreviousImage}
              aria-label="Show previous image"
            >
              <ChevronLeft size={18} />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant="secondary"
              className="absolute right-3 top-1/2 size-9 -translate-y-1/2 rounded-full bg-white/85 text-neutral-900 shadow-md hover:bg-white"
              onClick={showNextImage}
              aria-label="Show next image"
            >
              <ChevronRight size={18} />
            </Button>
            <Badge className="absolute bottom-3 right-3 bg-black/70 backdrop-blur">
              {activeImageIndex + 1} / {imageNames.length}
            </Badge>
          </>
        )}
      </div>

      <CardContent className="p-5 space-y-3">

        {/* Title */}
        <h3 className="text-lg font-semibold leading-tight">
          {property.short_description || "Untitled Property"}
        </h3>

        {/* Price */}
        <p className="text-xl font-bold text-primary">
          {property.rent_chf}
        </p>

        {/* Meta info */}
        <div className="text-sm text-muted-foreground">
          {property.n_rooms}, {property.street}, {property.postal_code}
        </div>

        {/* AI explanation */}
        <div className="text-sm bg-muted p-3 rounded-lg">
          {property.source_url || "Recommended based on your preferences"}
        </div>

        {/* Actions */}
        <div className="flex justify-between items-center pt-2">
          <Button variant="outline" size="sm">
            Details
          </Button>

          <Button
            size="sm"
            onClick={() => onSave?.(property.object_id)}
            className="flex items-center gap-2"
          >
            <Heart size={16} />
            Save
          </Button>
        </div>

      </CardContent>
    </Card>
  )
}
