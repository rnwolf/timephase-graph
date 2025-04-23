# pyganttccpm/config.py
from enum import Enum, auto

START_NODE = "START"
END_NODE = "END"


class TaskType(Enum):
    UNASSIGNED = auto()
    CRITICAL = auto()
    FEEDING = auto()
    FREE = auto()
    BUFFER = auto()
    SYSTEM = auto()


TASK_COLORS = {
    TaskType.UNASSIGNED: "purple",
    TaskType.CRITICAL: "red",
    TaskType.FEEDING: "orange",
    TaskType.FREE: "blue",
    TaskType.BUFFER: "gray",
    TaskType.SYSTEM: "black",
}
