"""
Router for ML-based anomaly detection endpoints.

Provides manual trigger for ML detection and status information.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from internal.auth.jwt import get_current_user
from internal.ml.ml_detector import get_ml_service
from models.models import TokenData

router = APIRouter()


class MLDetectionStatus(BaseModel):
    """Status of ML detection service"""
    initialized: bool
    model_loaded: bool
    model_type: str | None = None
    features_count: int | None = None
    trained_at: str | None = None


class MLDetectionResponse(BaseModel):
    """Response from manual ML detection trigger"""
    success: bool
    message: str
    alerts_generated: int | None = None


@router.get("/ml/status", response_model=MLDetectionStatus)
async def get_ml_status(current_user: TokenData = Depends(get_current_user)):
    """
    Get the status of the ML detection service.
    
    Returns information about whether the model is loaded and ready.
    """
    service = get_ml_service()
    
    if not service:
        return MLDetectionStatus(
            initialized=False,
            model_loaded=False
        )
    
    if not service.detector:
        return MLDetectionStatus(
            initialized=True,
            model_loaded=False
        )
    
    model_info = service.detector.get_model_info()
    
    return MLDetectionStatus(
        initialized=True,
        model_loaded=True,
        model_type=model_info.get('model_type'),
        features_count=model_info.get('n_features'),
        trained_at=model_info.get('trained_at')
    )


@router.post("/ml/detect", response_model=MLDetectionResponse)
async def trigger_ml_detection(current_user: TokenData = Depends(get_current_user)):
    """
    Manually trigger ML anomaly detection for all active devices.
    
    This endpoint allows administrators to immediately run the ML detection
    cycle instead of waiting for the scheduled background task.
    
    Requires authentication.
    """
    service = get_ml_service()
    
    if not service:
        raise HTTPException(
            status_code=503,
            detail="ML detection service not initialized"
        )
    
    if not service.detector:
        raise HTTPException(
            status_code=503,
            detail="ML model not loaded. Please check server logs."
        )
    
    try:
        # Run detection cycle
        await service.run_detection_cycle()
        
        return MLDetectionResponse(
            success=True,
            message="ML detection completed successfully",
            alerts_generated=None  # Could track this if needed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ML detection failed: {str(e)}"
        )
