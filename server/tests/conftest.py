import os

os.environ["BAJA_ENV"] = "testing"

from baja import tasks  # noqa: F401  Registers every job with the broker.
from tests.fixtures import *
