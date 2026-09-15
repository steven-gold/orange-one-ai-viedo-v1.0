#!/usr/bin/env python3
# Compatibility shim only; reusable policy semantics live in the neutral validator.
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('validate_validation_remediation_closure_protocol.py')),run_name='__main__')
