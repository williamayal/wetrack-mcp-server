"""Service for MongoDB operations."""
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)


class MongoService:
    """Service for interacting with MongoDB."""
    
    def __init__(self):
        """Initialize MongoDB connection."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_database]
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def execute_pipeline(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute an aggregation pipeline on the MongoDB view.
        
        Args:
            pipeline: MongoDB aggregation pipeline
            
        Returns:
            List of documents from the view
        """
        if self.db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        
        try:
            collection = self.db[settings.mongodb_view]
            logger.info(f"Executing pipeline with {len(pipeline)} stages")
            
            # Verify date types before execution
            def check_date_types(obj, path=""):
                """Recursively check if dates are datetime objects."""
                from datetime import datetime
                issues = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        if key in ["$gte", "$lte", "$gt", "$lt", "$eq", "$ne"]:
                            if isinstance(value, str):
                                issues.append(f"⚠️  {current_path} is STRING (should be datetime): {value}")
                            elif isinstance(value, datetime):
                                logger.debug(f"✅ {current_path} is datetime: {value}")
                        elif isinstance(value, (dict, list)):
                            issues.extend(check_date_types(value, current_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        issues.extend(check_date_types(item, f"{path}[{i}]"))
                return issues
            
            date_issues = check_date_types(pipeline)
            if date_issues:
                for issue in date_issues:
                    logger.warning(issue)
            else:
                logger.info("✅ All date fields are datetime objects")
            
            logger.info(f"Pipeline stages: {json.dumps(pipeline, default=str, indent=2)}")
            
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            logger.info(f"Pipeline executed successfully. Retrieved {len(results)} documents")
            if results:
                logger.info(f"First result sample: {json.dumps(results[0] if results else {}, default=str, indent=2)}")
            return results
        except Exception as e:
            logger.error(f"Error executing pipeline: {e}")
            raise
    
    async def get_view_sample(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a sample of documents from the view to help LLM understand structure.
        
        Args:
            limit: Number of sample documents to retrieve
            
        Returns:
            List of sample documents
        """
        if self.db is None:
            raise RuntimeError("MongoDB not connected. Call connect() first.")
        
        try:
            collection = self.db[settings.mongodb_view]
            cursor = collection.find().limit(limit)
            results = await cursor.to_list(length=limit)
            return results
        except Exception as e:
            logger.error(f"Error getting view sample: {e}")
            return []


# Global instance
mongo_service = MongoService()

