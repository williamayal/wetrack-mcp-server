"""JSON utility functions."""
import re
import logging
from typing import List, Dict, Any
from datetime import datetime
from .date_utils import is_iso_date_string, parse_iso_date_string

logger = logging.getLogger(__name__)


def fix_isodate_in_json(json_str: str) -> str:
    """
    Fix ISODate() calls in JSON string by replacing them with ISO date strings.
    ISODate("2025-10-01T00:00:00Z") -> "2025-10-01T00:00:00Z"
    
    Args:
        json_str: JSON string that may contain ISODate() calls
        
    Returns:
        JSON string with ISODate() replaced by ISO date strings
    """
    # Pattern to match: ISODate("YYYY-MM-DDTHH:mm:ssZ") or ISODate("YYYY-MM-DDTHH:mm:ss.sssZ")
    pattern = r'ISODate\s*\(\s*"([^"]+)"\s*\)'
    
    def replace_isodate(match):
        date_string = match.group(1)
        # Return as JSON string value
        return f'"{date_string}"'
    
    # Replace all ISODate() calls
    fixed_json = re.sub(pattern, replace_isodate, json_str)
    return fixed_json


def fix_pipeline_dates(pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fix date filters in pipeline by converting ISO date strings to datetime objects.
    
    MongoDB stores createdAt as datetime objects, so we need to convert string dates
    from the LLM to datetime objects for proper comparison.
    
    Args:
        pipeline: MongoDB aggregation pipeline (may contain ISO date strings)
        
    Returns:
        Pipeline with ISO date strings converted to datetime objects
    """
    if not pipeline:
        return pipeline
    
    def convert_iso_strings_to_datetime(obj):
        """
        Recursively convert ISO date strings to datetime objects.
        MongoDB stores createdAt as datetime objects, so we need datetime objects for comparison.
        """
        from datetime import datetime as dt
        
        if isinstance(obj, dict):
            converted = {}
            for key, value in obj.items():
                # Check if this is a date comparison operator ($gte, $lte, $gt, $lt, $eq)
                if key in ["$gte", "$lte", "$gt", "$lt", "$eq", "$ne"]:
                    # If value is already a datetime object, keep it
                    if isinstance(value, dt):
                        converted[key] = value
                    # If value is a string that looks like an ISO date, convert to datetime
                    elif isinstance(value, str) and is_iso_date_string(value):
                        try:
                            converted[key] = parse_iso_date_string(value)
                        except Exception as e:
                            logger.warning(f"Failed to parse date string {value}: {e}")
                            converted[key] = value
                    # If value is a string that looks like a date (has space and colons), try to convert
                    elif isinstance(value, str) and (' ' in value and value.count(':') >= 2):
                        try:
                            # Check if it has timezone info (+HH:MM or -HH:MM or Z)
                            if '+' in value[-6:] or (value.endswith('Z')) or (value.count('-') > 2 and value.rfind('-') > 10):
                                # Has timezone, normalize and parse
                                normalized = value.replace(' ', 'T', 1) if 'T' not in value else value
                                if normalized.endswith('Z'):
                                    normalized = normalized[:-1] + '+00:00'
                                converted[key] = dt.fromisoformat(normalized)
                            else:
                                # No timezone, parse as naive datetime and assume UTC
                                date_part = value[:19] if len(value) >= 19 else value
                                converted[key] = dt.strptime(date_part, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
                        except Exception as e:
                            logger.warning(f"Failed to parse date string {value}: {e}")
                            converted[key] = value
                    else:
                        converted[key] = convert_iso_strings_to_datetime(value)
                # Check if this is a nested date filter (e.g., {"createdAt": {"$gte": "..."}})
                elif isinstance(value, dict) and any(op in value for op in ["$gte", "$lte", "$gt", "$lt", "$eq", "$ne"]):
                    converted[key] = convert_iso_strings_to_datetime(value)
                # Check if value is a string that might be a date
                elif isinstance(value, str) and (is_iso_date_string(value) or (len(value) == 19 and value[10] == ' ')):
                    try:
                        if is_iso_date_string(value):
                            converted[key] = parse_iso_date_string(value)
                        elif len(value) == 19 and value[10] == ' ':
                            converted[key] = dt.strptime(value, "%Y-%m-%d %H:%M:%S")
                        else:
                            converted[key] = value
                    except Exception as e:
                        logger.warning(f"Failed to parse date string {value}: {e}")
                        converted[key] = value
                else:
                    converted[key] = convert_iso_strings_to_datetime(value)
            return converted
        elif isinstance(obj, list):
            return [convert_iso_strings_to_datetime(item) for item in obj]
        else:
            return obj
    
    try:
        corrected_pipeline = convert_iso_strings_to_datetime(pipeline)
        logger.info(f"Pipeline date strings converted to datetime objects: {len(pipeline)} stages")
        return corrected_pipeline
    except Exception as e:
        logger.error(f"Failed to convert date strings in pipeline: {e}")
        return pipeline  # Return original if conversion fails

