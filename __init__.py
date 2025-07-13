"""
MoFA-Stage: Web-based development tool for MoFA framework

MoFA-Stage provides a web interface for managing and editing Nodes and Dataflows 
in the MoFA framework. It includes features like:

- Agent management (create, edit, run, stop)
- Terminal access (web terminal, SSH connections)
- Code editing (Monaco editor, VSCode integration)
- Dataflow visualization and management

Usage:
    mofa-stage init      # Initialize project
    mofa-stage install   # Install dependencies  
    mofa-stage start     # Start services
    mofa-stage status    # Check service status
    mofa-stage stop      # Stop services
"""

__version__ = '0.1.1'
__author__ = 'MoFA Team'
__email__ = 'mofa-dev@example.com'

from . import cli

__all__ = ['cli']