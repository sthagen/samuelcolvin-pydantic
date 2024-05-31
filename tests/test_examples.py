import datetime as dt
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Optional, Union

import pytest
import pytz
from pydantic_core import CoreSchema, core_schema
from typing_extensions import Annotated

from pydantic import GetCoreSchemaHandler, TypeAdapter


def test_tzinfo_validator_example_pattern() -> None:
    """test that tzinfo custom validator pattern works as explained"""

    def my_validator_function(
        tz_constraint: Union[str, None],
        value: dt.datetime,
        handler: Callable,
    ):
        """validate tz_constraint and tz_info"""

        # handle naive datetimes
        if tz_constraint is None:
            assert value.tzinfo is None
            return handler(value)

        # validate tz_constraint and tz-aware tzinfo
        assert tz_constraint in pytz.all_timezones
        result = handler(value)
        assert tz_constraint == str(result.tzinfo)

        return result

    @dataclass(frozen=True)
    class MyDatetimeValidator:
        tz_constraint: Optional[str] = None

        def __get_pydantic_core_schema__(
            self,
            source_type: Any,
            handler: GetCoreSchemaHandler,
        ) -> CoreSchema:
            return core_schema.no_info_wrap_validator_function(
                partial(my_validator_function, self.tz_constraint), handler(source_type)
            )

    LA = 'America/Los_Angeles'

    # passing naive test
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator()])
    ta.validate_python(dt.datetime.now())

    # failing naive test
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator()])
    with pytest.raises(Exception):
        ta.validate_python(dt.datetime.now(pytz.timezone(LA)))

    # passing tz-aware test
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator(LA)])
    ta.validate_python(dt.datetime.now(pytz.timezone(LA)))

    # failing bad tz
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator('foo')])
    with pytest.raises(Exception):
        ta.validate_python(dt.datetime.now())

    # failing tz-aware test
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator(LA)])
    with pytest.raises(Exception):
        ta.validate_python(dt.datetime.now())


def test_utcoffset_validator_example_pattern() -> None:
    """test that utcoffset custom validator pattern works as explained"""

    def my_validator_function(
        lower_bound: int,
        upper_bound: int,
        value: dt.datetime,
        handler: Callable,
    ):
        """validate and test bounds"""
        # validate utcoffset exists
        assert value.utcoffset() is not None

        # validate bound range
        assert lower_bound <= upper_bound

        result = handler(value)

        # validate value is in range
        hours_offset = value.utcoffset().total_seconds() / 3600

        assert hours_offset >= lower_bound
        assert hours_offset <= upper_bound

        return result

    @dataclass(frozen=True)
    class MyDatetimeValidator:
        lower_bound: int
        upper_bound: int

        def __get_pydantic_core_schema__(
            self,
            source_type: Any,
            handler: GetCoreSchemaHandler,
        ) -> CoreSchema:
            return core_schema.no_info_wrap_validator_function(
                partial(
                    my_validator_function,
                    self.lower_bound,
                    self.upper_bound,
                ),
                handler(source_type),
            )

    LA = 'America/Los_Angeles'

    # test valid bound passing
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator(-10, 10)])
    ta.validate_python(dt.datetime.now(pytz.timezone(LA)))

    # test valid bound failing - missing TZ
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator(-12, 12)])
    with pytest.raises(Exception):
        ta.validate_python(dt.datetime.now())

    # test invalid bound
    ta = TypeAdapter(Annotated[dt.datetime, MyDatetimeValidator(0, 4)])
    with pytest.raises(Exception):
        ta.validate_python(dt.datetime.now(pytz.timezone(LA)))
