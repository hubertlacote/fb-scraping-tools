from core import common
from collections import namedtuple

Fake_Return_Value = namedtuple(
    'FakeReturnValue', ['status_code', 'text', 'headers'])


def create_ok_return_value(text="not empty"):
    return Fake_Return_Value(
        status_code=200,
        text=text,
        headers="Some headers"
    )


def create_ok_return_value_without_text():
    return Fake_Return_Value(
        status_code=200,
        text="",
        headers="Some headers"
    )


def create_not_found_return_value():
    return Fake_Return_Value(
        status_code=404,
        text="Page not found",
        headers="Some headers"
    )


def create_service_unavailable_return_value():
    return Fake_Return_Value(
        status_code=503,
        text="Service Unavailable",
        headers="Some headers"
    )
