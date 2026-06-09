from .logger import get_logger


class LangGraphOrchestrator:
    """Minimal stub for LangGraph orchestration.

    Replace this with real LangGraph wiring (nodes, edges, async flows).
    """

    def __init__(self) -> None:
        self._log: list[str] = []
        self._logger = get_logger(__name__)

    async def route(self, from_agent: str, to_agent: str, message: str) -> str:
        # In a real LangGraph integration this would build a graph flow
        # and execute it. For now just log and pass-through.
        entry = f"route {from_agent}->{to_agent}: {message}"
        self._log.append(entry)
        self._logger.debug("Routed message: %s", entry)
        return message

    def get_log(self) -> list[str]:
        return list(self._log)
