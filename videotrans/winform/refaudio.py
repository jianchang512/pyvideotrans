def openwin():
    from videotrans.winform import get_cls
    from pathlib import Path


    winobj = get_cls(Path(__file__).stem)()
    return winobj
