import json
import uuid
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from schemas import (
    GenerateTestQuestionsRequest, GenerateTestQuestionsResponse, TestQuestion, Section,
    EvaluateAnswersRequest, EvaluateAnswersResponse, QuestionEvaluation
)
from prompts import build_test_generation_messages, build_test_evaluation_messages
from llm import call_llm
from auth import require_internal_api_key_or_user_id

router = APIRouter(prefix="/ai/test", tags=["test"])


@router.post("/generate", response_model=GenerateTestQuestionsResponse)
async def generate_questions(request: GenerateTestQuestionsRequest, _=Depends(require_internal_api_key_or_user_id)):
    """Generate 20 test questions (10 MCQ + 10 SUBJECTIVE) for a topic."""
    try:
        messages = build_test_generation_messages(request.topic_name)
        response_text = await call_llm(messages)
        
        # Parse JSON response
        try:
            data = json.loads(response_text)
            questions_data = data.get("questions", [])
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse AI response")
        
        # Validate and convert to Pydantic models
        questions = []
        for q in questions_data:
            # Ensure questionId is a string UUID
            if not q.get("questionId"):
                q["questionId"] = str(uuid.uuid4())
            
            question = TestQuestion(
                question_id=q.get("questionId"),
                section=Section(q.get("section", "MCQ")),
                text=q.get("text", ""),
                options=q.get("options"),
                correct_option=q.get("correctOption"),
                model_answer=q.get("modelAnswer")
            )
            questions.append(question)
        
        return GenerateTestQuestionsResponse(questions=questions)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating questions: {str(e)}")


@router.post("/evaluate", response_model=EvaluateAnswersResponse)
async def evaluate_answers(request: EvaluateAnswersRequest, _=Depends(require_internal_api_key_or_user_id)):
    """Evaluate test answers and provide per-question feedback."""
    try:
        # Convert request to dict for prompts, including questionId
        answers = [
            {
                "questionId": a.question_id,
                "section": a.section.value,
                "question": a.question,
                "correctAnswer": a.correct_answer,
                "userAnswer": a.user_answer
            }
            for a in request.answers
        ]
        
        messages = build_test_evaluation_messages(request.topic_name, answers)
        response_text = await call_llm(messages)
        
        # Parse JSON response
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse AI evaluation response")
        
        # Convert per-question evaluations
        # Match by questionId from the response
        per_question = []
        for q_eval in data.get("perQuestion", []):
            question_id = q_eval.get("questionId")
            if not question_id:
                # Fallback: use index-based matching if questionId is missing
                continue
            eval_obj = QuestionEvaluation(
                question_id=question_id,
                is_correct=q_eval.get("isCorrect", False),
                evaluation=q_eval.get("evaluation", "")
            )
            per_question.append(eval_obj)
        
        return EvaluateAnswersResponse(
            per_question=per_question,
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating answers: {str(e)}")
