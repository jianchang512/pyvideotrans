from videotrans.util import tools


class BaseCon:

    def __init__(self, **kwargs):
        self.uuid = None

    def _signal(self, **kwargs):
        kwargs['uuid'] = self.uuid
        tools.set_process(**kwargs)
