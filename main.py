#!/usr/bin/env python3
"""Main entry point for the Enonomics economic worldbuilding generator."""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from econgen.cli import app

def main():
    """Main entry point for CLI."""
    app()

if __name__ == "__main__":
    main()
