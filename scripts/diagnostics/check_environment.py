#!/usr/bin/env python3
"""
Environment Configuration Checker

This script checks the current environment configuration and reports any issues.
It verifies required settings, file permissions, and service connectivity.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
import pymongo
import redis
from pydantic import AnyUrl, ValidationError

# Import settings from the application
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from app.core.config import Settings, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("environment_check")


class EnvironmentCheck:
    """Check environment configuration and dependencies."""

    def __init__(self):
        """Initialize the environment checker."""
        self.settings = get_settings()
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def check_required_vars(self) -> None:
        """Check for required environment variables."""
        required_vars = [
            "MONGODB_URL",
            "SERPAPI_KEY",
            "SECRET_KEY",
        ]

        for var in required_vars:
            if not getattr(self.settings, var, None):
                self.issues.append(f"Required environment variable {var} is not set")

    def check_file_permissions(self) -> None:
        """Check file and directory permissions."""
        dirs_to_check = [
            (self.settings.get_models_dir(), 0o755, "models directory"),
            (self.settings.get_logs_dir(), 0o755, "logs directory"),
        ]

        for dir_path, expected_mode, name in dirs_to_check:
            try:
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created {name} at {dir_path}")
                
                if not os.access(dir_path, os.W_OK):
                    self.issues.append(f"No write permission for {name} at {dir_path}")
                
                # Check directory permissions
                mode = dir_path.stat().st_mode & 0o777
                if mode != expected_mode:
                    self.warnings.append(
                        f"{name} at {dir_path} has permissions {oct(mode)[-3:]}, "
                        f"recommended is {oct(expected_mode)[-3:]}"
                    )
            except Exception as e:
                self.issues.append(f"Failed to check {name} at {dir_path}: {e}")

    async def check_mongodb_connection(self) -> None:
        """Check MongoDB connection."""
        try:
            # Extract host and port for better error messages
            host = self.settings.MONGODB_URL.split('//')[-1].split('/')[0].split('@')[-1]
            
            # Create connection parameters without duplicating the URL
            conn_params = {
                'serverSelectionTimeoutMS': 5000,
                'socketTimeoutMS': 5000,
                'connectTimeoutMS': 5000,
            }
            
            # Only add additional params if they're not in the URL
            if 'username' not in self.settings.MONGODB_URL:
                conn_params.update({
                    'username': self.settings.mongodb_connection_params.get('username'),
                    'password': self.settings.mongodb_connection_params.get('password'),
                })
            
            client = pymongo.MongoClient(self.settings.MONGODB_URL, **conn_params)
            
            # Test the connection
            client.server_info()
            logger.info(f"✅ Successfully connected to MongoDB at {host}")
            
            # Check if database exists
            db = client[self.settings.MONGODB_DB_NAME]
            collections = db.list_collection_names()
            logger.info(f"Available collections: {', '.join(collections) or 'None'}")
            
        except pymongo.errors.ServerSelectionTimeoutError:
            self.issues.append(f"Failed to connect to MongoDB at {host}: Connection timeout")
            self.warnings.append("Verify that MongoDB is running and accessible")
            self.warnings.append(f"Check if the URL is correct: {self.settings.MONGODB_URL}")
            
        except pymongo.errors.ConfigurationError as e:
            self.issues.append(f"MongoDB configuration error: {e}")
            self.warnings.append("Check your MongoDB URL format and credentials")
            
        except pymongo.errors.PyMongoError as e:
            self.issues.append(f"MongoDB error: {e}")
            
        except Exception as e:
            self.issues.append(f"Unexpected error connecting to MongoDB: {e}")
            
        finally:
            if 'client' in locals():
                client.close()

    async def check_redis_connection(self) -> None:
        """Check Redis connection."""
        # Get connection details for better error messages
        host = self.settings.REDIS_HOST
        port = self.settings.REDIS_PORT
        
        # First, check if Redis is installed
        try:
            import redis
        except ImportError:
            self.issues.append("Redis Python client not installed. Install with: pip install redis")
            return
            
        # Check if Redis server is running locally
        if host in ["localhost", "127.0.0.1"]:
            try:
                import subprocess
                result = subprocess.run(["which", "redis-server"], capture_output=True, text=True)
                if result.returncode != 0:
                    self.issues.append("Redis server is not installed on this system")
                    self.warnings.append("Install Redis with: brew install redis (macOS) or sudo apt-get install redis (Ubuntu)")
                    return
            except Exception:
                # If we can't check, continue with connection test
                pass
        
        try:
            # Try to connect with a short timeout
            r = redis.Redis(
                host=host,
                port=port,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD or None,
                socket_connect_timeout=2,  # Shorter timeout for faster feedback
                socket_timeout=2,
                ssl=self.settings.REDIS_SSL,
                decode_responses=True
            )
            
            # Test the connection
            if not r.ping():
                self.issues.append(f"Failed to ping Redis server at {host}:{port}")
            else:
                logger.info(f"✅ Successfully connected to Redis at {host}:{port}")
                
                # Get Redis info
                try:
                    info = r.info()
                    logger.info(f"Redis version: {info.get('redis_version')}")
                    logger.info(f"Connected clients: {info.get('connected_clients')}")
                    logger.info(f"Used memory: {info.get('used_memory_human')}")
                except Exception as e:
                    logger.warning(f"Could not get Redis info: {e}")
                
        except redis.ConnectionError as e:
            self.issues.append(f"Could not connect to Redis at {host}:{port}")
            self.warnings.append("Make sure Redis is running and accessible")
            self.warnings.append("Check if the host and port are correct")
            if "password" in str(e).lower():
                self.warnings.append("Authentication failed - check your Redis password")
            
            # Additional help for local development
            if host in ["localhost", "127.0.0.1"]:
                self.warnings.append("To start Redis locally, run: redis-server")
                self.warnings.append("Or install with: brew install redis (macOS) or sudo apt-get install redis (Ubuntu)")
                
        except redis.RedisError as e:
            self.issues.append(f"Redis error: {e}")
            
        except Exception as e:
            self.issues.append(f"Unexpected error connecting to Redis: {e}")

    async def check_serpapi_connection(self) -> None:
        """Check SerpAPI connection with a simple request."""
        if not self.settings.SERPAPI_KEY:
            self.issues.append("SERPAPI_KEY is not set")
            return
            
        test_query = {
            "q": "test",
            "api_key": self.settings.SERPAPI_KEY,
            "num": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.settings.SERPAPI_ENDPOINT,
                    params=test_query
                )
                
                if response.status_code == 200:
                    logger.info("✅ Successfully connected to SerpAPI")
                else:
                    self.issues.append(
                        f"SerpAPI returned status code {response.status_code}: {response.text}"
                    )
                    
        except httpx.RequestError as e:
            self.issues.append(f"Failed to connect to SerpAPI: {e}")
        except Exception as e:
            self.issues.append(f"Unexpected error connecting to SerpAPI: {e}")

    def check_environment(self) -> None:
        """Run all environment checks."""
        logger.info("Starting environment checks...")
        
        # Basic checks
        self.check_required_vars()
        self.check_file_permissions()
        
        # Print current environment
        logger.info(f"Environment: {self.settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {self.settings.DEBUG}")
        logger.info(f"MongoDB URL: {self.settings.MONGODB_URL}")
        logger.info(f"Redis host: {self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}")
        
        # Run async checks
        import asyncio
        asyncio.run(self.run_async_checks())
        
        # Print summary
        self.print_summary()
    
    async def run_async_checks(self) -> None:
        """Run all async checks."""
        await asyncio.gather(
            self.check_mongodb_connection(),
            self.check_redis_connection(),
            self.check_serpapi_connection(),
        )

    def print_summary(self) -> None:
        """Print a summary of issues found."""
        print("\n" + "=" * 50)
        print("ENVIRONMENT CHECK SUMMARY")
        print("=" * 50)
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if self.issues:
            print("\n❌ ISSUES FOUND:")
            for issue in self.issues:
                print(f"  • {issue}")
            print("\nSome required services are not available or misconfigured.")
            sys.exit(1)
        else:
            print("\n✅ All checks passed! Environment is properly configured.")
            sys.exit(0)


def main() -> None:
    """Run the environment check."""
    checker = EnvironmentCheck()
    checker.check_environment()


if __name__ == "__main__":
    main()
