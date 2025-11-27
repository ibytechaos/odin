"""CopilotKit integration for Odin framework.

Provides seamless integration with CopilotKit's Python SDK,
allowing Odin tools to be exposed as CopilotKit actions.

References:
- https://docs.copilotkit.ai/
- https://pypi.org/project/copilotkit/
"""

from odin.protocols.copilotkit.adapter import CopilotKitAdapter

__all__ = ["CopilotKitAdapter"]
