"use client"

import Image from "next/image"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Property } from "@/types/property"
import { Heart } from "lucide-react"

type Props = {
  property: Property
  onSave?: (id: string) => void
}

export function PropertyCard({ property, onSave }: Props) {
  return (
    <Card className="overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow">

      {/* Image */}
      <div className="relative h-64 w-full">
        <Image
          src={property.image_names?.[0] ? `/data/images/${property.image_names[0]}` : "/placeholder.jpg"}
          alt={property.short_description || "Property image"}
          fill
          className="object-cover"
        />
        <Badge className="absolute top-3 left-3 bg-black/70 backdrop-blur">
          {property.match_score}% Match
        </Badge>
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
