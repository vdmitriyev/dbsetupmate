import os
import subprocess  # nosec B404

from app.configs import logger


def get_version():
    version = None
    version = get_latest_git_tag()
    if version is None:
        version = get_latest_version_from_file()
    if version is None:
        return "Unknown"
    return version


def get_latest_git_tag():
    """
    Gets the latest Git tag of the current repository.

    Returns:
        str: The latest Git tag, or None if no tags are found or if
             it's not a Git repository.
    """
    try:
        # Run the git command to get tags, sorted by version (latest first)
        # and limit to the first result
        command = ["git", "tag", "--sort=-v:refname", "--list", "v*", "--merged", "HEAD"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)  # nosec B603

        # Split the output into lines and get the first line (latest tag)
        tags = result.stdout.strip().split("\n")
        if tags and tags[0]:
            return tags[0]
        else:
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing Git command: {e}")
        logger.error(f"Stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        logger.error("Git command not found. Please ensure Git is installed and in your PATH.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None


def get_latest_version_from_file(fname: str = "version.txt") -> str:
    """
    Retrieves the first line from a specified file.

    Args:
        fname (str): The name of the file to read from. Defaults to 'version.txt'.

    Returns:
        str: The first line of the file, or an empty string if the file
             does not exist or is empty.
    """
    if not os.path.exists(fname):
        logger.error(f"Error: The file '{fname}' was not found.")
        return None

    with open(fname, "r") as file:
        first_line = file.readline().strip()
        return first_line
