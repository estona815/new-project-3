#!/usr/bin/env python3
import sys, subprocess
from pathlib import Path
print('Use the project render script for full analysis:', Path(sys.argv[1]) if len(sys.argv) > 1 else '<vocal stem>')
