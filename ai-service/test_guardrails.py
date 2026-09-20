#!/usr/bin/env python3
"""
Manual smoke test for topic scope classification.

Scope enforcement for Learn Mode chat now happens inside the model itself (see
prompts.SCOPE_GUARD) rather than a separate keyword gate, so it isn't something
this script can exercise without actually streaming a chat turn. This script
covers the one remaining pre-check: validate_topic_scope(), used before
generating structured content (test questions, interview plans) where there is
no conversational turn for the model to decline within.

Requires a configured LLM_API_KEY - makes real model calls.
"""
import asyncio
from app.scope_validator import validate_topic_scope


async def run_tests():
    print("=" * 60)
    print("Testing topic scope classification")
    print("=" * 60)

    print("\n[TEST 1] Tech-related topics (should be VALID)")
    tech_topics = [
        "Python",
        "JavaScript",
        "Data Structures",
        "System Design",
        "Kubernetes",
        "React",
        "Spring Boot",
        "Machine Learning",
    ]
    for topic in tech_topics:
        is_valid, error = await validate_topic_scope(topic)
        status = "✓ PASS" if is_valid else "✗ FAIL"
        print(f"  {status}: '{topic}'")

    print("\n[TEST 2] Out-of-scope topics (should be INVALID)")
    out_of_scope_topics = [
        "Politics",
        "Sports",
        "Cooking",
        "Entertainment",
        "Fashion",
        "Dating Advice",
    ]
    for topic in out_of_scope_topics:
        is_valid, error = await validate_topic_scope(topic)
        status = "✗ FAIL" if is_valid else "✓ PASS"
        print(f"  {status}: '{topic}'")
        if error:
            print(f"       Error message: {error[:60]}...")

    print("\n" + "=" * 60)
    print("Scope classification testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
