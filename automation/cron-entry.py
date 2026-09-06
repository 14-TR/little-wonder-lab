"""Operator copies this small entrypoint to default-profile scripts, not a symlink."""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path('/Users/tr/little-wonder-lab')
os.chdir(ROOT)
os.environ['TERMINAL_CWD'] = str(ROOT)
sys.path.insert(0, str(ROOT / 'scripts'))
sys.argv = [str(ROOT / 'scripts/autonomy.py'), 'run']
runpy.run_path(sys.argv[0], run_name='__main__')
