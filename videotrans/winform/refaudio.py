def openwin():
    from videotrans.winform import get_cls
    from videotrans.configure.config import params,app_cfg
    from pathlib import Path


    winobj = get_cls(Path(__file__).stem)()
    return winobj
