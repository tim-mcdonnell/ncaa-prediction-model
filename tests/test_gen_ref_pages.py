"""Test the documentation reference pages generator script."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the docs directory to the Python path so we can import gen_ref_pages
sys.path.append(str(Path(__file__).parent.parent / "docs"))

# Now we can import the module
import gen_ref_pages


class TestGenRefPages(unittest.TestCase):
    """Test the gen_ref_pages.py script that generates API reference docs."""
    
    def test_generates_file_structure_from_python_modules(self):
        """
        Test that the script creates the expected file structure from Python modules.
        
        This test verifies the script generates the correct output paths and builds
        the appropriate navigation structure. It doesn't validate content processing
        since that would require MkDocStrings integration.
        """
        # Create a temporary directory structure with test Python files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a source directory with Python files
            src_dir = temp_path / "src"
            src_dir.mkdir()
            
            # Create a test module
            module_dir = src_dir / "test_module"
            module_dir.mkdir(parents=True)
            
            # Create __init__.py
            with open(module_dir / "__init__.py", "w") as f:
                f.write('"""Test module for documentation."""\n')
            
            # Create a test file
            with open(module_dir / "test_file.py", "w") as f:
                f.write('''"""Test file docstring."""

class TestClass:
    """Test class docstring."""
    
    def test_method(self):
        """Test method docstring."""
        pass
''')
            
            # Mock the mkdocs_gen_files module
            mock_nav = MagicMock()
            mock_open_files = {}
            
            def mock_file_open(path, mode):
                mock_file = MagicMock()
                mock_open_files[str(path)] = []
                
                def mock_write(content):
                    mock_open_files[str(path)].append(content)
                
                mock_file.write.side_effect = mock_write
                mock_file.__enter__ = MagicMock(return_value=mock_file)
                mock_file.__exit__ = MagicMock(return_value=None)
                
                return mock_file
                
            mock_gen_files = MagicMock()
            mock_gen_files.open.side_effect = mock_file_open
            mock_gen_files.Nav.return_value = mock_nav
            
            # Create a modified version of the generate_reference_docs function
            # that uses our temporary directory instead of the actual src directory
            original_function = gen_ref_pages.generate_reference_docs
            
            def modified_generate_docs():
                # Store the original Path constructor
                original_path = Path
                
                # Create a patched Path that resolves "src" to our temp directory
                class PatchedPath(original_path):
                    def __new__(cls, *args, **kwargs):
                        path_str = str(args[0]) if args else ""
                        if path_str == "src":
                            return original_path(src_dir)
                        return original_path.__new__(original_path, *args, **kwargs)
                
                # Patch the Path class in gen_ref_pages module
                with patch('gen_ref_pages.Path', PatchedPath):
                    original_function()
            
            # Run the modified function with our mocks
            with patch("gen_ref_pages.mkdocs_gen_files", mock_gen_files):
                modified_generate_docs()
            
            # Debug: Print all paths that were created
            print("Files that would be created:")
            for path, contents in mock_open_files.items():
                content = "".join(contents)
                print(f"  - {path} ({len(content)} chars)")
                if "test_file.md" in path:
                    print("    Content preview:")
                    print("    " + content[:200] + "..." if len(content) > 200 else content)
            
            # Verify that test_file.md would have been created
            self.assertTrue(
                any("test_module/test_file.md" in path for path in mock_open_files.keys()),
                "Expected reference file was not created"
            )
            
            # Find the test_file.md content
            test_file_paths = [path for path in mock_open_files.keys() 
                              if "test_module/test_file.md" in path]
            
            # Just verify the file path was created - content verification
            # would require the actual mkdocstrings plugin to be working
            self.assertTrue(len(test_file_paths) > 0, "Test file markdown was not created")
            
            # Verify that the nav file was created
            self.assertTrue(
                any("SUMMARY.md" in path for path in mock_open_files.keys()),
                "Nav file was not created"
            )
            
            # Verify the Nav object was built and used
            mock_nav.build_literate_nav.assert_called_once()


if __name__ == "__main__":
    unittest.main() 