import os
import sys
import py_compile
import logging

# Configure basic logging for visibility
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("code_validator")


def validate_python_files(project_root: str) -> bool:
    """
    Recursively scans the directory and compiles all Python files.
    Returns True if all files compile without syntax errors, False otherwise.
    """
    logger.info(f"Starting static syntax verification inside: {project_root}")
    
    python_files = []
    for root, dirs, files in os.walk(project_root):
        # Exclude directories like virtual envs and caches
        dirs[:] = [d for d in dirs if d not in [".git", "venv", ".venv", "__pycache__"]]
        
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
                
    if not python_files:
        logger.warning("No Python files found for validation.")
        return True
        
    logger.info(f"Discovered {len(python_files)} Python file(s) to validate.")
    
    failures = 0
    total_lines = 0
    
    for filepath in python_files:
        rel_path = os.path.relpath(filepath, project_root)
        try:
            # Check syntax via compile
            py_compile.compile(filepath, doraise=True)
            
            # Count lines for statistics
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = len(f.readlines())
                total_lines += lines
                
            logger.info(f"  [PASS] {rel_path} ({lines} lines)")
        except py_compile.PyCompileError as err:
            logger.error(f"  [FAIL] Syntax error in {rel_path}: {err.msg}")
            failures += 1
        except Exception as e:
            logger.error(f"  [FAIL] Error reading {rel_path}: {e}")
            failures += 1
            
    logger.info("--------------------------------------------------")
    logger.info(f"Validation summary: Checked {len(python_files)} files ({total_lines} lines).")
    
    if failures > 0:
        logger.error(f"Static validation failed! Encountered {failures} file syntax error(s).")
        return False
        
    logger.info("Static validation succeeded. All code files compile successfully.")
    return True


if __name__ == "__main__":
    # Use current working directory as default project root
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    success = validate_python_files(root_dir)
    if not success:
        sys.exit(1)
    sys.exit(0)
