import os
from typing import List


def find_cfg(sibling_dirs: List[str] = None) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # 1. BladoCommon/config.ini (master config)
    master = os.path.normpath(os.path.join(here, '..', 'config.ini'))
    if os.path.isfile(master):
        return master
    # 2. Racine D:\Blado\config.ini (setup wizard le crée là)
    root = os.path.normpath(os.path.join(here, '..', '..', 'config.ini'))
    if os.path.isfile(root):
        return root
    # 3. Current working directory
    cwd_cfg = os.path.normpath(os.path.join(os.getcwd(), 'config.ini'))
    if os.path.isfile(cwd_cfg):
        return cwd_cfg
    # 4. Default (Database will use built-in defaults if missing)
    return root  # root path — sera créé par le setup wizard
