# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2025 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================


"""
    Date Time
    ~~~~~~~~~

"""

import time
from typing import Tuple

from dimples import DateTime


def two_digits(value: int) -> str:
    if value < 10:
        return '0%s' % value
    else:
        return '%s' % value


def yesterday() -> str:
    day = DateTime.current_timestamp() - 3600 * 24
    day = DateTime(timestamp=day)
    day = str(day)
    array = day.split()
    return array[0]


def parse_time(msg_time: float) -> Tuple[str, str, str, str, str]:
    local_time = time.localtime(msg_time)
    assert isinstance(local_time, time.struct_time), 'time error: %s' % local_time
    year = str(local_time.tm_year)
    month = two_digits(value=local_time.tm_mon)
    day = two_digits(value=local_time.tm_mday)
    hours = two_digits(value=local_time.tm_hour)
    minutes = two_digits(value=local_time.tm_min)
    return year, month, day, hours, minutes
