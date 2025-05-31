"""AI processing service for news content."""
import logging
import numpy as np
from typing import Dict, Any, Optional, List

from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIProcessor:
    """Service for AI processing of news content."""
    
    def __init__(self):
        """Initialize the AI processor with required models."""
        self.embedding_model = None
        self.summarizer = None
        self._models_loaded = False
    
    async def load_models(self) -> None:
        """Lazy load the AI models."""
        if self._models_loaded:
            logger.debug("Models already loaded, skipping...")
            return
            
        import os
        from pathlib import Path
        import torch
        
        try:
            # Ensure model directory exists
            os.makedirs(settings.HF_HOME, exist_ok=True)
            logger.info(f"Using model cache directory: {os.path.abspath(settings.HF_HOME)}")
            
            # Set environment variable for Hugging Face cache
            os.environ['TRANSFORMERS_CACHE'] = settings.HF_HOME
            os.environ['HF_HOME'] = settings.HF_HOME
            
            logger.info("Loading AI models...")
            logger.info(f"PyTorch version: {torch.__version__}")
            logger.info(f"CUDA available: {torch.cuda.is_available()}")
            
            # Load sentence transformer for embeddings
            logger.info(f"Loading SentenceTransformer model: {settings.SENTENCE_TRANSFORMER_MODEL}")
            logger.info(f"Cache folder: {os.path.abspath(settings.HF_HOME)}")
            logger.info(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
            
            try:
                # Verificar se o diretório de cache existe
                if not os.path.exists(settings.HF_HOME):
                    logger.info(f"Creating cache directory: {settings.HF_HOME}")
                    os.makedirs(settings.HF_HOME, exist_ok=True)
                
                logger.info("Initializing SentenceTransformer...")
                self.embedding_model = SentenceTransformer(
                    settings.SENTENCE_TRANSFORMER_MODEL,
                    cache_folder=settings.HF_HOME,
                    device='cuda' if torch.cuda.is_available() else 'cpu'
                )
                
                logger.info("SentenceTransformer initialized, testing with sample text...")
                test_text = "This is a test sentence for embedding generation."
                test_embedding = self.embedding_model.encode(
                    test_text,
                    convert_to_numpy=True,
                    show_progress_bar=True
                )
                
                logger.info(f"Test embedding generated successfully")
                logger.info(f"Test embedding shape: {test_embedding.shape}")
                logger.info(f"Test embedding type: {type(test_embedding)}")
                logger.info(f"Test embedding first 5 values: {test_embedding[:5]}")
                
                # Verificar se o embedding é válido
                if test_embedding is None:
                    raise ValueError("Test embedding is None")
                if not isinstance(test_embedding, np.ndarray):
                    raise ValueError(f"Test embedding is not a numpy array: {type(test_embedding)}")
                if test_embedding.size == 0:
                    raise ValueError("Test embedding is empty")
                if not np.any(test_embedding):
                    raise ValueError("Test embedding contains only zeros")
                
                logger.info("SentenceTransformer model loaded and tested successfully")
                
            except Exception as e:
                logger.error(f"Failed to load or test SentenceTransformer model: {str(e)}", exc_info=True)
                # Tentar forçar o download do modelo novamente
                try:
                    logger.info("Attempting to force download the model...")
                    import shutil
                    model_path = os.path.join(settings.HF_HOME, f"sentence-transformers_{settings.SENTENCE_TRANSFORMER_MODEL.replace('/', '_')}")
                    if os.path.exists(model_path):
                        logger.warning(f"Removing potentially corrupted model cache: {model_path}")
                        shutil.rmtree(model_path, ignore_errors=True)
                    
                    # Tentar novamente
                    self.embedding_model = SentenceTransformer(
                        settings.SENTENCE_TRANSFORMER_MODEL,
                        cache_folder=settings.HF_HOME,
                        device='cuda' if torch.cuda.is_available() else 'cpu',
                        force_download=True
                    )
                    logger.info("Model re-downloaded successfully")
                except Exception as e2:
                    logger.error(f"Failed to re-download model: {str(e2)}", exc_info=True)
                    raise ValueError(f"Failed to load SentenceTransformer model: {str(e)}. Also failed to re-download: {str(e2)}")
            
            # Load summarization pipeline
            logger.info(f"Loading summarization model: {settings.SUMMARIZATION_MODEL}")
            try:
                # Set environment variables for model cache
                os.environ['TRANSFORMERS_CACHE'] = settings.HF_HOME
                os.environ['HF_HOME'] = settings.HF_HOME
                
                self.summarizer = pipeline(
                    "summarization",
                    model=settings.SUMMARIZATION_MODEL,
                    device=0 if torch.cuda.is_available() else -1,
                    framework="pt"  # Explicitly use PyTorch
                )
                # Test the summarizer with model_kwargs
                test_summary = self.summarizer("This is a test.", max_length=10, min_length=5, do_sample=False)
                logger.info(f"Summarization model loaded successfully. Test summary: {test_summary}")
            except Exception as e:
                logger.error(f"Failed to load summarization model: {str(e)}", exc_info=True)
                raise
            
            self._models_loaded = True
            logger.info("All AI models loaded and tested successfully")
            
        except Exception as e:
            logger.error(f"Error loading AI models: {str(e)}", exc_info=True)
            self._models_loaded = False
            raise
    
    async def get_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.
        
        Args:
            text: The input text to embed.
            
        Returns:
            A list of floats representing the embedding vector.
            Returns an empty list if there's an error or if the input text is empty.
        """
        logger.info("Starting get_embedding method")
        
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided for embedding")
            return []
            
        if not self._models_loaded:
            logger.info("Models not loaded, loading them now...")
            try:
                await self.load_models()
            except Exception as e:
                logger.error(f"Failed to load AI models: {str(e)}", exc_info=True)
                return []
        
        if self.embedding_model is None:
            logger.error("Embedding model is not initialized")
            return []
            
        try:
            logger.info(f"Generating embedding for text (first 100 chars): {text[:100]}...")
            logger.info(f"Embedding model type: {type(self.embedding_model)}")
            logger.info(f"Model device: {getattr(self.embedding_model, '_target_device', 'unknown')}")
            
            # Convert text to embedding
            logger.info("Calling embedding_model.encode()...")
            try:
                embedding = self.embedding_model.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=True,
                    batch_size=32,
                    device='cuda' if str(self.embedding_model._target_device) != 'cpu' else 'cpu'
                )
                logger.info("embedding_model.encode() completed successfully")
            except Exception as encode_error:
                logger.error(f"Error in embedding_model.encode(): {str(encode_error)}", exc_info=True)
                # Try with default parameters as fallback
                try:
                    logger.info("Trying with default parameters...")
                    embedding = self.embedding_model.encode(text)
                    logger.info("Fallback embedding_model.encode() completed")
                except Exception as fallback_error:
                    logger.error(f"Fallback embedding generation also failed: {str(fallback_error)}", exc_info=True)
                    return []
            
            # Log embedding metadata
            logger.info(f"Generated embedding type: {type(embedding)}")
            if hasattr(embedding, 'shape'):
                logger.info(f"Embedding shape: {embedding.shape}")
            if hasattr(embedding, 'dtype'):
                logger.info(f"Embedding dtype: {embedding.dtype}")
            
            # Validate the embedding
            if embedding is None:
                logger.error("Embedding generation returned None")
                return []
                
            # Convert numpy array to list if needed
            if hasattr(embedding, 'tolist'):
                logger.info("Converting numpy array to list...")
                try:
                    embedding_list = embedding.tolist()
                    logger.info(f"Converted to list with length: {len(embedding_list) if hasattr(embedding_list, '__len__') else 'N/A'}")
                    
                    # Additional validation
                    if not isinstance(embedding_list, list):
                        logger.error(f"Expected list after tolist(), got {type(embedding_list)}")
                        return []
                        
                    if not embedding_list:
                        logger.error("Generated embedding list is empty")
                        return []
                        
                    if not all(isinstance(x, (int, float)) for x in embedding_list):
                        logger.error("Embedding list contains non-numeric values")
                        return []
                        
                    # Check for NaN or Inf values
                    import math
                    if any(not math.isfinite(x) for x in embedding_list):
                        logger.error("Embedding contains NaN or infinite values")
                        return []
                        
                    logger.info(f"Successfully generated embedding with {len(embedding_list)} dimensions")
                    logger.info(f"First 5 values: {embedding_list[:5]}")
                    return embedding_list
                    
                except Exception as convert_error:
                    logger.error(f"Error converting embedding to list: {str(convert_error)}", exc_info=True)
                    return []
            
            # If we get here, the embedding is not a numpy array
            if isinstance(embedding, list):
                logger.info(f"Returning embedding as list with length: {len(embedding)}")
                return embedding
            
            logger.error(f"Unexpected embedding type that couldn't be converted to list: {type(embedding)}")
            return []
            
        except Exception as e:
            logger.error(f"Unexpected error in get_embedding: {str(e)}", exc_info=True)
            return []
    
    async def summarize_text(self, text: str, max_length: int = 150) -> str:
        """Generate a summary of the input text.
        
        Args:
            text: The input text to summarize.
            max_length: Maximum length of the summary.
            
        Returns:
            A summary of the input text.
        """
        if not self._models_loaded:
            await self.load_models()
        
        try:
            # Truncate text to avoid token limits
            max_input_length = 1024  # Adjust based on model limits
            truncated_text = text[:max_input_length]
            
            # Generate summary
            summary = self.summarizer(
                truncated_text,
                max_length=max_length,
                min_length=30,
                do_sample=False
            )
            return summary[0]['summary_text']
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return text[:max_length]  # Fallback to truncation
    
    async def process_news_content(self, content: str) -> Dict[str, Any]:
        """Process news content with AI models.
        
        Args:
            content: The news content to process.
            
        Returns:
            A dictionary with processed information including summary and embedding.
            If any step fails, returns partial results with error information.
        """
        result = {
            'individual_summary': '',
            'embedding': [],
            'processed_at': datetime.utcnow(),
            'language': 'pt-br',
            'processing_errors': []
        }
        
        # Ensure models are loaded
        if not self._models_loaded:
            try:
                await self.load_models()
            except Exception as e:
                error_msg = f"Failed to load AI models: {str(e)}"
                logger.error(error_msg, exc_info=True)
                result['processing_errors'].append(error_msg)
                return result
        
        # Generate summary
        try:
            summary = await self.summarize_text(content)
            if summary and isinstance(summary, str):
                result['individual_summary'] = summary
            else:
                error_msg = f"Invalid summary generated: {type(summary)}"
                logger.warning(error_msg)
                result['processing_errors'].append(error_msg)
        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result['processing_errors'].append(error_msg)
        
        # Generate embedding (most critical part)
        try:
            embedding = await self.get_embedding(content)
            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                result['embedding'] = embedding
                logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            else:
                error_msg = f"Invalid embedding generated: {type(embedding)}, length: {len(embedding) if hasattr(embedding, '__len__') else 'N/A'}"
                logger.error(error_msg)
                result['processing_errors'].append("Failed to generate valid embedding")
        except Exception as e:
            error_msg = f"Error generating embedding: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result['processing_errors'].append(error_msg)
        
        # Clean up processing_errors if empty
        if not result['processing_errors']:
            result.pop('processing_errors', None)
        
        return result

# Create a singleton instance
ai_processor = AIProcessor()

# Helper function for direct imports
async def process_news_content(content: str) -> Dict[str, Any]:
    """Process news content using the AI processor.
    
    This is a convenience function that uses the singleton instance.
    """
    return await ai_processor.process_news_content(content)
