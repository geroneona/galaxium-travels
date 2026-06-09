"""Settings and configuration classes for ICA integration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ICASettings:
    """Configuration settings for ICA Agentic Apps integration.
    
    Contains all necessary credentials and identifiers for registering and
    interacting with the ICA platform.
    """
    
    agent_url: str
    """Base URL of the agent (e.g., from ngrok tunnel or deployment)."""
    
    app_id: str
    """ID of the agentic app in the ICA platform."""
    
    app_name: str
    """Name of the agentic app."""
    
    ica_token: str
    """JWT or API token for authentication with ICA APIs."""
    
    team_id: str
    """Team ID for ICA requests."""
    
    user_id: str
    """User ID for ICA requests."""
    
    agent_type: str = "a2a"
    """Type of agent (default: "a2a")."""
    
    provider: str = "a2a"
    """Provider type (default: "a2a")."""
    
    poll_max_retries: int = 30
    """Maximum polling attempts for agent card endpoint."""
    
    poll_retry_delay: float = 1.0
    """Initial delay between poll retries in seconds."""
    
    register_agent: bool = False
    """Whether to automatically register the agent on startup (default: True)."""
    
    @classmethod
    def from_env(cls, agent_url: str) -> ICASettings:
        """Create ICASettings from environment variables.
        
        Reads the following environment variables:
        - ICA_APP_ID: App ID
        - ICA_APP_NAME: App name
        - ICA_TOKEN: Authentication token
        - ICA_TEAM_ID: Team ID
        - ICA_USER_ID: User ID
        - ICA_AGENT_TYPE: Agent type (optional, default: "a2a")
        - ICA_PROVIDER: Provider type (optional, default: "a2a")
        - ICA_POLL_MAX_RETRIES: Max polling retries (optional, default: 30)
        - ICA_POLL_RETRY_DELAY: Poll retry delay (optional, default: 1.0)
        
        Returns:
            ICASettings instance populated from environment variables
            
        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = {
            "ICA_APP_ID": "app_id",
            "ICA_TOKEN": "ica_token",
            "ICA_TEAM_ID": "team_id",
        }
        
        missing = [key for key in required_vars if not os.getenv(key)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        
        kwargs = {
            value: os.getenv(key)
            for key, value in required_vars.items()
        }

        kwargs["agent_url"] = agent_url
        
        # Optional variables with defaults
        kwargs["app_name"] = os.getenv("ICA_APP_NAME")
        kwargs["user_id"] = os.getenv("ICA_USER_ID")
        kwargs["agent_type"] = os.getenv("ICA_AGENT_TYPE", "a2a")
        kwargs["provider"] = os.getenv("ICA_PROVIDER", "a2a")
        
        try:
            kwargs["poll_max_retries"] = int(os.getenv("ICA_POLL_MAX_RETRIES", "30"))
        except ValueError:
            kwargs["poll_max_retries"] = 30
        
        try:
            kwargs["poll_retry_delay"] = float(os.getenv("ICA_POLL_RETRY_DELAY", "1.0"))
        except ValueError:
            kwargs["poll_retry_delay"] = 1.0
        
        # Parse register_agent as boolean
        register_agent_str = os.getenv("ICA_REGISTER_AGENT", "false").lower()
        kwargs["register_agent"] = register_agent_str in ("true", "1", "yes", "on")
        
        return cls(**kwargs)
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary.
        
        Returns:
            Dictionary representation of all settings
        """
        return {
            "agent_url": self.agent_url,
            "app_id": self.app_id,
            "app_name": self.app_name,
            "ica_token": self.ica_token,
            "team_id": self.team_id,
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "provider": self.provider,
            "poll_max_retries": self.poll_max_retries,
            "poll_retry_delay": self.poll_retry_delay,
            "register_agent": self.register_agent,
        }
