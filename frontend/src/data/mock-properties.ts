import { Property } from "@/types/property"

const images = [
  "/train/Asian.jpg",
  "/train/Coastal.jpg",
  "/train/Contemporary Art.jpg",
  "/train/Craftsman.jpg",
  "/train/Eclectic.jpg",
  "/train/Farmhouse.jpg",
  "/train/Rustic.jpg",
]

export const properties: Property[] = images.map((image, index) => ({
  id: String(index + 1),
  title: `Property ${index + 1}`,
  city: ["Zurich", "Lucerne", "Geneva"][index % 3],
  price: 1000 + index * 500,
  rooms: 2 + index,
  area: 50 + index * 10,
  image,
  matchScore: 12, // Random score between 80-100
  reason:
    "Recommended because it matches your preferences for location and style."
}))
