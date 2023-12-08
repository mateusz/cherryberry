class AddHistory:
    def __init__(self, event, skip_if_duplicate=False):
        self.event = event
        self.skip_if_duplicate = skip_if_duplicate
