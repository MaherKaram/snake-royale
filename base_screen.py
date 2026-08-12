class BaseScreen:
    def __init__(self,manager):
        self.manager=manager

    def handle_events(self,events):
        pass

    def update(self):
        pass

    def draw(self,surface):
        pass