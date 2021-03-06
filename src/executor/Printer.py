from .iExecutor import iExecutor


class Printer(iExecutor):
    def __init__(self, *parents, msg=""):
        self.msg = msg
        super().__init__(*parents)

    def run(self, item):
        if item is not None:
            print(f"printer loaded, item {item}, message: {self.msg}")
        else:
            print(f"printer loaded, message: {self.msg}")
        return item
