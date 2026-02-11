"""Basic tests for puzzle video pipeline components."""

import sys
from pathlib import Path

def test_models():
    """Test puzzle models and validation."""
    print("Testing models...")
    from src.models import Puzzle, validate_puzzle, get_puzzle_schema
    
    # Valid puzzle data
    valid_data = {
        "id": "test_001",
        "puzzle_type": "matrix_reasoning",
        "difficulty": 5,
        "question_text": "Complete the pattern",
        "grid_logic": "row1: circle, square, triangle; rule: simple pattern",
        "options": ["A", "B", "C", "D", "E"],
        "correct_answer": "A",
        "explanation": "Test explanation"
    }
    
    try:
        puzzle = validate_puzzle(valid_data)
        assert puzzle.id == "test_001"
        assert puzzle.difficulty == 5
        print("✓ Puzzle validation works")
    except Exception as e:
        print(f"✗ Puzzle validation failed: {e}")
        return False
    
    # Test schema
    schema = get_puzzle_schema()
    assert "properties" in schema
    print("✓ Schema generation works")
    
    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    from src import config
    
    try:
        # Check basic config values
        assert config.VIDEO_RESOLUTION == (1080, 1920)
        assert config.IMAGE_SIZE == (1080, 1350)
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False
    
    return True

def test_asset_manager():
    """Test asset manager."""
    print("\nTesting asset manager...")
    from src.asset_manager import AssetManager
    import tempfile
    from PIL import Image
    
    try:
        # Use temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = AssetManager(Path(tmpdir))
            
            # Test image save
            test_image = Image.new("RGB", (100, 100), (255, 0, 0))
            image_path = manager.save_image("test_img", test_image)
            assert image_path.exists()
            
            # Test metadata save
            from src.models import Puzzle
            test_puzzle = Puzzle(
                id="test",
                puzzle_type="matrix_reasoning",
                difficulty=5,
                question_text="Test",
                grid_logic="test",
                options=["A", "B", "C", "D", "E"],
                correct_answer="A",
                explanation="Test"
            )
            metadata_path = manager.save_metadata("test_meta", test_puzzle)
            assert metadata_path.exists()
            
            print("✓ Asset manager works")
    except Exception as e:
        print(f"✗ Asset manager failed: {e}")
        return False
    
    return True

def test_renderer():
    """Test puzzle renderer."""
    print("\nTesting puzzle renderer...")
    from src.puzzle_renderer import PuzzleRenderer
    from src.models import Puzzle
    import tempfile
    
    try:
        renderer = PuzzleRenderer()
        
        test_puzzle = Puzzle(
            id="render_test",
            puzzle_type="matrix_reasoning",
            difficulty=3,
            question_text="Test puzzle",
            grid_logic="row1: circle, square, triangle; row2: filled-circle, filled-square, ?; rule: pattern",
            options=["A: filled-triangle", "B: circle", "C: square", "D: triangle", "E: diamond", "F: star"],
            correct_answer="A: filled-triangle",
            explanation="The pattern adds fill to shapes"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.png"
            image = renderer.render(test_puzzle, output_path)
            assert output_path.exists()
            print("✓ Puzzle renderer works")
    except Exception as e:
        print(f"✗ Puzzle renderer failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Basic Component Tests")
    print("=" * 60)
    
    tests = [
        ("Models", test_models),
        ("Config", test_config),
        ("Asset Manager", test_asset_manager),
        ("Renderer", test_renderer),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"✗ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All basic tests passed!")
        print("\nNote: These are basic component tests.")
        print("For full pipeline test, run: python -m src.main_pipeline --count 1")
        return 0
    else:
        print("\n✗ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
