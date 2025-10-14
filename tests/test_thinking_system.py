#!/usr/bin/env python
"""Comprehensive test for the Extended Thinking System."""

import sys
from datetime import datetime, timedelta

def test_imports():
    """Test all thinking system imports."""
    print("Testing imports...")

    try:
        from contextvault.models.thinking import (
            ThinkingSession, Thought, SubQuestion, ThinkingSynthesis,
            ThinkingStatus, ThoughtType
        )
        print("✓ Thinking models import successfully")
    except Exception as e:
        print(f"✗ Thinking models import failed: {e}")
        return False

    try:
        from contextvault.thinking import (
            thinking_engine, session_manager, question_generator
        )
        print("✓ Thinking services import successfully")
    except Exception as e:
        print(f"✗ Thinking services import failed: {e}")
        return False

    try:
        from contextvault.api import thinking
        print("✓ Thinking API imports successfully")
    except Exception as e:
        print(f"✗ Thinking API import failed: {e}")
        return False

    try:
        from contextvault.main import app
        print("✓ FastAPI app imports successfully")
    except Exception as e:
        print(f"✗ FastAPI app import failed: {e}")
        return False

    return True


def test_model_creation():
    """Test creating thinking session models."""
    print("\nTesting model creation...")

    try:
        from contextvault.models.thinking import ThinkingSession, Thought, SubQuestion, ThinkingSynthesis

        # Test ThinkingSession creation
        session = ThinkingSession(
            original_question="What is the meaning of life?",
            thinking_duration_minutes=30,
            model_id="llama3.1",
            status="created",
            total_thoughts=0,
            total_questions=0,
            total_syntheses=0,
            confidence_evolution=[]
        )

        session_dict = session.to_dict()
        if "original_question" in session_dict:
            print("✓ ThinkingSession creation and serialization works")
        else:
            print("✗ ThinkingSession serialization failed")
            return False

        # Test Thought creation
        thought = Thought(
            session_id=session.id,
            sequence_number=0,
            thought_text="This is a profound question that has puzzled humanity for millennia",
            thought_type="exploration",
            confidence=0.7,
            time_offset_seconds=0
        )

        thought_dict = thought.to_dict()
        if "thought_text" in thought_dict and thought_dict["confidence"] == 0.7:
            print("✓ Thought creation and serialization works")
        else:
            print("✗ Thought serialization failed")
            return False

        # Test SubQuestion creation
        sub_q = SubQuestion(
            session_id=session.id,
            question_text="What do philosophers mean by 'meaning'?",
            priority=8,
            explored=False
        )

        if sub_q.priority == 8 and not sub_q.explored:
            print("✓ SubQuestion creation works")
        else:
            print("✗ SubQuestion creation failed")
            return False

        # Test mark_explored method
        sub_q.mark_explored("Explored the concept of meaning in philosophy")
        if sub_q.explored and sub_q.insights_gained:
            print("✓ SubQuestion.mark_explored() works")
        else:
            print("✗ SubQuestion.mark_explored() failed")
            return False

        # Test ThinkingSynthesis creation
        synthesis = ThinkingSynthesis(
            session_id=session.id,
            sequence_number=0,
            synthesis_text="Current understanding: The meaning of life is subjective",
            key_insights=["Subjective nature", "Cultural perspectives"],
            confidence_level=0.6,
            remaining_questions=["What about objective meaning?"],
            time_offset_seconds=300
        )

        if len(synthesis.key_insights) == 2:
            print("✓ ThinkingSynthesis creation works")
        else:
            print("✗ ThinkingSynthesis creation failed")
            return False

        return True

    except Exception as e:
        print(f"✗ Model creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_methods():
    """Test ThinkingSession helper methods."""
    print("\nTesting session methods...")

    try:
        from contextvault.models.thinking import ThinkingSession

        session = ThinkingSession(
            original_question="Test question",
            thinking_duration_minutes=30,
            model_id="llama3.1",
            started_at=datetime.utcnow() - timedelta(minutes=10),
            status="thinking"
        )

        # Test get_elapsed_seconds
        elapsed = session.get_elapsed_seconds()
        if 590 <= elapsed <= 610:  # Should be around 600 seconds (10 minutes)
            print(f"✓ get_elapsed_seconds() works: {elapsed}s")
        else:
            print(f"✗ get_elapsed_seconds() returned unexpected value: {elapsed}s")
            return False

        # Test get_progress_percentage
        progress = session.get_progress_percentage()
        if 30 <= progress <= 35:  # Should be around 33% (10/30 minutes)
            print(f"✓ get_progress_percentage() works: {progress:.1f}%")
        else:
            print(f"✗ get_progress_percentage() returned unexpected value: {progress}%")
            return False

        return True

    except Exception as e:
        print(f"✗ Session methods test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_engine_parsing():
    """Test thinking engine parsing methods."""
    print("\nTesting engine parsing...")

    try:
        from contextvault.thinking.thinking_engine import ThinkingEngine

        engine = ThinkingEngine()

        # Test _parse_thoughts
        response = """
THOUGHT: This is an exploration of the concept
TYPE: exploration
CONFIDENCE: 0.8
---
THOUGHT: This critiques the previous thought
TYPE: critique
CONFIDENCE: 0.6
---
THOUGHT: This makes a connection to another idea
TYPE: connection
CONFIDENCE: 0.7
"""

        thoughts = engine._parse_thoughts(response)

        if len(thoughts) == 3:
            print(f"✓ _parse_thoughts() works: parsed {len(thoughts)} thoughts")
        else:
            print(f"✗ _parse_thoughts() failed: expected 3, got {len(thoughts)}")
            return False

        # Verify thought contents
        if thoughts[0][0].startswith("This is an exploration"):
            print("✓ Thought text parsing works")
        else:
            print(f"✗ Thought text parsing failed: {thoughts[0][0]}")
            return False

        if thoughts[0][1] == "exploration":
            print("✓ Thought type parsing works")
        else:
            print(f"✗ Thought type parsing failed: {thoughts[0][1]}")
            return False

        if thoughts[0][2] == 0.8:
            print("✓ Confidence parsing works")
        else:
            print(f"✗ Confidence parsing failed: {thoughts[0][2]}")
            return False

        # Test _parse_questions
        question_response = """
QUESTION: What is the relationship between A and B?
PRIORITY: 8
---
QUESTION: How does this affect C?
PRIORITY: 6
"""

        questions = engine._parse_questions(question_response)

        if len(questions) == 2:
            print(f"✓ _parse_questions() works: parsed {len(questions)} questions")
        else:
            print(f"✗ _parse_questions() failed: expected 2, got {len(questions)}")
            return False

        if questions[0][1] == 8:
            print("✓ Question priority parsing works")
        else:
            print(f"✗ Question priority parsing failed: {questions[0][1]}")
            return False

        # Test _extract_insights
        synthesis_text = """
SYNTHESIS: This is the current understanding
INSIGHTS:
- First key insight
- Second key insight
- Third key insight
CONFIDENCE: 0.75
REMAINING:
- Question one
- Question two
"""

        insights = engine._extract_insights(synthesis_text)

        if len(insights) == 3:
            print(f"✓ _extract_insights() works: extracted {len(insights)} insights")
        else:
            print(f"✗ _extract_insights() failed: expected 3, got {len(insights)}")
            return False

        # Test _extract_confidence
        confidence = engine._extract_confidence(synthesis_text)

        if confidence == 0.75:
            print(f"✓ _extract_confidence() works: {confidence}")
        else:
            print(f"✗ _extract_confidence() failed: expected 0.75, got {confidence}")
            return False

        # Test _extract_remaining_questions
        remaining = engine._extract_remaining_questions(synthesis_text)

        if len(remaining) == 2:
            print(f"✓ _extract_remaining_questions() works: extracted {len(remaining)} questions")
        else:
            print(f"✗ _extract_remaining_questions() failed: expected 2, got {len(remaining)}")
            return False

        return True

    except Exception as e:
        print(f"✗ Engine parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_structure():
    """Test API endpoint structure."""
    print("\nTesting API structure...")

    try:
        from contextvault.api.thinking import router

        # Check that router has endpoints
        routes = router.routes

        endpoint_paths = [route.path for route in routes]

        expected_endpoints = [
            "/start",
            "/{session_id}",
            "/{session_id}/stream",
            "/{session_id}/questions",
            "/{session_id}/syntheses",
            "/{session_id}/stats",
            "/{session_id}/pause",
            "/{session_id}/resume",
            "/",
            "/{session_id}/export"
        ]

        missing_endpoints = []
        for expected in expected_endpoints:
            if expected not in endpoint_paths:
                missing_endpoints.append(expected)

        if not missing_endpoints:
            print(f"✓ All {len(expected_endpoints)} API endpoints defined")
        else:
            print(f"✗ Missing endpoints: {missing_endpoints}")
            return False

        return True

    except Exception as e:
        print(f"✗ API structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_integration():
    """Test config integration."""
    print("\nTesting config integration...")

    try:
        from contextvault.config import settings

        # Check thinking-specific settings
        if hasattr(settings, 'enable_extended_thinking'):
            print("✓ enable_extended_thinking setting exists")
        else:
            print("✗ enable_extended_thinking setting missing")
            return False

        if hasattr(settings, 'max_thinking_duration_minutes'):
            print(f"✓ max_thinking_duration_minutes: {settings.max_thinking_duration_minutes}")
        else:
            print("✗ max_thinking_duration_minutes setting missing")
            return False

        if hasattr(settings, 'synthesis_interval_seconds'):
            print(f"✓ synthesis_interval_seconds: {settings.synthesis_interval_seconds}")
        else:
            print("✗ synthesis_interval_seconds setting missing")
            return False

        return True

    except Exception as e:
        print(f"✗ Config integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Extended Thinking System - Comprehensive Tests")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Model Creation", test_model_creation),
        ("Session Methods", test_session_methods),
        ("Engine Parsing", test_engine_parsing),
        ("API Structure", test_api_structure),
        ("Config Integration", test_config_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed! Extended Thinking System is ready.")
        print("\nNext steps:")
        print("1. Create Alembic migration: alembic revision --autogenerate -m 'Add thinking tables'")
        print("2. Run migration: alembic upgrade head")
        print("3. Test with real Ollama: POST /api/thinking/start")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        sys.exit(1)
