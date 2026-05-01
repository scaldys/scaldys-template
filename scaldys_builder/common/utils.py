import logging
import os
import shutil
import stat
import time
import uuid
import tempfile
import sys
from pathlib import Path
from subprocess import run
from typing import Any, Callable, Iterable, Union

logger = logging.getLogger(__name__)


def get_safe_temp_dir(path: Path) -> Path:
    """
    Find a temporary directory on the same drive as the path to allow atomic rename.

    Parameters
    ----------
    path : Path
        The path to find a temporary directory for.

    Returns
    -------
    Path
        The temporary directory path.
    """
    system_temp = Path(tempfile.gettempdir())
    try:
        # Use case-insensitive comparison for drive letters (e.g., 'C:' == 'c:')
        if system_temp.drive.lower() == path.drive.lower():
            return system_temp
    except Exception:
        pass
    return path.parent


def safe_rmtree(path: Path) -> None:
    """
    Safely remove a directory tree, handling read-only files and locks on Windows.

    Parameters
    ----------
    path : Path
        The directory tree to remove.

    Raises
    ------
    OSError
        If the directory cannot be removed after retries.
    """
    if not path.exists():
        return

    was_renamed = False
    # Try to rename the directory first to move it away from any active locks/syncing.
    if path.is_dir():
        temp_base = get_safe_temp_dir(path)
        for i in range(5):
            try:
                temp_path = temp_base / f"{path.name}.{uuid.uuid4().hex}.del"
                path.rename(temp_path)
                path = temp_path
                was_renamed = True
                break
            except (PermissionError, OSError):
                if temp_base != path.parent:
                    try:
                        temp_path = path.parent / f"{path.name}.{uuid.uuid4().hex}.del"
                        path.rename(temp_path)
                        path = temp_path
                        was_renamed = True
                        break
                    except (PermissionError, OSError):
                        pass

                if i == 4:
                    logger.debug(
                        f"Failed to rename {path} for deletion, proceeding with original path."
                    )
                    break
                time.sleep(0.1 * (2**i))

    def handle_error(func: Callable[[Any, Any, Any], None], path_item: Any, exc: Any) -> None:
        """Error handler for shutil.rmtree that retries with backoff."""
        for i in range(10):  # More retries for OneDrive
            try:
                if not os.access(path_item, os.W_OK):
                    try:
                        os.chmod(path_item, stat.S_IWRITE)
                    except OSError:
                        pass
                func(path_item)
                return
            except (PermissionError, OSError):
                if i == 9:
                    raise
                time.sleep(0.1 * (2**i))

    try:
        # Using onexc for Python 3.12+, falling back to onerror for older versions
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=handle_error)
        else:
            shutil.rmtree(path, onerror=handle_error)
    except Exception as e:
        # Final fallback for Windows
        if os.name == "nt":
            try:
                run(["cmd", "/c", "rd", "/s", "/q", str(path)], check=True, capture_output=True)
                return
            except Exception:
                pass

        if was_renamed:
            logger.warning(
                f"Note: Could not fully delete renamed garbage directory {path}: {e}. "
                "The original path was cleared, so the build will proceed."
            )
        else:
            logger.error(f"Failed to remove directory {path}: {e}")
            raise


def safe_unlink(path: Path) -> None:
    """
    Safely unlink a file, handling read-only files and locks on Windows.

    Parameters
    ----------
    path : Path
        The file to unlink.
    """
    if not path.exists():
        return
    for i in range(10):
        try:
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWRITE)
            path.unlink()
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.warning(f"Failed to remove {path} after retries: {e}")
            else:
                time.sleep(0.1 * (2**i))


def safe_empty_dir(path: Path) -> None:
    """
    Safely empty a directory without deleting the directory itself.

    Parameters
    ----------
    path : Path
        The directory to empty.
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    if not path.is_dir():
        safe_unlink(path)
        path.mkdir(parents=True, exist_ok=True)
        return

    # Efficient approach: move the entire directory aside and create a new empty one.
    temp_base = get_safe_temp_dir(path)
    temp_path = temp_base / f"{path.name}.{uuid.uuid4().hex}.del"

    try:
        path.rename(temp_path)
        path.mkdir(parents=True, exist_ok=True)
        safe_rmtree(temp_path)
    except (PermissionError, OSError) as e:
        logger.debug(
            f"Could not rename root {path} for cleaning: {e}. Falling back to item-by-item."
        )
        for item in path.iterdir():
            try:
                if item.is_dir():
                    safe_rmtree(item)
                else:
                    safe_unlink(item)
            except Exception as ex:
                logger.warning(f"Could not remove {item} while emptying {path}: {ex}")


def safe_copy(src: Path, dst: Path) -> None:
    """
    Safely copy a file with retries for Windows/OneDrive.

    Parameters
    ----------
    src : Path
        The source file path.
    dst : Path
        The destination file path.
    """
    for i in range(10):
        try:
            shutil.copy2(src, dst)
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.error(f"Failed to copy {src} to {dst}: {e}")
                raise
            time.sleep(0.1 * (2**i))


def safe_copytree(src: Path, dst: Path, **kwargs: Any) -> None:
    """
    Safely copy a directory tree with retries and prior cleaning.

    Parameters
    ----------
    src : Path
        The source directory.
    dst : Path
        The destination directory.
    **kwargs : Any
        Passed to `shutil.copytree`.
    """
    for i in range(10):
        try:
            shutil.copytree(src, dst, **kwargs)
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.error(f"Failed to copy tree {src} to {dst}: {e}")
                raise
            time.sleep(0.1 * (2**i))


def safe_rename(src: Path, dst: Path) -> None:
    """
    Safely rename a file or directory with retries.

    Parameters
    ----------
    src : Path
        The source path.
    dst : Path
        The destination path.
    """
    for i in range(10):
        try:
            if dst.exists():
                if dst.is_dir():
                    safe_rmtree(dst)
                else:
                    safe_unlink(dst)
            os.rename(src, dst)
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.error(f"Failed to rename {src} to {dst}: {e}")
                raise
            time.sleep(0.1 * (2**i))
