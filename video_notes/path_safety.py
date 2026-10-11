"""Reject link/reparse components; checks reduce, not eliminate, OS races."""
from pathlib import Path
import stat

def plain_path(raw, root):
    path = Path(raw).absolute()
    root = Path(root).absolute()
    if not path.is_relative_to(root):
        raise ValueError('Path escapes intended root')
    for component in [path, *path.parents]:
        if component.exists() or component.is_symlink():
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError(f'Link or reparse component prohibited: {component}. Use a plain local root; linked/sync reparse directories are unsupported')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Resolved path escapes intended root')
    return path
