from datetime import datetime
from fastapi import APIRouter, Depends
from app.api.deps import require_maturity_stage
from app.core.database import get_traits_collection, get_users_collection
from app.models.trait import TraitListResponse, TraitResponse

router = APIRouter(prefix="/traits", tags=["traits"])

@router.get("/", response_model=TraitListResponse)
async def get_traits(current_user: dict = Depends(require_maturity_stage("extraction"))):
    """
    Returns the user's aggregated OCEAN traits based on extracted signals over time.
    Flags traits as an "early estimate" if the user hasn't reached the scoring maturity stage (first entry < 30 days ago).
    """
    user_id = current_user["user_id"]
    
    # Check if early estimate (less than 30 days since first entry)
    is_early_estimate = True
    users_col = get_users_collection()
    user_doc = await users_col.find_one({"user_id": user_id})
    if user_doc and "first_entry_at" in user_doc and user_doc["first_entry_at"]:
        days_elapsed = (datetime.utcnow() - user_doc["first_entry_at"]).days
        if days_elapsed >= 30:
            is_early_estimate = False
            
    traits_col = get_traits_collection()
    trait_doc = await traits_col.find_one({"user_id": user_id})
    
    response_traits = []
    
    if trait_doc and "categories" in trait_doc:
        categories = trait_doc["categories"]
        
        # Mapping OCEAN keys to full labels
        labels = {
            "O": "openness to experience",
            "C": "conscientiousness",
            "E": "extraversion",
            "A": "agreeableness",
            "N": "neuroticism"
        }
        
        for dim, stats in categories.items():
            high_count = stats.get("high_signals_count", 0)
            low_count = stats.get("low_signals_count", 0)
            total_count = high_count + low_count
            
            if total_count == 0:
                continue
                
            # Determine direction
            ratio = high_count / total_count
            if ratio >= 0.6:
                direction = "high"
            elif ratio <= 0.4:
                direction = "low"
            else:
                direction = "mixed"
                
            # Construct dynamic label
            label = f"{direction} {labels.get(dim, dim)}"
            if direction == "mixed":
                label = f"mixed signals for {labels.get(dim, dim)}"
                
            response_traits.append(
                TraitResponse(
                    label=label,
                    ocean_dimension=dim,
                    direction=direction,
                    confidence=stats.get("overall_confidence", 0.0),
                    signal_count=total_count
                )
            )
            
        # Sort by confidence descending
        response_traits.sort(key=lambda x: x.confidence, reverse=True)
        
    return TraitListResponse(traits=response_traits, is_early_estimate=is_early_estimate)


@router.post("/extract")
async def run_trait_extractor(current_user: dict = Depends(require_maturity_stage("extraction"))):
    """
    Manually triggers the trait extraction pipeline for the current user's unextracted entries.
    Useful for development/testing via the frontend UI.
    """
    user_id = current_user["user_id"]
    from app.services.synthesis.trait_extraction import process_trait_extractions
    
    # Run the extraction specifically for this user
    await process_trait_extractions(user_id=user_id)
    
    return {"message": f"Trait extraction triggered successfully for user {user_id}"}

