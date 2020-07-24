from abc import abstractmethod
from typing import Dict, Any

from .iExecutor import iExecutor

class UndefinedDatabaseException(Exception):
    '''Raise when attempt to access database before injected into the crawler'''

# Interface for any Executor that requires access to a database (either to make changes or get information)
class iDatabaseExecutor(iExecutor):
    def __init__(self, *parents, stateful=False):
        super().__init__(*parents, stateful=stateful)
        self.database = None

    def set_database(self, database):
        self.database = database
        return self

    @abstractmethod
    def run(self, obj: Dict[str, Any]):
        pass

    def requires_database(self):
        return self.database is None