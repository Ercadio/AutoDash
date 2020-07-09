from src.database.FirebaseAccessor import FirebaseAccessor
from src.database.Source import Source


class FirebaseSource(Source):

    def __init__(self, *parents):
        super().__init__(*parents)
        self.set_database(FirebaseAccessor())
