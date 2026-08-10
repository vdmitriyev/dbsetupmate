"""Process wide singletons: the logger, the Rich console and the global flags."""

from rich.console import Console

from dbsetupmate.constants import app_log_level
from dbsetupmate.logger import get_logger


class GlobalFlags:  # pylint: disable=too-few-public-methods
    """Class to hold global configuration state."""

    dry_run: bool = False
    verbose: bool = False


logger = get_logger()
console = Console()
settings = GlobalFlags()


def cprint(*args, log_level: str = "debug", **kwargs) -> None:
    """Print to the Rich console and, if verbose or DEBUG level, also log to file.

    Args:
        *args: Positional arguments forwarded to console.print().
        log_level: Logger method to use for file output ("debug", "info", "warning", "error").
        **kwargs: Keyword arguments forwarded to console.print().
    """
    console.print(*args, **kwargs)
    if app_log_level() == "DEBUG" or settings.verbose:
        message = " ".join(str(a) for a in args)
        getattr(logger, log_level, logger.debug)(message)
