"""Test script for embedding generation."""
import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_embedding.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_embedding():
    """Test embedding generation."""
    from app.services.ai.processor import ai_processor
    
    try:
        # Initialize AI processor
        logger.info("Initializing AI processor...")
        await ai_processor.load_models()
        
        # Test text
        test_text = """
        O autismo é uma condição neurológica que afeta a comunicação e o comportamento.
        Crianças com autismo podem ter dificuldades com interações sociais e comunicação não verbal.
        """
        
        # Generate embedding
        logger.info("Generating embedding...")
        embedding = await ai_processor.get_embedding(test_text)
        
        # Check result
        if not embedding:
            logger.error("Failed to generate embedding: Empty result")
            return False
            
        logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
        logger.info(f"First 5 values: {embedding[:5]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in test_embedding: {str(e)}", exc_info=True)
        return False
    
if __name__ == "__main__":
    result = asyncio.run(test_embedding())
    if result:
        print("\n✅ Embedding test completed successfully!")
    else:
        print("\n❌ Embedding test failed. Check the logs for details.")
