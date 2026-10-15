"""
Shared dependencies, singletons, and service injectors for HAMSA Web API.
"""

from hamsa.core.orchestrator import Orchestrator
from hamsa.core.database import GLOBAL_DB
from hamsa.core.cache import GLOBAL_CACHE

# Global Orchestrator instance for intelligence operations
GLOBAL_ORCHESTRATOR = Orchestrator()
