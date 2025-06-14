"""Utility functions for API v1 endpoints."""
from typing import Any, Union, Dict, List
from bson import ObjectId

def convert_objectid_to_str(doc: Any) -> Any:
    """Recursively convert ObjectId and other non-serializable types to string."""
    if isinstance(doc, ObjectId):
        return str(doc)
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            result[key] = convert_objectid_to_str(value)
        return result
    
    if isinstance(doc, list):
        return [convert_objectid_to_str(item) for item in doc]
    
    # Return as is for other types
    return doc
