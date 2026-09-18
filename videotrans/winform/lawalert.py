

def openwin():
    from pathlib import Path
    from videotrans.winform import get_cls
    from videotrans.configure.config import params,app_cfg


    winobj = get_cls(Path(__file__).stem)()
    return winobj
