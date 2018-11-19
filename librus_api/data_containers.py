import datetime
from dataclasses import dataclass


@dataclass
class Teacher:
    """Dataclass for representing teachers"""
    first_name: str
    last_name: str
    id: int


@dataclass
class Notice:
    """Representation of school notice (ogłoszenie)"""
    start: datetime.datetime
    end: datetime.datetime
    time: datetime.datetime
    subject: str
    content: str
    teacher: Teacher


@dataclass
class Message:
    """Representation of a message. Will handle attachment downloads"""
    subject: str
    content: str
    teacher: Teacher
    time: datetime.datetime
    id: int
    url: str
    has_attachments: bool
    details_fetched: bool = False
