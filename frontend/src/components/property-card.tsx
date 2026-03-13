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
          src={property.image}
          alt={property.title}
          fill
          className="object-cover"
        />

        {/* Match score */}
        <Badge className="absolute top-3 left-3 bg-black/70 backdrop-blur">
          {property.matchScore}% Match
        </Badge>
      </div>

      <CardContent className="p-5 space-y-3">

        {/* Title */}
        <h3 className="text-lg font-semibold leading-tight">
          {property.title}
        </h3>

        {/* Price */}
        <p className="text-xl font-bold text-primary">
          CHF {property.price.toLocaleString()}
        </p>

        {/* Meta info */}
        <div className="text-sm text-muted-foreground">
          {property.rooms} rooms • {property.area} m² • {property.city}
        </div>

        {/* AI explanation */}
        <div className="text-sm bg-muted p-3 rounded-lg">
          {property.reason}
        </div>

        {/* Actions */}
        <div className="flex justify-between items-center pt-2">
          <Button variant="outline" size="sm">
            Details
          </Button>

          <Button
            size="sm"
            onClick={() => onSave?.(property.id)}
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
