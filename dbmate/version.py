"""Reads the installed package metadata."""

import importlib.metadata as importlib_metadata

from dbmate.logger import get_logger

logger = get_logger()


def package_summary(package_name: str = "dbmate"):
    """Prints information about a Python package based on its metadata.

    Args:
        package_name (str): The name of the package. Defaults to "dbmate".
    """
    info = []
    try:
        metadata = importlib_metadata.distribution(package_name)
        info.append({"field": "Version", "value": metadata.version})
        info.append({"field": "Package name", "value": metadata.metadata["Name"]})
        info.append({"field": "Summary", "value": metadata.metadata.get("Summary")})
    except importlib_metadata.PackageNotFoundError:
        logger.debug("Package '%s' not found; is it installed?", package_name)

    return info


def package_version(package_name: str = "dbmate") -> str:
    """Returns version information about a Python package based on its metadata.

    Args:
        package_name (str): The name of the package. Defaults to "dbmate".

    Returns:
        str: version. Defaults to "0.0.0"
    """

    version = "0.0.0"
    try:
        metadata = importlib_metadata.distribution(package_name)
        version = metadata.version
    except importlib_metadata.PackageNotFoundError:
        logger.debug("Package '%s' not found; is it installed?", package_name)

    return version
