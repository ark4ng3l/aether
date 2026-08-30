import logging
import sys
from rich.logging import RichHandler
from rich.console import Console

# Ensure Windows stdout/stderr handles UTF-8 / unicode without charmap crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class AetherLogger:
    """
    A centralized logger using Rich for beautiful terminal output
    with Windows-safe UTF-8 encoding and fallback handling.
    """
    def __init__(self, name="AETHER", level="INFO"):
        self.console = Console(file=sys.stdout, soft_wrap=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.handlers:
            rich_handler = RichHandler(
                console=self.console,
                rich_tracebacks=True,
                markup=True,
                show_path=True,
                show_time=True,
            )
            self.logger.addHandler(rich_handler)

    def info(self, message: str):
        try:
            self.logger.info(f"[bold cyan]{message}[/bold cyan]")
        except Exception:
            self.logger.info(str(message).encode("ascii", "replace").decode("ascii"))

    def success(self, message: str):
        try:
            self.logger.info(f"[bold green][OK] {message}[/bold green]")
        except Exception:
            self.logger.info(str(message).encode("ascii", "replace").decode("ascii"))

    def warning(self, message: str):
        try:
            self.logger.warning(f"[yellow]{message}[/yellow]")
        except Exception:
            self.logger.warning(str(message).encode("ascii", "replace").decode("ascii"))

    def debug(self, message: str):
        try:
            self.logger.debug(f"[dim]{message}[/dim]")
        except Exception:
            self.logger.debug(str(message).encode("ascii", "replace").decode("ascii"))

    def error(self, message: str):
        try:
            self.logger.error(f"[bold red]{message}[/bold red]")
        except Exception:
            self.logger.error(str(message).encode("ascii", "replace").decode("ascii"))

    def mission_critical(self, message: str):
        """For high-level phase transitions or major discoveries."""
        try:
            self.console.print(f"\n[bold magenta]>>> MISSION CRITICAL: {message}[/bold magenta]\n")
        except Exception:
            print(f">>> MISSION CRITICAL: {str(message).encode('ascii', 'replace').decode('ascii')}")


# Global instance
logger = AetherLogger()
