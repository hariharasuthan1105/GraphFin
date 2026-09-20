"""
GraphFin Research Experiment Runner CLI module.
Allows invocation via:
  python -m app.research_runner --dataset-id <ID>
or
  python -m backend.app.research_runner --dataset-id <ID>
"""
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Support direct import whether running as app.research_runner or backend.app.research_runner
try:
    from .services.research_runner import main, research_runner
except ImportError:
    from backend.app.services.research_runner import main, research_runner

if __name__ == "__main__":
    main()
