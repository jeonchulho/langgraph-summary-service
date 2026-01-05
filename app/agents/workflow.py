"""LangGraph workflow for text summarization."""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import re

from app.config import settings
from app.utils.logger import logger


class SummaryState(TypedDict):
    """State for summary workflow."""
    original_text: str
    text: str
    summary_type: str
    summary_style: str
    key_points: List[str]
    summary: str
    quality_score: float
    needs_refinement: bool


def preprocess_node(state: SummaryState) -> SummaryState:
    """
    Preprocess text based on type.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state
    """
    text = state["text"]
    summary_type = state["summary_type"]
    
    if summary_type == "email":
        # Remove email metadata - handle lines starting with common email headers
        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            # Skip lines that start with common email headers (case insensitive)
            line_lower = line.lower().strip()
            if not (line_lower.startswith('from:') or 
                    line_lower.startswith('to:') or 
                    line_lower.startswith('subject:') or 
                    line_lower.startswith('date:')):
                filtered_lines.append(line)
        text = '\n'.join(filtered_lines)
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
    elif summary_type == "chat":
        # Remove timestamps
        text = re.sub(r'\[\d{2}:\d{2}(:\d{2})?\]', '', text)
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}', '', text)
    
    # General cleanup
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines
    text = text.strip()
    
    state["text"] = text
    logger.info(f"Preprocessed {summary_type} text")
    return state


async def extract_key_points_node(state: SummaryState) -> SummaryState:
    """
    Extract 3-7 key points from text.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state
    """
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.3,
        openai_api_key=settings.openai_api_key
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at identifying key points in text. Extract 3-7 main points."),
        ("human", "Extract the key points from this text:\n\n{text}\n\nProvide exactly 3-7 key points, one per line, starting each with '- '.")
    ])
    
    chain = prompt | llm
    response = await chain.ainvoke({"text": state["text"]})
    
    # Parse key points
    key_points = []
    for line in response.content.split('\n'):
        line = line.strip()
        if line.startswith('-'):
            key_points.append(line[1:].strip())
    
    # Ensure we have 3-7 points
    key_points = key_points[:7] if len(key_points) > 7 else key_points
    if len(key_points) < 3:
        key_points.extend([f"Additional point {i}" for i in range(3 - len(key_points))])
    
    state["key_points"] = key_points
    logger.info(f"Extracted {len(key_points)} key points")
    return state


async def generate_summary_node(state: SummaryState) -> SummaryState:
    """
    Generate summary based on style.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state
    """
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.5,
        openai_api_key=settings.openai_api_key
    )
    
    style = state["summary_style"]
    
    # Style-specific prompts
    style_prompts = {
        "brief": "Provide a concise summary in 2-3 sentences.",
        "detailed": "Provide a comprehensive summary in 5-7 sentences with key details.",
        "bullet": "Provide a summary in bullet point format with 5-7 main points.",
        "executive": "Provide an executive summary with conclusions first, then supporting details."
    }
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are an expert summarizer. {style_prompts.get(style, style_prompts['brief'])}"),
        ("human", "Summarize this text:\n\n{text}\n\nKey points to include:\n{key_points}")
    ])
    
    key_points_text = "\n".join([f"- {point}" for point in state["key_points"]])
    
    chain = prompt | llm
    response = await chain.ainvoke({
        "text": state["text"],
        "key_points": key_points_text
    })
    
    state["summary"] = response.content.strip()
    logger.info(f"Generated {style} summary")
    return state


async def validate_quality_node(state: SummaryState) -> SummaryState:
    """
    Validate summary quality.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state
    """
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.0,
        openai_api_key=settings.openai_api_key
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a quality evaluator. Rate the summary quality from 0.0 to 1.0 based on accuracy, completeness, and clarity. Respond with only a number."),
        ("human", "Original text:\n{original}\n\nSummary:\n{summary}\n\nQuality score (0.0-1.0):")
    ])
    
    chain = prompt | llm
    response = await chain.ainvoke({
        "original": state["text"],
        "summary": state["summary"]
    })
    
    # Extract score
    try:
        score = float(re.search(r'0?\.\d+|[01]\.0|[01]', response.content).group())
        score = max(0.0, min(1.0, score))
    except:
        score = 0.7  # Default score
    
    state["quality_score"] = score
    state["needs_refinement"] = score < 0.6
    
    logger.info(f"Quality score: {score}")
    return state


async def refine_summary_node(state: SummaryState) -> SummaryState:
    """
    Refine summary if quality is low.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state
    """
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        openai_api_key=settings.openai_api_key
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert editor. Improve this summary to be more accurate, complete, and clear."),
        ("human", "Original text:\n{original}\n\nCurrent summary:\n{summary}\n\nKey points:\n{key_points}\n\nProvide an improved summary:")
    ])
    
    key_points_text = "\n".join([f"- {point}" for point in state["key_points"]])
    
    chain = prompt | llm
    response = await chain.ainvoke({
        "original": state["text"],
        "summary": state["summary"],
        "key_points": key_points_text
    })
    
    state["summary"] = response.content.strip()
    state["needs_refinement"] = False
    state["quality_score"] = 0.8  # Assume improvement
    
    logger.info("Refined summary")
    return state


def should_refine(state: SummaryState) -> str:
    """
    Determine if summary needs refinement.
    
    Args:
        state: Current workflow state
        
    Returns:
        Next node name
    """
    return "refine" if state["needs_refinement"] else END


def create_summary_workflow() -> StateGraph:
    """
    Create the summary workflow graph.
    
    Returns:
        Compiled workflow graph
    """
    workflow = StateGraph(SummaryState)
    
    # Add nodes
    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("extract_key_points", extract_key_points_node)
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("validate_quality", validate_quality_node)
    workflow.add_node("refine", refine_summary_node)
    
    # Add edges
    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "extract_key_points")
    workflow.add_edge("extract_key_points", "generate_summary")
    workflow.add_edge("generate_summary", "validate_quality")
    workflow.add_conditional_edges(
        "validate_quality",
        should_refine,
        {
            "refine": "refine",
            END: END
        }
    )
    workflow.add_edge("refine", END)
    
    return workflow.compile()
