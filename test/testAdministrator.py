#!/usr/bin/env python3
import unittest
from src.pipeline import run as administrator
from src.executor.iExecutor import iExecutor
from multiprocessing import Queue
from queue import Empty as EmptyException

events = Queue()


def run(executors):
    pass


class TestExecutor(iExecutor):
    def __init__(self, next, event_num):
        super().__init__(next)
        self.event_num = event_num

    def run(self, obj):
        print(f"run {self.event_num}")
        events.put(self.event_num)


class TestAdministrator(unittest.TestCase):
    def test_main_single_process(self):
        num_items = 10
        ptr = TestExecutor(None, 0)
        executors = [ptr]

        for x in range(1, num_items):
            temp = TestExecutor(None, x)
            ptr.next = temp
            ptr = temp

        administrator(executors, n_workers=1, max_iterations=1)

        for i in range(num_items):
            self.assertEqual(events.get(timeout=2), i, "items in wrong order")

        self.assertRaises(EmptyException, events.get, True, 0.25)

    def test_main_multi_process(self):
        num_items = 10
        ptr = TestExecutor(None, 0)
        executors = [ptr]

        for x in range(1, num_items):
            temp = TestExecutor(None, x)
            ptr.next = temp
            ptr = temp

        administrator(executors, n_workers=2, max_iterations=3)
        for i in range(num_items*3):
            events.get(timeout=2)

        self.assertRaises(EmptyException, events.get, True, 0.25)


if __name__ == '__main__':
    unittest.main()