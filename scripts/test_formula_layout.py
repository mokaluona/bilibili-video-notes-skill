# Compatibility entry point; canonical tests are discovered under tests/.
import runpy
from pathlib import Path
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tests' / 'test_formula_layout.py'), run_name='__main__')
