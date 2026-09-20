#!/usr/bin/env python3
"""
Test script to verify guardrails are working correctly.
Tests both keyword-based and LLM-based validation.
"""
import asyncio
from app.scope_validator import validate_topic_scope, validate_user_message_scope, _is_tech_related

async def run_tests():
    print("=" * 60)
    print("Testing Guardrails")
    print("=" * 60)

    # Test 1: Tech-related topics (should pass)
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

    # Test 2: Out-of-scope topics (should fail)
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

    # Test 3: User messages in tech context (should pass)
    print("\n[TEST 3] Tech-related messages (should be VALID)")
    tech_messages = [
        "What is a binary search tree?",
        "How do you optimize database queries?",
        "Explain the difference between Docker and Kubernetes",
        "What's the time complexity of merge sort?",
    ]
    for msg in tech_messages:
        is_valid, error = await validate_user_message_scope("Python", msg)
        status = "✓ PASS" if is_valid else "✗ FAIL"
        print(f"  {status}: '{msg}'")

    # Test 4: Out-of-scope messages (should fail)
    print("\n[TEST 4] Out-of-scope messages (should be INVALID)")
    out_of_scope_messages = [
        "Tell me about the latest movies",
        "What's your favorite sports team?",
        "Give me cooking recipes",
        "Who's your favorite celebrity?",
    ]
    for msg in out_of_scope_messages:
        is_valid, error = await validate_user_message_scope("Python", msg)
        status = "✗ FAIL" if is_valid else "✓ PASS"
        print(f"  {status}: '{msg}'")
        if error and not is_valid:
            print(f"       Error message: {error[:60]}...")

    # Test 5: Keyword detection
    print("\n[TEST 5] Keyword detection (quick check)")
    keyword_tests = [
        ("python programming", True),
        ("data structures", True),
        ("machine learning", True),
        ("politics and elections", False),
        ("sports teams", False),
        ("cooking recipes", False),
    ]
    for text, expected in keyword_tests:
        result = _is_tech_related(text)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text}' -> {result} (expected {expected})")

    print("\n" + "=" * 60)
    print("Guardrails testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
