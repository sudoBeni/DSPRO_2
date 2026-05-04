from .fuzzy_cluster import FuzzyClusterRecommender
from .k_nearest import KNearestRecommender
from .schemas import RatedItem, RecommendationResult
from .weighted_vector import WeightedVectorRecommender

__all__ = [
    "RatedItem",
    "RecommendationResult",
    "KNearestRecommender",
    "WeightedVectorRecommender",
    "FuzzyClusterRecommender",
]
