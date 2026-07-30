#!/usr/bin/env python3
"""
Abd Editor V1.0 — Entry Point
"""

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.application import create_application

if __name__ == "__main__":
    create_application()
