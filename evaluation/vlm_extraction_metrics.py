"""
VLM Extraction Metrics Framework

Custom metrics for evaluating Vision LLM blueprint extraction quality.
Similar to RAGAS pattern but tailored for structured data extraction.

Metrics:
- Area Accuracy: MAPE-based accuracy for room areas
- Recall: Percentage of ground truth rooms found
- Precision: Percentage of extracted rooms that are valid
- Type Match Rate: Percentage of rooms with matching types
- Name Match Rate: Percentage of rooms with matching names (fuzzy)
- Semantic Understanding Score: Heuristic for semantic reasoning quality
- Confidence Calibration: Correlation between confidence scores and actual accuracy
- Composite Score: Weighted combination of all metrics
"""

from typing import List, Tuple, Dict, Any, Optional
from rapidfuzz import fuzz, process
from app.models.domain import Room, BlueprintExtractionResult


# Matching threshold for fuzzy string matching (0-100)
FUZZY_MATCH_THRESHOLD = 85  # 85% similarity required for match


def match_rooms(
    extracted: List[Room], 
    ground_truth: List[Room],
    fuzzy_threshold: int = FUZZY_MATCH_THRESHOLD
) -> Tuple[List[Tuple[Room, Room]], List[Room], List[Room]]:
    """
    Match extracted rooms to ground truth rooms by name using fuzzy matching.
    
    Uses rapidfuzz for fuzzy string matching to handle variations like:
    - "Office / Bedroom" vs "Office/Bedroom" (space vs slash)
    - "T & B" vs "T&B" (spaces)
    - Minor spelling differences
    
    Args:
        extracted: List of extracted Room objects
        ground_truth: List of ground truth Room objects
        fuzzy_threshold: Minimum similarity score (0-100) for fuzzy match
        
    Returns:
        Tuple of:
        - matched_pairs: List of (extracted_room, ground_truth_room) tuples
        - unmatched_extracted: List of extracted rooms that couldn't be matched
        - unmatched_ground_truth: List of ground truth rooms that weren't found
    """
    matched_pairs = []
    unmatched_extracted = []
    unmatched_ground_truth = list(ground_truth)  # Start with all, remove as matched
    
    # Create lookup for exact matches first (faster)
    ground_truth_by_name_exact = {
        r.name.lower().strip(): r for r in ground_truth
    }
    
    # Track which ground truth rooms have been matched
    matched_gt_indices = set()
    
    # First pass: Try exact matches (case-insensitive, trimmed)
    for ext_room in extracted:
        ext_name_lower = ext_room.name.lower().strip()
        
        if ext_name_lower in ground_truth_by_name_exact:
            gt_room = ground_truth_by_name_exact[ext_name_lower]
            matched_pairs.append((ext_room, gt_room))
            matched_gt_indices.add(id(gt_room))
        else:
            unmatched_extracted.append(ext_room)
    
    # Second pass: Try fuzzy matching for unmatched extracted rooms
    # Only consider ground truth rooms that haven't been matched yet
    unmatched_gt_for_fuzzy = [
        gt for gt in unmatched_ground_truth 
        if id(gt) not in matched_gt_indices
    ]
    
    if unmatched_gt_for_fuzzy and unmatched_extracted:
        # Build list of unmatched extracted for fuzzy matching
        fuzzy_unmatched_extracted = []
        fuzzy_unmatched_indices = []
        
        for idx, ext_room in enumerate(unmatched_extracted):
            # Try fuzzy match
            best_match = process.extractOne(
                ext_room.name,
                [gt.name for gt in unmatched_gt_for_fuzzy],
                scorer=fuzz.ratio,
                score_cutoff=fuzzy_threshold
            )
            
            if best_match:
                # Find the corresponding ground truth room
                matched_gt_name = best_match[0]
                matched_gt_room = next(
                    gt for gt in unmatched_gt_for_fuzzy 
                    if gt.name == matched_gt_name
                )
                
                matched_pairs.append((ext_room, matched_gt_room))
                matched_gt_indices.add(id(matched_gt_room))
            else:
                fuzzy_unmatched_extracted.append(ext_room)
                fuzzy_unmatched_indices.append(idx)
        
        unmatched_extracted = fuzzy_unmatched_extracted
    
    # Update unmatched_ground_truth to only include truly unmatched rooms
    unmatched_ground_truth = [
        gt for gt in ground_truth 
        if id(gt) not in matched_gt_indices
    ]
    
    return matched_pairs, unmatched_extracted, unmatched_ground_truth


def calculate_area_accuracy(
    extracted_rooms: List[Room], 
    ground_truth_rooms: List[Room]
) -> float:
    """
    Calculate area accuracy using Mean Absolute Percentage Error (MAPE).
    
    Matches rooms first, then calculates MAPE for matched rooms.
    Returns accuracy score: 1.0 - MAPE (clamped to [0, 1]).
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        
    Returns:
        Area accuracy score (0.0 to 1.0, where 1.0 is perfect)
    """
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    
    if not matched_pairs:
        return 0.0
    
    # Calculate MAPE for matched rooms
    percentage_errors = []
    for ext_room, gt_room in matched_pairs:
        if gt_room.area_m2 > 0:
            error_pct = abs(ext_room.area_m2 - gt_room.area_m2) / gt_room.area_m2
            percentage_errors.append(error_pct)
    
    if not percentage_errors:
        return 0.0
    
    mape = sum(percentage_errors) / len(percentage_errors)
    
    # Convert MAPE to accuracy: accuracy = 1.0 - MAPE (clamped to [0, 1])
    accuracy = max(0.0, min(1.0, 1.0 - mape))
    
    return accuracy


def calculate_recall(
    extracted_rooms: List[Room], 
    ground_truth_rooms: List[Room]
) -> float:
    """
    Calculate recall: percentage of ground truth rooms that were found.
    
    Formula: matched_rooms / total_ground_truth_rooms
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        
    Returns:
        Recall score (0.0 to 1.0)
    """
    if not ground_truth_rooms:
        return 0.0
    
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    matched_count = len(matched_pairs)
    
    return matched_count / len(ground_truth_rooms)


def calculate_precision(
    extracted_rooms: List[Room], 
    ground_truth_rooms: List[Room]
) -> float:
    """
    Calculate precision: percentage of extracted rooms that are valid (match ground truth).
    
    Formula: matched_rooms / total_extracted_rooms
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        
    Returns:
        Precision score (0.0 to 1.0)
    """
    if not extracted_rooms:
        return 0.0
    
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    matched_count = len(matched_pairs)
    
    return matched_count / len(extracted_rooms)


def calculate_type_match_rate(
    extracted_rooms: List[Room], 
    ground_truth_rooms: List[Room]
) -> float:
    """
    Calculate type match rate: percentage of matched rooms with matching types.
    
    Only considers matched rooms. Compares room.type field.
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        
    Returns:
        Type match rate (0.0 to 1.0)
    """
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    
    if not matched_pairs:
        return 0.0
    
    type_matches = sum(
        1 for ext_room, gt_room in matched_pairs 
        if ext_room.type == gt_room.type
    )
    
    return type_matches / len(matched_pairs)


def calculate_name_match_rate(
    extracted_rooms: List[Room], 
    ground_truth_rooms: List[Room]
) -> float:
    """
    Calculate name match rate: percentage of ground truth rooms with matching names.
    
    Uses fuzzy matching, so minor variations are still considered matches.
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        
    Returns:
        Name match rate (0.0 to 1.0)
    """
    if not ground_truth_rooms:
        return 0.0
    
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    matched_count = len(matched_pairs)
    
    return matched_count / len(ground_truth_rooms)


def calculate_semantic_understanding_score(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult
) -> float:
    """
    Evaluate if LLM used semantic understanding vs just text extraction.
    
    Heuristic-based score that measures:
    1. Type classification accuracy (semantic reasoning)
    2. Reasonable type assignments (not all "other")
    3. Structured output quality (valid Room models)
    
    Semantic extraction should:
    - Classify rooms into meaningful types (bedroom, living, etc.)
    - Not default to "other" for most rooms
    - Produce structured, valid output
    
    Text-only extraction would:
    - Miss type classification
    - Default to "other" frequently
    - Have lower type confidence scores
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        extraction_result: BlueprintExtractionResult with confidence scores
        
    Returns:
        Semantic understanding score (0.0 to 1.0)-
    """
    if not extracted_rooms:
        return 0.0
    
    # Factor 1: Type classification quality (40% weight)
    # Penalize "other" types (indicates LLM couldn't classify)
    other_type_count = sum(1 for r in extracted_rooms if r.type == "other")
    other_type_ratio = other_type_count / len(extracted_rooms)
    type_quality_score = 1.0 - (other_type_ratio * 0.5)  # Max 50% penalty
    
    # Factor 2: Type match rate for matched rooms (30% weight)
    type_match_rate = calculate_type_match_rate(extracted_rooms, ground_truth_rooms)
    
    # Factor 3: Type confidence from extraction (20% weight)
    type_confidence = extraction_result.confidence.type_confidence
    
    # Factor 4: Overall confidence (10% weight)
    overall_confidence = extraction_result.confidence.overall
    
    # Weighted combination
    semantic_score = (
        type_quality_score * 0.4 +
        type_match_rate * 0.3 +
        type_confidence * 0.2 +
        overall_confidence * 0.1
    )
    
    return max(0.0, min(1.0, semantic_score))


def calculate_confidence_calibration(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult
) -> float:
    """
    Measure how well confidence scores correlate with actual accuracy.
    
    Compares ExtractionConfidence scores to actual extraction errors.
    Uses a simple correlation: if confidence is high, accuracy should be high.
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        extraction_result: BlueprintExtractionResult with confidence scores
        
    Returns:
        Calibration score (0.0 to 1.0, where 1.0 is perfectly calibrated)
    """
    # Calculate actual accuracy metrics
    recall = calculate_recall(extracted_rooms, ground_truth_rooms)
    precision = calculate_precision(extracted_rooms, ground_truth_rooms)
    area_accuracy = calculate_area_accuracy(extracted_rooms, ground_truth_rooms)
    type_match_rate = calculate_type_match_rate(extracted_rooms, ground_truth_rooms)
    
    # Average of actual metrics (overall accuracy)
    actual_accuracy = (recall + precision + area_accuracy + type_match_rate) / 4.0
    
    # Predicted accuracy (from confidence scores)
    predicted_accuracy = extraction_result.confidence.overall
    
    # Calibration error: difference between predicted and actual
    calibration_error = abs(predicted_accuracy - actual_accuracy)
    
    # Convert to score: 1.0 - error (clamped to [0, 1])
    # Perfect calibration (error = 0) → score = 1.0
    # Large error (error = 1.0) → score = 0.0
    calibration_score = max(0.0, min(1.0, 1.0 - calibration_error))
    
    return calibration_score


def calculate_composite_score(
    metrics: Dict[str, float],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate weighted composite score for model comparison.
    
    Default weights:
    - area_accuracy: 25%
    - recall: 20%
    - precision: 20%
    - type_match_rate: 15%
    - semantic_understanding_score: 10%
    - confidence_calibration: 5%
    - name_match_rate: 5% (optional, can be included)
    
    Args:
        metrics: Dictionary of metric names to scores
        weights: Optional custom weights (must sum to 1.0)
        
    Returns:
        Composite score (0.0 to 1.0)
    """
    default_weights = {
        "area_accuracy": 0.25,
        "recall": 0.20,
        "precision": 0.20,
        "type_match_rate": 0.15,
        "semantic_understanding_score": 0.10,
        "confidence_calibration": 0.05,
        "name_match_rate": 0.05,
    }
    
    if weights is None:
        weights = default_weights
    
    # Normalize weights to sum to 1.0
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights.items()}
    
    # Calculate weighted sum
    composite = 0.0
    for metric_name, weight in weights.items():
        if metric_name in metrics:
            composite += metrics[metric_name] * weight
    
    return max(0.0, min(1.0, composite))


def calculate_all_metrics(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult,
    include_latency: bool = False,
    latency_seconds: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate all metrics for a single extraction.
    
    Convenience function that computes all metrics at once.
    
    Args:
        extracted_rooms: List of extracted Room objects
        ground_truth_rooms: List of ground truth Room objects
        extraction_result: BlueprintExtractionResult with confidence scores
        include_latency: Whether to include latency in metrics
        latency_seconds: Optional latency in seconds (for latency score calculation)
        
    Returns:
        Dictionary of all metric scores
    """
    metrics = {
        "area_accuracy": calculate_area_accuracy(extracted_rooms, ground_truth_rooms),
        "recall": calculate_recall(extracted_rooms, ground_truth_rooms),
        "precision": calculate_precision(extracted_rooms, ground_truth_rooms),
        "type_match_rate": calculate_type_match_rate(extracted_rooms, ground_truth_rooms),
        "name_match_rate": calculate_name_match_rate(extracted_rooms, ground_truth_rooms),
        "semantic_understanding_score": calculate_semantic_understanding_score(
            extracted_rooms, ground_truth_rooms, extraction_result
        ),
        "confidence_calibration": calculate_confidence_calibration(
            extracted_rooms, ground_truth_rooms, extraction_result
        ),
    }
    
    # Add latency score if requested (normalized: lower latency = higher score)
    if include_latency and latency_seconds is not None:
        # Normalize latency: assume 30s is "slow" (score = 0), 5s is "fast" (score = 1)
        # Linear interpolation between 5s and 30s
        latency_score = max(0.0, min(1.0, 1.0 - (latency_seconds - 5.0) / 25.0))
        metrics["latency_score"] = latency_score
        metrics["latency_seconds"] = latency_seconds
    
    # Calculate composite score
    metrics["composite_score"] = calculate_composite_score(metrics)
    
    return metrics
