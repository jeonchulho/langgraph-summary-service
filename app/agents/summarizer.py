"""Summarization service using LangGraph workflow."""
from typing import List, Dict, Any
import time

from app.agents.workflow import create_summary_workflow, SummaryState
from app.utils.logger import logger


class SummarizerService:
    """Service for text summarization using LangGraph."""
    
    def __init__(self):
        """Initialize summarizer service."""
        self.workflow = create_summary_workflow()
        logger.info("Summarizer service initialized")
    
    async def summarize(
        self,
        text: str,
        summary_type: str = "document",
        summary_style: str = "brief"
    ) -> Dict[str, Any]:
        """
        Summarize a single text.
        
        Args:
            text: Text to summarize
            summary_type: Type of text (email, chat, document)
            summary_style: Style of summary (brief, detailed, bullet, executive)
            
        Returns:
            Summary result with metrics
        """
        start_time = time.time()
        
        # Initialize state
        initial_state: SummaryState = {
            "original_text": text,
            "text": text,
            "summary_type": summary_type,
            "summary_style": summary_style,
            "key_points": [],
            "summary": "",
            "quality_score": 0.0,
            "needs_refinement": False
        }
        
        try:
            # Run workflow
            result = await self.workflow.ainvoke(initial_state)
            
            processing_time = time.time() - start_time
            
            # Calculate metrics
            token_count = len(text.split()) + len(result["summary"].split())
            cost = token_count * 0.00002  # Rough estimate
            
            return {
                "summary": result["summary"],
                "key_points": result["key_points"],
                "metrics": {
                    "quality_score": result["quality_score"],
                    "processing_time": processing_time,
                    "token_count": token_count,
                    "cost": cost
                }
            }
        
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            raise
    
    async def summarize_batch(
        self,
        texts: List[str],
        summary_type: str = "document",
        summary_style: str = "brief"
    ) -> Dict[str, Any]:
        """
        Summarize multiple texts.
        
        Args:
            texts: List of texts to summarize
            summary_type: Type of texts
            summary_style: Style of summaries
            
        Returns:
            Batch summary results
        """
        start_time = time.time()
        summaries = []
        total_cost = 0.0
        
        for text in texts:
            try:
                result = await self.summarize(text, summary_type, summary_style)
                summaries.append(result)
                total_cost += result["metrics"]["cost"]
            except Exception as e:
                logger.error(f"Batch summarization error: {e}")
                # Add error result
                summaries.append({
                    "summary": "Error generating summary",
                    "key_points": [],
                    "metrics": {
                        "quality_score": 0.0,
                        "processing_time": 0.0,
                        "token_count": 0,
                        "cost": 0.0
                    }
                })
        
        total_time = time.time() - start_time
        
        return {
            "summaries": summaries,
            "total_cost": total_cost,
            "total_time": total_time
        }


# Global summarizer instance
summarizer_service = SummarizerService()
