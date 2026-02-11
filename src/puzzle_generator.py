"""Puzzle generation using LLM (OpenAI API)."""

import json
import logging
from typing import List, Optional
from openai import OpenAI

from . import config
from .models import Puzzle, validate_puzzle, get_puzzle_schema, MIN_OPTIONS, MAX_OPTIONS

logger = logging.getLogger(__name__)


class PuzzleGenerator:
    """Generates Raven-style matrix puzzles using LLM."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize puzzle generator.
        
        Args:
            api_key: OpenAI API key (defaults to config.OPENAI_API_KEY)
            model: Model name (defaults to config.OPENAI_MODEL)
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.model = model or config.OPENAI_MODEL
        # gpt-5-nano only supports temperature=1; use 1 for that model
        if self.model and "gpt-5-nano" in self.model.lower():
            self.temperature = 1.0
            logger.debug("Using temperature=1 for gpt-5-nano (only supported value)")
        else:
            self.temperature = config.OPENAI_TEMPERATURE
        self.max_retries = config.OPENAI_MAX_RETRIES
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for puzzle generation (IQ-style, harder, more options)."""
        schema = get_puzzle_schema()
        
        return f"""You are an expert designer of IQ-style and Raven's Progressive Matrices puzzles. Your puzzles are used in short-form video content where viewers expect a real challenge—they should have to stop, look again, and think.

Generate matrix reasoning puzzles that feel like real IQ-test items: multi-step logic, subtle patterns, and several plausible wrong answers so solvers must eliminate options rather than guess.

IMPORTANT: Your response must be ONLY valid JSON matching this exact schema:

{json.dumps(schema, indent=2)}

Difficulty and thinking required:
- The rule(s) should not be obvious at first glance. Combine at least two dimensions (e.g., shape + fill + position, or rotation + count + size).
- Patterns can work by row, by column, or by diagonal. Consider symmetry, progression, or substitution rules.
- question_text should be short and natural (e.g., "Which one completes the pattern?", "What goes in the empty cell?", "Find the missing piece."). Do not sound like a textbook.

grid_logic format:
- Use: "row1: [elements]; row2: [elements]; row3: [elements]; rule: [clear pattern description]"
- Elements: shapes (circle, square, triangle, diamond, star), modifiers (filled, large, small, rotated-90), and "?" for the missing cell.
- Rule should describe what actually determines the answer (e.g., "row: shape cycles; column: fill and size both increase").

Options ({MIN_OPTIONS} to {MAX_OPTIONS}):
- Provide between {MIN_OPTIONS} and {MAX_OPTIONS} distinct options (labeled A, B, C, ...). Use 6 or 7 options when in doubt so the quiz feels substantial.
- Include plausible distractors: options that match one dimension of the rule but not another, or that look right at a glance.
- Only one option should be fully correct. Others should be "close" so viewers have to go back and verify.
- Format each option as "LABEL: shape-description" (e.g., "A: large-filled-triangle", "B: small-circle").

Generate puzzles that are:
- Genuinely challenging (IQ-style): require 15–30 seconds of study for a strong reasoner
- Visually clear and logically consistent
- Natural wording, not stiff or academic

Return ONLY the JSON object, no additional text or markdown."""

    def _get_user_prompt(self, difficulty: int) -> str:
        """Get user prompt for specific difficulty level (IQ-style, harder)."""
        # Bias toward 6-7 options for a natural "many choices" feel; higher difficulty = more options.
        n_options = min(MAX_OPTIONS, max(MIN_OPTIONS, 5 + (difficulty // 3)))
        return (
            f"Generate a matrix reasoning puzzle with difficulty {difficulty}/10. "
            f"Include {n_options} answer options (A through {chr(ord('A') + n_options - 1)}) with plausible distractors. "
            f"The pattern should require real thought (multi-step or subtle). Return only valid JSON."
        )
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            
        Returns:
            Response text from LLM
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}  # Enforce JSON mode
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def generate_puzzle(self, difficulty: Optional[int] = None, puzzle_id: Optional[str] = None) -> Optional[Puzzle]:
        """Generate a single puzzle.
        
        Args:
            difficulty: Difficulty level 1-10 (random if not specified)
            puzzle_id: Optional custom puzzle ID
            
        Returns:
            Validated Puzzle object or None if generation fails
        """
        import random
        
        if difficulty is None:
            difficulty = random.randint(3, 7)  # Default to medium difficulty
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(difficulty)
        
        # Try up to max_retries times
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Generating puzzle (attempt {attempt}/{self.max_retries}, difficulty={difficulty})")
                
                # Call LLM
                response_text = self._call_llm(system_prompt, user_prompt)
                
                # Parse JSON
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON response (attempt {attempt}): {e}")
                    logger.debug(f"Response text: {response_text[:200]}...")
                    continue
                
                # Override ID if provided
                if puzzle_id:
                    data["id"] = puzzle_id
                
                # Validate
                puzzle = validate_puzzle(data)
                logger.info(f"Successfully generated puzzle: {puzzle.id}")
                return puzzle
                
            except ValueError as e:
                logger.warning(f"Validation failed (attempt {attempt}): {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error during puzzle generation (attempt {attempt}): {e}")
                continue
        
        # All retries exhausted
        logger.error(f"Failed to generate valid puzzle after {self.max_retries} attempts")
        return None
    
    def generate_puzzles(
        self,
        count: int,
        start_difficulty: Optional[int] = None,
        start_index: int = 1
    ) -> List[Puzzle]:
        """Generate multiple puzzles.
        
        Args:
            count: Number of puzzles to generate
            start_difficulty: Starting difficulty (increments for each puzzle)
            start_index: Numeric index for the first generated puzzle ID
            
        Returns:
            List of successfully generated Puzzle objects
        """
        if start_index < 1:
            raise ValueError(f"start_index must be >= 1, got: {start_index}")

        puzzles = []
        
        for i in range(count):
            # Calculate difficulty (cycle through 1-10 or use provided start)
            if start_difficulty is not None:
                difficulty = ((start_difficulty - 1 + i) % 10) + 1
            else:
                difficulty = None  # Let generate_puzzle choose randomly
            
            # Generate puzzle ID
            puzzle_id = f"puzzle_{start_index + i:03d}"
            
            try:
                puzzle = self.generate_puzzle(difficulty=difficulty, puzzle_id=puzzle_id)
                if puzzle:
                    puzzles.append(puzzle)
                    logger.info(f"Progress: {len(puzzles)}/{count} puzzles generated")
                else:
                    logger.warning(f"Skipping puzzle {i+1} due to generation failure")
            except Exception as e:
                logger.error(f"Error generating puzzle {i+1}: {e}")
                continue
        
        logger.info(f"Successfully generated {len(puzzles)}/{count} puzzles")
        return puzzles
