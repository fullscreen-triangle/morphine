import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import uuid
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    SINGLE_ANALYSIS = "single_analysis"      # One-time movement analysis
    PLAYER_PROFILE = "player_profile"        # Comprehensive player analysis
    TECHNIQUE_TEMPLATE = "technique_template" # Reusable technique framework
    PREDICTION_ENGINE = "prediction_engine"   # Validated prediction model

class ModelStatus(Enum):
    DRAFT = "draft"
    VALIDATION_PENDING = "validation_pending"
    VALIDATED = "validated"
    MARKETPLACE_READY = "marketplace_ready"
    DEPRECATED = "deprecated"

class ListingType(Enum):
    ONE_TIME_PURCHASE = "one_time_purchase"
    SUBSCRIPTION = "subscription"
    LICENSE = "license"
    RENT = "rent"

@dataclass
class BiomechanicalModel:
    """A user's biomechanical analysis model that can be monetized"""
    model_id: str
    creator_user_id: str
    model_type: ModelType
    status: ModelStatus
    
    # Model content
    title: str
    description: str
    movement_types: List[str]  # ["penalty_kick", "free_throw", etc.]
    analysis_data: Dict[str, Any]  # Core biomechanical insights
    
    # Validation metrics
    validation_count: int = 0
    success_rate: float = 0.0
    confidence_score: float = 0.0
    expert_endorsements: List[str] = None  # Expert user IDs who endorsed
    
    # Market data
    price: float = 0.0
    total_sales: int = 0
    total_revenue: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    
    # Metadata
    created_at: datetime = None
    updated_at: datetime = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.expert_endorsements is None:
            self.expert_endorsements = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []

@dataclass
class MarketplaceListing:
    """A model listing in the marketplace"""
    listing_id: str
    model_id: str
    seller_user_id: str
    listing_type: ListingType
    
    # Pricing
    base_price: float
    subscription_price: Optional[float] = None  # Monthly subscription
    license_terms: Optional[Dict[str, Any]] = None
    
    # Listing details
    featured: bool = False
    active: bool = True
    view_count: int = 0
    purchase_count: int = 0
    
    # Performance tracking
    conversion_rate: float = 0.0
    average_rating: float = 0.0
    
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ModelPurchase:
    """Record of a model purchase/license"""
    purchase_id: str
    buyer_user_id: str
    model_id: str
    seller_user_id: str
    listing_type: ListingType
    
    # Transaction details
    price_paid: float
    platform_fee: float
    seller_revenue: float
    
    # Access details
    access_granted_at: datetime
    access_expires_at: Optional[datetime] = None
    usage_count: int = 0
    
    # Feedback
    rating: Optional[float] = None
    review: Optional[str] = None
    
    def __post_init__(self):
        if self.access_granted_at is None:
            self.access_granted_at = datetime.now()

class ModelMarketplace:
    """
    Marketplace for buying, selling, and licensing biomechanical analysis models.
    Enables users to monetize expertise beyond just betting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Storage
        self.models: Dict[str, BiomechanicalModel] = {}
        self.listings: Dict[str, MarketplaceListing] = {}
        self.purchases: Dict[str, ModelPurchase] = {}
        
        # User data
        self.user_models: Dict[str, List[str]] = {}  # user_id -> model_ids
        self.user_purchases: Dict[str, List[str]] = {}  # user_id -> purchase_ids
        self.user_earnings: Dict[str, float] = {}  # user_id -> total_earnings
        
        # Platform settings
        self.platform_fee_rate = config.get("platform_fee_rate", 0.15)  # 15% platform fee
        self.min_validation_for_marketplace = config.get("min_validation_count", 3)
        self.min_success_rate_for_marketplace = config.get("min_success_rate", 0.6)
        
        logger.info("Model Marketplace initialized")
    
    async def create_model_from_session(self, 
                                      session_data: Dict[str, Any], 
                                      model_params: Dict[str, Any]) -> str:
        """
        Create a biomechanical model from a Spectacular analysis session.
        
        Args:
            session_data: Raw session data from Spectacular
            model_params: User-specified model parameters
            
        Returns:
            model_id of created model
        """
        try:
            model_id = f"model_{uuid.uuid4().hex[:12]}"
            
            # Extract biomechanical insights from session
            analysis_data = {
                "joint_sequence": session_data.get("clicked_joints", []),
                "muscle_activation": session_data.get("selected_muscles", []),
                "phase_breakdown": session_data.get("phase_annotations", {}),
                "force_patterns": session_data.get("force_vectors", []),
                "angle_relationships": session_data.get("angle_measurements", {}),
                "timing_patterns": session_data.get("timing_analysis", {}),
                "quality_indicators": session_data.get("technique_assessment", {}),
                "user_insights": session_data.get("user_observations", []),
                "reasoning_framework": session_data.get("reasoning", "")
            }
            
            # Create model
            model = BiomechanicalModel(
                model_id=model_id,
                creator_user_id=session_data["user_id"],
                model_type=ModelType(model_params.get("model_type", "single_analysis")),
                status=ModelStatus.DRAFT,
                title=model_params["title"],
                description=model_params["description"],
                movement_types=[session_data.get("movement_type", "unknown")],
                analysis_data=analysis_data,
                price=model_params.get("price", 0.0),
                tags=model_params.get("tags", [])
            )
            
            # Store model
            self.models[model_id] = model
            
            # Update user's model list
            user_id = session_data["user_id"]
            if user_id not in self.user_models:
                self.user_models[user_id] = []
            self.user_models[user_id].append(model_id)
            
            logger.info(f"Created model {model_id} from session {session_data['session_id']}")
            
            return model_id
            
        except Exception as e:
            logger.error(f"Error creating model from session: {e}")
            raise
    
    async def validate_model_with_prediction(self, 
                                           model_id: str, 
                                           prediction_success: bool,
                                           prediction_accuracy: float) -> bool:
        """
        Validate a model based on prediction success.
        
        Args:
            model_id: ID of model to validate
            prediction_success: Whether prediction was successful
            prediction_accuracy: Accuracy score of prediction
            
        Returns:
            True if model is now marketplace ready
        """
        try:
            if model_id not in self.models:
                logger.warning(f"Model {model_id} not found for validation")
                return False
            
            model = self.models[model_id]
            
            # Update validation metrics
            model.validation_count += 1
            
            # Calculate new success rate
            current_successes = model.success_rate * (model.validation_count - 1)
            if prediction_success:
                current_successes += 1
            
            model.success_rate = current_successes / model.validation_count
            
            # Update confidence score (weighted average)
            if model.confidence_score == 0:
                model.confidence_score = prediction_accuracy
            else:
                model.confidence_score = (
                    (model.confidence_score * 0.8) + (prediction_accuracy * 0.2)
                )
            
            # Check if ready for marketplace
            if (model.validation_count >= self.min_validation_for_marketplace and
                model.success_rate >= self.min_success_rate_for_marketplace):
                
                model.status = ModelStatus.MARKETPLACE_READY
                logger.info(f"Model {model_id} is now marketplace ready!")
                return True
            else:
                model.status = ModelStatus.VALIDATION_PENDING
                return False
            
        except Exception as e:
            logger.error(f"Error validating model: {e}")
            return False
    
    async def create_marketplace_listing(self, 
                                       model_id: str, 
                                       listing_params: Dict[str, Any]) -> str:
        """
        Create a marketplace listing for a validated model.
        
        Args:
            model_id: ID of model to list
            listing_params: Listing configuration
            
        Returns:
            listing_id of created listing
        """
        try:
            if model_id not in self.models:
                raise ValueError(f"Model {model_id} not found")
            
            model = self.models[model_id]
            
            if model.status != ModelStatus.MARKETPLACE_READY:
                raise ValueError(f"Model {model_id} not ready for marketplace")
            
            listing_id = f"listing_{uuid.uuid4().hex[:12]}"
            
            listing = MarketplaceListing(
                listing_id=listing_id,
                model_id=model_id,
                seller_user_id=model.creator_user_id,
                listing_type=ListingType(listing_params["listing_type"]),
                base_price=listing_params["base_price"],
                subscription_price=listing_params.get("subscription_price"),
                license_terms=listing_params.get("license_terms"),
                featured=listing_params.get("featured", False)
            )
            
            self.listings[listing_id] = listing
            
            logger.info(f"Created marketplace listing {listing_id} for model {model_id}")
            
            return listing_id
            
        except Exception as e:
            logger.error(f"Error creating marketplace listing: {e}")
            raise
    
    async def purchase_model(self, 
                           buyer_user_id: str, 
                           listing_id: str,
                           purchase_params: Dict[str, Any]) -> str:
        """
        Purchase or license a model from the marketplace.
        
        Args:
            buyer_user_id: ID of user making purchase
            listing_id: ID of listing being purchased
            purchase_params: Purchase configuration
            
        Returns:
            purchase_id of completed transaction
        """
        try:
            if listing_id not in self.listings:
                raise ValueError(f"Listing {listing_id} not found")
            
            listing = self.listings[listing_id]
            model = self.models[listing.model_id]
            
            if not listing.active:
                raise ValueError("Listing is not active")
            
            # Calculate pricing
            base_price = listing.base_price
            platform_fee = base_price * self.platform_fee_rate
            seller_revenue = base_price - platform_fee
            
            # Create purchase record
            purchase_id = f"purchase_{uuid.uuid4().hex[:12]}"
            
            # Set access expiration based on listing type
            access_expires_at = None
            if listing.listing_type == ListingType.SUBSCRIPTION:
                access_expires_at = datetime.now() + timedelta(days=30)
            elif listing.listing_type == ListingType.RENT:
                rental_days = purchase_params.get("rental_days", 7)
                access_expires_at = datetime.now() + timedelta(days=rental_days)
            
            purchase = ModelPurchase(
                purchase_id=purchase_id,
                buyer_user_id=buyer_user_id,
                model_id=listing.model_id,
                seller_user_id=listing.seller_user_id,
                listing_type=listing.listing_type,
                price_paid=base_price,
                platform_fee=platform_fee,
                seller_revenue=seller_revenue,
                access_granted_at=datetime.now(),
                access_expires_at=access_expires_at
            )
            
            # Store purchase
            self.purchases[purchase_id] = purchase
            
            # Update user purchase history
            if buyer_user_id not in self.user_purchases:
                self.user_purchases[buyer_user_id] = []
            self.user_purchases[buyer_user_id].append(purchase_id)
            
            # Update seller earnings
            if listing.seller_user_id not in self.user_earnings:
                self.user_earnings[listing.seller_user_id] = 0.0
            self.user_earnings[listing.seller_user_id] += seller_revenue
            
            # Update listing and model metrics
            listing.purchase_count += 1
            listing.conversion_rate = listing.purchase_count / max(1, listing.view_count)
            
            model.total_sales += 1
            model.total_revenue += seller_revenue
            
            logger.info(f"Completed purchase {purchase_id} for model {listing.model_id}")
            
            return purchase_id
            
        except Exception as e:
            logger.error(f"Error processing model purchase: {e}")
            raise
    
    async def get_marketplace_feed(self, 
                                 user_id: str, 
                                 filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get personalized marketplace feed for a user.
        
        Args:
            user_id: ID of user requesting feed
            filters: Optional filters for listings
            
        Returns:
            List of marketplace listings tailored to user
        """
        try:
            # Get all active listings
            active_listings = [
                listing for listing in self.listings.values()
                if listing.active and listing.seller_user_id != user_id
            ]
            
            # Apply filters if provided
            if filters:
                if "movement_types" in filters:
                    movement_types = set(filters["movement_types"])
                    active_listings = [
                        listing for listing in active_listings
                        if any(mt in movement_types for mt in self.models[listing.model_id].movement_types)
                    ]
                
                if "max_price" in filters:
                    max_price = filters["max_price"]
                    active_listings = [
                        listing for listing in active_listings
                        if listing.base_price <= max_price
                    ]
                
                if "min_rating" in filters:
                    min_rating = filters["min_rating"]
                    active_listings = [
                        listing for listing in active_listings
                        if self.models[listing.model_id].rating >= min_rating
                    ]
            
            # Sort by relevance (featured first, then by rating and sales)
            def listing_score(listing):
                model = self.models[listing.model_id]
                score = 0
                
                if listing.featured:
                    score += 1000
                
                score += model.rating * 100
                score += model.total_sales * 10
                score += model.success_rate * 50
                
                return score
            
            active_listings.sort(key=listing_score, reverse=True)
            
            # Format for response
            feed_items = []
            for listing in active_listings[:20]:  # Limit to top 20
                model = self.models[listing.model_id]
                
                feed_items.append({
                    "listing_id": listing.listing_id,
                    "model_id": listing.model_id,
                    "title": model.title,
                    "description": model.description,
                    "movement_types": model.movement_types,
                    "price": listing.base_price,
                    "listing_type": listing.listing_type.value,
                    "rating": model.rating,
                    "total_sales": model.total_sales,
                    "success_rate": model.success_rate,
                    "validation_count": model.validation_count,
                    "tags": model.tags,
                    "creator_expertise": await self._get_creator_expertise_level(model.creator_user_id)
                })
            
            return feed_items
            
        except Exception as e:
            logger.error(f"Error generating marketplace feed: {e}")
            return []
    
    async def get_user_model_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive view of user's model portfolio and earnings"""
        
        try:
            user_model_ids = self.user_models.get(user_id, [])
            user_models = [self.models[mid] for mid in user_model_ids if mid in self.models]
            
            # Calculate portfolio metrics
            total_models = len(user_models)
            marketplace_ready = len([m for m in user_models if m.status == ModelStatus.MARKETPLACE_READY])
            total_sales = sum(m.total_sales for m in user_models)
            total_revenue = self.user_earnings.get(user_id, 0.0)
            avg_rating = sum(m.rating for m in user_models if m.rating > 0) / max(1, len([m for m in user_models if m.rating > 0]))
            
            # Best performing model
            best_model = max(user_models, key=lambda m: m.total_revenue) if user_models else None
            
            # Recent activity
            recent_purchases = [
                self.purchases[pid] for pid in self.user_purchases.get(user_id, [])
                if self.purchases[pid].access_granted_at > datetime.now() - timedelta(days=30)
            ]
            
            return {
                "portfolio_summary": {
                    "total_models": total_models,
                    "marketplace_ready": marketplace_ready,
                    "total_sales": total_sales,
                    "total_revenue": total_revenue,
                    "average_rating": avg_rating
                },
                "models": [asdict(model) for model in user_models],
                "best_performing_model": asdict(best_model) if best_model else None,
                "recent_purchases": [asdict(purchase) for purchase in recent_purchases],
                "earnings_trend": await self._calculate_earnings_trend(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting user model portfolio: {e}")
            return {}
    
    async def _get_creator_expertise_level(self, user_id: str) -> float:
        """Calculate creator's expertise level based on model performance"""
        
        user_model_ids = self.user_models.get(user_id, [])
        if not user_model_ids:
            return 0.0
        
        user_models = [self.models[mid] for mid in user_model_ids if mid in self.models]
        
        # Weighted average of success rates, weighted by validation count
        total_weight = 0
        weighted_success = 0
        
        for model in user_models:
            if model.validation_count > 0:
                weight = min(model.validation_count, 10)  # Cap weight at 10
                weighted_success += model.success_rate * weight
                total_weight += weight
        
        return weighted_success / max(1, total_weight)
    
    async def _calculate_earnings_trend(self, user_id: str) -> List[Dict[str, Any]]:
        """Calculate earnings trend over the last 6 months"""
        
        # This would normally query a database for historical earnings
        # For now, return mock trend data
        
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        earnings = [120, 250, 180, 340, 290, 450]  # Mock data
        
        return [
            {"month": month, "earnings": earning}
            for month, earning in zip(months, earnings)
        ]
    
    async def suggest_model_improvements(self, model_id: str) -> Dict[str, Any]:
        """Suggest improvements to increase model marketability"""
        
        if model_id not in self.models:
            return {"error": "Model not found"}
        
        model = self.models[model_id]
        suggestions = []
        
        # Check validation count
        if model.validation_count < self.min_validation_for_marketplace:
            suggestions.append({
                "type": "validation",
                "message": f"Get {self.min_validation_for_marketplace - model.validation_count} more betting validations",
                "priority": "high"
            })
        
        # Check success rate
        if model.success_rate < self.min_success_rate_for_marketplace:
            suggestions.append({
                "type": "accuracy",
                "message": "Improve analysis accuracy to increase success rate",
                "priority": "high"
            })
        
        # Check description quality
        if len(model.description) < 100:
            suggestions.append({
                "type": "description",
                "message": "Add more detailed description to attract buyers",
                "priority": "medium"
            })
        
        # Check tags
        if len(model.tags) < 3:
            suggestions.append({
                "type": "tags",
                "message": "Add more relevant tags for better discoverability",
                "priority": "low"
            })
        
        return {
            "model_id": model_id,
            "current_status": model.status.value,
            "suggestions": suggestions,
            "marketplace_readiness": len([s for s in suggestions if s["priority"] == "high"]) == 0
        } 