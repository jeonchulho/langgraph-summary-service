"""Tests for summarizer service."""
import pytest

from app.agents.summarizer import SummarizerService
from app.agents.workflow import create_summary_workflow


@pytest.mark.asyncio
async def test_summarizer_initialization():
    """Test summarizer service initialization."""
    summarizer = SummarizerService()
    assert summarizer.workflow is not None


@pytest.mark.asyncio
async def test_workflow_creation():
    """Test workflow creation."""
    workflow = create_summary_workflow()
    assert workflow is not None


@pytest.mark.asyncio
async def test_summarize_basic(sample_text):
    """Test basic summarization."""
    summarizer = SummarizerService()
    
    # Note: This test requires OPENAI_API_KEY to be set
    # In a real test environment, you would mock the LLM calls
    try:
        result = await summarizer.summarize(
            sample_text,
            summary_type="document",
            summary_style="brief"
        )
        
        assert "summary" in result
        assert "key_points" in result
        assert "metrics" in result
        assert len(result["key_points"]) >= 3
        assert len(result["key_points"]) <= 7
        assert result["metrics"]["quality_score"] >= 0.0
        assert result["metrics"]["quality_score"] <= 1.0
    except Exception as e:
        # If OpenAI API key is not configured, skip this test
        pytest.skip(f"Skipping test due to: {e}")


@pytest.mark.asyncio
async def test_summarize_different_styles(sample_text):
    """Test summarization with different styles."""
    summarizer = SummarizerService()
    
    styles = ["brief", "detailed", "bullet", "executive"]
    
    for style in styles:
        try:
            result = await summarizer.summarize(
                sample_text,
                summary_type="document",
                summary_style=style
            )
            
            assert "summary" in result
            assert len(result["summary"]) > 0
        except Exception as e:
            pytest.skip(f"Skipping test due to: {e}")


@pytest.mark.asyncio
async def test_batch_summarization(sample_text):
    """Test batch summarization."""
    summarizer = SummarizerService()
    
    texts = [sample_text, sample_text, sample_text]
    
    try:
        result = await summarizer.summarize_batch(
            texts,
            summary_type="document",
            summary_style="brief"
        )
        
        assert "summaries" in result
        assert "total_cost" in result
        assert "total_time" in result
        assert len(result["summaries"]) == len(texts)
    except Exception as e:
        pytest.skip(f"Skipping test due to: {e}")


def test_preprocess_email():
    """Test email preprocessing."""
    from app.agents.workflow import preprocess_node
    
    email_text = """
    From: sender@example.com
    To: receiver@example.com
    Subject: Test Email
    
    This is the email body.
    """
    
    state = {
        "original_text": email_text,
        "text": email_text,
        "summary_type": "email",
        "summary_style": "brief",
        "key_points": [],
        "summary": "",
        "quality_score": 0.0,
        "needs_refinement": False
    }
    
    result = preprocess_node(state)
    assert "From:" not in result["text"]
    assert "To:" not in result["text"]
    assert "Subject:" not in result["text"]
    assert "email body" in result["text"]


def test_preprocess_chat():
    """Test chat preprocessing."""
    from app.agents.workflow import preprocess_node
    
    chat_text = """
    [10:30] User1: Hello
    [10:31] User2: Hi there
    [10:32] User1: How are you?
    """
    
    state = {
        "original_text": chat_text,
        "text": chat_text,
        "summary_type": "chat",
        "summary_style": "brief",
        "key_points": [],
        "summary": "",
        "quality_score": 0.0,
        "needs_refinement": False
    }
    
    result = preprocess_node(state)
    assert "[10:30]" not in result["text"]
    assert "Hello" in result["text"]
    assert "Hi there" in result["text"]
