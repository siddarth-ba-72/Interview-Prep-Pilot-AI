# AI Service Guardrails

This document describes the scope guardrails implemented in the AI service to ensure it only responds to tech and interview-related questions.

## Overview

The AI service now enforces strict scope validation across all endpoints to prevent it from answering off-topic questions (politics, sports, cooking, entertainment, etc.). Instead, it responds with a friendly message redirecting users to ask about technical topics.

## Implementation

### Scope Validator Module (`app/scope_validator.py`)

The validator uses a two-tier approach:

#### 1. Keyword-Based Detection (Fast)
- **Tech Keywords**: 169 curated keywords covering:
  - Programming languages (Python, Java, JavaScript, Rust, Go, etc.)
  - Frameworks (React, Spring Boot, Django, Express, etc.)
  - Core CS concepts (algorithms, data structures, design patterns, etc.)
  - Technologies (cloud platforms, databases, DevOps tools, etc.)
  - Interview-related terms

- **Blocked Topics**: 24 explicitly blocked non-tech topics:
  - Politics, sports, entertainment, cooking, dating, relationships, history, art, etc.

#### 2. LLM-Based Validation (Edge Cases)
- For messages that don't match keywords, a lightweight LLM call validates scope
- Asks the model: "Is this message tech/interview related?"
- Gracefully handles validation errors (allows the message through if validation fails)

### Integration Points

**Learn Mode** (`app/routers/learn.py`):
- Validates topic name when starting/continuing a session
- Validates user's latest message before responding
- Streams error message to client if out of scope

**Test Mode** (`app/routers/test.py`):
- Validates topic name for both `/generate` and `/evaluate` endpoints
- Returns HTTP 400 error with scope message if invalid

**Interview Mode** (`app/routers/interview.py`):
- Validates topic name for `/plan`, `/next-turn`, and `/generate-report` endpoints
- Returns HTTP 400 error with scope message if invalid

## Response Messages

When a request is out of scope, users receive:

```
I'm specifically designed to help with technical interview preparation and 
engineering topics. I cannot answer questions about {topic}. 
Please ask me about programming languages, data structures, algorithms, 
system design, or other technical interview topics instead!
```

## Examples

### Valid Topics (Will be processed)
✓ Python
✓ Data Structures
✓ System Design
✓ Kubernetes
✓ Machine Learning
✓ JavaScript
✓ Spring Boot

### Invalid Topics (Will be blocked)
✗ Politics
✗ Sports
✗ Cooking
✗ Entertainment
✗ Fashion
✗ Dating

## Testing

Run the included test script to verify guardrails:
```bash
python3 -m pytest test_guardrails.py
```

Or manually test with:
```bash
python3 << 'EOF'
from app.scope_validator import _is_tech_related
assert _is_tech_related("Python programming") == True
assert _is_tech_related("cooking recipes") == False
EOF
```

## Performance Impact

- **Keyword check**: ~0ms (simple string matching)
- **LLM validation**: ~100-500ms (only for ambiguous messages)
- **Memory overhead**: ~15KB (keyword sets)

## Future Enhancements

1. Add category-based blocking (e.g., block entire categories like "sports")
2. Implement rate limiting on LLM validation calls
3. Log blocked requests for monitoring abuse patterns
4. Add configuration for dynamic keyword lists
5. Implement user preference settings for scope strictness
