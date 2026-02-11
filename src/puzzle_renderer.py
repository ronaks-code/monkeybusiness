"""Puzzle rendering using PIL/Pillow for deterministic image generation."""

import math
import logging
from typing import Tuple, List, Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from . import config
from .models import Puzzle, OPTION_LABELS

logger = logging.getLogger(__name__)


class PuzzleRenderer:
    """Renders Raven-style matrix puzzles as images using PIL."""
    
    def __init__(
        self,
        image_size: Optional[Tuple[int, int]] = None,
        background_color: Optional[Tuple[int, int, int]] = None
    ):
        """Initialize puzzle renderer.
        
        Args:
            image_size: Image dimensions (width, height)
            background_color: RGB background color
        """
        self.image_size = image_size or config.IMAGE_SIZE
        self.background_color = background_color or config.IMAGE_BACKGROUND
        self.margin = config.IMAGE_MARGIN
        self.grid_line_width = config.GRID_LINE_WIDTH
        self.shape_line_width = config.SHAPE_LINE_WIDTH
    
    def _parse_grid_logic(self, grid_logic: str) -> dict:
        """Parse grid_logic string into structured data.
        
        Args:
            grid_logic: String describing the puzzle pattern
            
        Returns:
            Dictionary with parsed grid information
        """
        # Simple parser for grid_logic format
        # Expected: "row1: elem1, elem2, elem3; row2: ...; rule: description"
        
        parsed = {
            "rows": [],
            "rule": "",
            "has_missing": False,
            "missing_position": None
        }
        
        try:
            # Split by semicolons
            parts = [p.strip() for p in grid_logic.split(";")]
            
            for part in parts:
                if ":" not in part:
                    continue
                
                key, value = part.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key.startswith("row"):
                    # Parse row elements
                    elements = [e.strip() for e in value.split(",")]
                    parsed["rows"].append(elements)
                    
                    # Check for missing element (marked with ?)
                    if "?" in elements:
                        parsed["has_missing"] = True
                        row_idx = len(parsed["rows"]) - 1
                        col_idx = elements.index("?")
                        parsed["missing_position"] = (row_idx, col_idx)
                
                elif key == "rule":
                    parsed["rule"] = value
        
        except Exception as e:
            logger.warning(f"Error parsing grid_logic: {e}. Using fallback.")
        
        # Fallback: if parsing failed, create a simple 3x3 grid
        if not parsed["rows"]:
            parsed["rows"] = [
                ["circle", "square", "triangle"],
                ["filled-circle", "filled-square", "filled-triangle"],
                ["large-circle", "large-square", "?"]
            ]
            parsed["has_missing"] = True
            parsed["missing_position"] = (2, 2)
            parsed["rule"] = "Pattern increases in complexity"
        
        return parsed
    
    def _draw_shape(
        self,
        draw: ImageDraw.ImageDraw,
        shape_desc: str,
        center: Tuple[int, int],
        size: int,
        color: Tuple[int, int, int] = (0, 0, 0)
    ):
        """Draw a single shape.
        
        Args:
            draw: PIL ImageDraw object
            shape_desc: Description of shape (e.g., "circle", "filled-square", "large-triangle")
            center: Center point (x, y)
            size: Base size for the shape
            color: RGB color for the shape
        """
        x, y = center
        
        # Parse shape description
        desc_lower = shape_desc.lower()
        is_filled = "filled" in desc_lower or "solid" in desc_lower
        is_large = "large" in desc_lower or "big" in desc_lower
        is_small = "small" in desc_lower or "tiny" in desc_lower
        
        # Adjust size
        if is_large:
            size = int(size * 1.4)
        elif is_small:
            size = int(size * 0.6)
        
        # Determine fill
        fill = color if is_filled else None
        outline = color
        width = self.shape_line_width
        
        # Draw based on shape type
        if "circle" in desc_lower or "ellipse" in desc_lower:
            bbox = [x - size//2, y - size//2, x + size//2, y + size//2]
            draw.ellipse(bbox, fill=fill, outline=outline, width=width)
        
        elif "square" in desc_lower or "rectangle" in desc_lower:
            bbox = [x - size//2, y - size//2, x + size//2, y + size//2]
            draw.rectangle(bbox, fill=fill, outline=outline, width=width)
        
        elif "triangle" in desc_lower:
            # Equilateral triangle pointing up
            h = int(size * 0.866)  # height = size * sqrt(3)/2
            points = [
                (x, y - h//2),  # top
                (x - size//2, y + h//2),  # bottom left
                (x + size//2, y + h//2)  # bottom right
            ]
            draw.polygon(points, fill=fill, outline=outline, width=width)
        
        elif "diamond" in desc_lower:
            points = [
                (x, y - size//2),  # top
                (x + size//2, y),  # right
                (x, y + size//2),  # bottom
                (x - size//2, y)  # left
            ]
            draw.polygon(points, fill=fill, outline=outline, width=width)
        
        elif "star" in desc_lower:
            # Simple 5-pointed star
            points = []
            for i in range(10):
                angle = math.pi/2 + i * math.pi/5
                r = size//2 if i % 2 == 0 else size//4
                px = x + int(r * math.cos(angle))
                py = y - int(r * math.sin(angle))
                points.append((px, py))
            draw.polygon(points, fill=fill, outline=outline, width=width)
        
        elif "?" in desc_lower or "missing" in desc_lower:
            # Draw a question mark or leave empty
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except:
                font = ImageFont.load_default()
            draw.text((x, y), "?", fill=color, anchor="mm", font=font)
        
        else:
            # Default: draw a circle
            bbox = [x - size//2, y - size//2, x + size//2, y + size//2]
            draw.ellipse(bbox, fill=fill, outline=outline, width=width)
    
    def _render_grid(
        self,
        image: Image.Image,
        grid_data: dict,
        grid_bbox: Tuple[int, int, int, int]
    ):
        """Render the puzzle grid.
        
        Args:
            image: PIL Image to draw on
            grid_data: Parsed grid data
            grid_bbox: Bounding box for grid (x1, y1, x2, y2)
        """
        draw = ImageDraw.Draw(image)
        x1, y1, x2, y2 = grid_bbox
        
        rows = grid_data["rows"]
        n_rows = len(rows)
        n_cols = max(len(row) for row in rows) if rows else 3
        
        # Calculate cell dimensions
        cell_width = (x2 - x1) // n_cols
        cell_height = (y2 - y1) // n_rows
        
        # Draw grid lines
        for i in range(n_rows + 1):
            y = y1 + i * cell_height
            draw.line([(x1, y), (x2, y)], fill=(0, 0, 0), width=self.grid_line_width)
        
        for j in range(n_cols + 1):
            x = x1 + j * cell_width
            draw.line([(x, y1), (x, y2)], fill=(0, 0, 0), width=self.grid_line_width)
        
        # Draw shapes in each cell
        shape_size = min(cell_width, cell_height) // 3
        
        for i, row in enumerate(rows):
            for j, element in enumerate(row):
                if not element:
                    continue
                
                # Calculate cell center
                cell_x = x1 + j * cell_width + cell_width // 2
                cell_y = y1 + i * cell_height + cell_height // 2
                
                # Draw shape
                self._draw_shape(draw, element, (cell_x, cell_y), shape_size)
    
    def _render_options(
        self,
        image: Image.Image,
        options: List[str],
        options_bbox: Tuple[int, int, int, int]
    ):
        """Render answer options (5-8 options) in a natural 2-row grid.
        
        Args:
            image: PIL Image to draw on
            options: List of 5-8 option strings (e.g. "A: large-triangle")
            options_bbox: Bounding box for options area (x1, y1, x2, y2)
        """
        draw = ImageDraw.Draw(image)
        x1, y1, x2, y2 = options_bbox
        n = len(options)
        # 2 rows; columns = ceil(n/2) for balanced layout (5->3, 6->3, 7->4, 8->4)
        ncols = (n + 1) // 2
        nrows = 2
        cell_width = (x2 - x1) // ncols
        cell_height = (y2 - y1) // nrows
        
        # Slightly smaller shapes and font when more options
        shape_size = min(cell_width, cell_height) // (4 if n <= 6 else 5)
        font_size = 32 if n <= 6 else 26
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()
        
        # Card-style colors: light fill, subtle border
        cell_fill = (248, 248, 250)
        cell_outline = (180, 180, 188)
        label_color = (60, 60, 68)
        
        for idx, option in enumerate(options):
            label = OPTION_LABELS[idx] if idx < len(OPTION_LABELS) else str(idx + 1)
            col = idx % ncols
            row = idx // ncols
            cx1 = x1 + col * cell_width + 4
            cy1 = y1 + row * cell_height + 4
            cx2 = cx1 + cell_width - 8
            cy2 = cy1 + cell_height - 8
            
            # Rounded-rectangle effect: draw filled rect then outline
            draw.rectangle([cx1, cy1, cx2, cy2], fill=cell_fill, outline=cell_outline, width=2)
            draw.text((cx1 + 12, cy1 + 8), label + ":", fill=label_color, font=font)
            
            if ":" in option:
                shape_desc = option.split(":", 1)[1].strip()
            else:
                shape_desc = option
            center_x = (cx1 + cx2) // 2
            center_y = (cy1 + cy2) // 2 + (font_size // 2)
            self._draw_shape(draw, shape_desc, (center_x, center_y), shape_size)
    
    def render(self, puzzle: Puzzle, output_path: Optional[Path] = None) -> Image.Image:
        """Render a puzzle to an image (natural quiz UI, 5-8 options)."""
        # Softer background for a more engaging, less “test-like” look
        bg = config.IMAGE_BACKGROUND_QUIZ
        image = Image.new("RGB", self.image_size, bg)
        draw = ImageDraw.Draw(image)
        width, height = self.image_size
        
        # Natural question line (use puzzle text if short, else default)
        question = (puzzle.question_text or "").strip()
        if not question or len(question) > 60:
            question = "Which one completes the pattern?"
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 46)
        except Exception:
            font_large = ImageFont.load_default()
        text_y = self.margin + 10
        draw.text((width // 2, text_y), question, fill=(40, 40, 48), anchor="mt", font=font_large)
        
        grid_data = self._parse_grid_logic(puzzle.grid_logic)
        # Leave space for 2 rows of options (flexible height)
        options_height = 340 if len(puzzle.options) <= 6 else 380
        grid_top = text_y + 72
        grid_bottom = height - options_height
        grid_bbox = (self.margin, grid_top, width - self.margin, grid_bottom)
        options_bbox = (self.margin, grid_bottom + 16, width - self.margin, height - self.margin)
        
        self._render_grid(image, grid_data, grid_bbox)
        self._render_options(image, puzzle.options, options_bbox)
        
        if output_path:
            image.save(output_path, "PNG")
            logger.info(f"Rendered puzzle image: {output_path}")
        return image
