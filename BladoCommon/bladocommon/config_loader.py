import os, sys
from typing import List


def find_cfg(sibling_dirs: List[str] = None) -> str:
    # 0. À côté de l'exécutable (priorité absolue)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    exe_cfg = os.path.join(exe_dir, 'config.ini')
    if os.path.isfile(exe_cfg):
        return exe_cfg

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
    # 4. Créer config.ini par défaut à côté de l'exécutable
    exe_cfg = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'config.ini')
    try:
        with open(exe_cfg, 'w', encoding='utf-8') as f:
            f.write('[App]\nVersion=1.0\nMode=RH\n\n[IntranetDatabase]\nHost=127.0.0.1\nPort=55515\nDB=bladodb\nUser=postgres\nPass=postgres\n')
        return exe_cfg
    except Exception:
        return exe_cfg
