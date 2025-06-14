from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """
    Abstract base class for all scanner plugins.
    Each plugin must implement the run method.
    """

    @abstractmethod
    def run(self, repo_path: str) -> list[dict]:
        """
        Run the plugin's check on the given repository.

        Args:
            repo_path: The absolute path to the cloned repository inside the container.

        Returns:
            A list of dictionaries, where each dictionary represents a found issue.
            An empty list should be returned if no issues are found.
        """
        pass
