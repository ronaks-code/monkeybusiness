"""Data models and validation for puzzle objects."""

from dataclasses import dataclass, asdict
from typing import Literal, List
import json

# Option count: 5-8 for harder, more natural quizzes (people have to think and eliminate)
MIN_OPTIONS = 5
MAX_OPTIONS = 8
OPTION_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H"]


def _extract_option_label(option: str) -> str:
    """Extract option label from strings like 'A: foo'."""
    if not isinstance(option, str):
        return ""
    prefix = option.split(":", 1)[0].strip().upper()
    if len(prefix) == 1 and prefix in OPTION_LABELS:
        return prefix
    return ""


@dataclass
class Puzzle:
    """Represents a single Raven-style puzzle with metadata.
    
    Attributes:
        id: Unique identifier for the puzzle
        puzzle_type: Type of puzzle (currently only matrix_reasoning)
        difficulty: Difficulty level from 1 (easiest) to 10 (hardest)
        question_text: Optional text description of the puzzle
        grid_logic: Structured description of visual pattern rules
        options: List of 5-8 answer options (A through H)
        correct_answer: The correct answer (must be one of the options)
        explanation: Explanation of the solution logic
    """
    id: str
    puzzle_type: Literal["matrix_reasoning"]
    difficulty: int
    question_text: str
    grid_logic: str
    options: List[str]
    correct_answer: str
    explanation: str

    def to_dict(self) -> dict:
        """Convert puzzle to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert puzzle to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def validate_puzzle(data: dict) -> Puzzle:
    """Validate puzzle data and return a Puzzle object.
    
    Args:
        data: Dictionary containing puzzle fields from LLM
        
    Returns:
        Validated Puzzle object
        
    Raises:
        ValueError: If validation fails
    """
    # Check required fields
    required_fields = [
        "id", "puzzle_type", "difficulty", "question_text",
        "grid_logic", "options", "correct_answer", "explanation"
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    # Validate puzzle_type
    if data["puzzle_type"] not in ["matrix_reasoning"]:
        raise ValueError(f"Invalid puzzle_type: {data['puzzle_type']}")
    
    # Validate difficulty range
    difficulty = data["difficulty"]
    if not isinstance(difficulty, int) or not 1 <= difficulty <= 10:
        raise ValueError(f"Difficulty must be an integer from 1-10, got: {difficulty}")
    
    # Validate options (5-8 for harder, natural quizzes)
    options = data["options"]
    if not isinstance(options, list) or not (MIN_OPTIONS <= len(options) <= MAX_OPTIONS):
        n = len(options) if isinstance(options, list) else 0
        raise ValueError(f"Options must be a list of {MIN_OPTIONS}-{MAX_OPTIONS} items, got: {n}")
    for idx, option in enumerate(options):
        if not isinstance(option, str) or not option.strip():
            raise ValueError(f"Option {idx + 1} must be a non-empty string")
    
    # Validate/normalize correct_answer.
    # Accept either exact option string, or label-only answers like "A" when
    # options are in "A: ..." format.
    correct_answer = data["correct_answer"]
    if not isinstance(correct_answer, str) or not correct_answer.strip():
        raise ValueError("Field 'correct_answer' must be a non-empty string")

    normalized_correct_answer = correct_answer.strip()
    if normalized_correct_answer not in options:
        label_to_option = {}
        for option in options:
            label = _extract_option_label(option)
            if label and label not in label_to_option:
                label_to_option[label] = option

        answer_label = _extract_option_label(normalized_correct_answer)
        if not answer_label:
            upper = normalized_correct_answer.upper()
            if len(upper) == 1 and upper in OPTION_LABELS:
                answer_label = upper

        mapped = label_to_option.get(answer_label)
        if mapped:
            normalized_correct_answer = mapped
        else:
            raise ValueError(f"correct_answer '{correct_answer}' not found in options: {options}")
    
    # Validate string fields are not empty
    string_fields = ["id", "question_text", "grid_logic", "explanation"]
    for field in string_fields:
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"Field '{field}' must be a non-empty string")
    
    # Create and return Puzzle object
    return Puzzle(
        id=data["id"],
        puzzle_type=data["puzzle_type"],
        difficulty=data["difficulty"],
        question_text=data["question_text"],
        grid_logic=data["grid_logic"],
        options=data["options"],
        correct_answer=normalized_correct_answer,
        explanation=data["explanation"]
    )


def get_puzzle_schema() -> dict:
    """Return JSON schema for puzzle structure.
    
    This can be included in LLM prompts to ensure correct output format.
    """
    return {
        "type": "object",
        "required": [
            "id", "puzzle_type", "difficulty", "question_text",
            "grid_logic", "options", "correct_answer", "explanation"
        ],
        "properties": {
            "id": {
                "type": "string",
                "description": "Unique identifier (e.g., puzzle_001)"
            },
            "puzzle_type": {
                "type": "string",
                "enum": ["matrix_reasoning"],
                "description": "Type of puzzle"
            },
            "difficulty": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "Difficulty level from 1 (easy) to 10 (hard)"
            },
            "question_text": {
                "type": "string",
                "description": "Optional question or instruction text"
            },
            "grid_logic": {
                "type": "string",
                "description": "Structured description of the pattern (e.g., 'row1: circle, square, triangle; row2: filled circle, filled square, filled triangle; row3: large circle, large square, ?; rule: size increases per row')"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": MIN_OPTIONS,
                "maxItems": MAX_OPTIONS,
                "description": "Five to eight answer options (labeled A through H). Include plausible distractors so solvers must think and eliminate."
            },
            "correct_answer": {
                "type": "string",
                "description": "The correct answer (must be one of the options)"
            },
            "explanation": {
                "type": "string",
                "description": "Explanation of the solution"
            }
        }
    }
