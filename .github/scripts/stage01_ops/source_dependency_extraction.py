#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stage01_operation_runtime import main_for
if __name__=="__main__":
    main_for("SOURCE_DEPENDENCY_EXTRACTION")
