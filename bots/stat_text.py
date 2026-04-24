#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

import time
from typing import Optional, Tuple, List

from dimples import ID, Visa
from dimples import ReliableMessage
from dimples import Content
from dimples import TextContent
from dimples import BaseContentProcessor
from dimples import CommonFacebook, CommonMessenger

from dimples.utils import Log, Logging

from libs.utils import template_replace
from libs.utils import md_user_url
from libs.utils import get_locale
from libs.utils import yesterday
from libs.client import RequestFilter
from libs.client import Emitter

from bots.shared import GlobalVariable
from bots.stat_recoder import g_recorder


async def get_supervisors() -> List[ID]:
    shared = GlobalVariable()
    return await shared.config.get_supervisors(facebook=shared.facebook)


def math_stat(array: List[float]) -> Tuple[str, int]:
    count = len(array)
    if count == 0:
        return '[]', 0
    elif count == 1:
        return '%.3f' % array[0], 1
    elif count == 2:
        right = array.pop()
        left = array.pop(0)
        return '%.3f, %.3f' % (left, right), count
    Log.info(msg='array (%d): %s' % (count, array))
    array = sorted(array)
    right = array.pop()
    left = array.pop(0)
    mean = sum(array) / len(array)
    return '%.3f ... **%.3f** ... %.3f' % (left, mean, right), count


def parse_ip(ip):
    if ip is None:
        return None
    elif isinstance(ip, str):
        return '[%s](https://ip138.com/iplookup.php?ip=%s "")' % (ip, ip)
    array = []
    for item in ip:
        text = '[%s](https://ip138.com/iplookup.php?ip=%s "")' % (item, item)
        array.append(text)
    return array


#
#   CPU - Content Processing Unit
#


class TextContentProcessor(BaseContentProcessor, Logging):
    """ Process text message content """

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'barrack error: %s' % barrack
        return barrack

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'transceiver error: %s' % transceiver
        return transceiver

    @property
    def request_filter(self) -> RequestFilter:
        return RequestFilter(facebook=self.facebook)

    async def __get_visa(self, sender: str) -> Optional[Visa]:
        identifier = ID.parse(identifier=sender)
        if identifier is not None:
            return await self.facebook.get_visa(user=identifier)

    async def __get_users(self, day: str) -> str:
        day = day.strip()
        if len(day) == 0:
            now = time.time()
            day = time.strftime('%Y-%m-%d', time.localtime(now))
        else:
            try:
                now = time.mktime(time.strptime(day, '%Y-%m-%d'))
            except ValueError as e:
                text = 'error date: %s, %s' % (day, e)
                self.error(msg=text)
                return text
        text = '| User | IP |\n'
        text += '|------|----|\n'
        users = await g_recorder.get_users(now=now)
        self.info(msg='users: %s' % str(users))
        for item in users:
            # get user info
            sender = item.get('U')
            visa = await self.__get_visa(sender=sender)
            if visa is None:
                title = '**%s**' % sender
            else:
                title = md_user_url(visa=visa)
                # get language
                locale = get_locale(visa=visa)
                if locale is not None:
                    title = '%s - %s' % (title, locale)
            # get IP info
            ip = item.get('IP')
            ip = parse_ip(ip=ip)
            text += '| %s | %s |\n' % (title, ip)
        text += '\n'
        text += 'Total: %d, Date: %s' % (len(users), day)
        return text

    async def __get_speeds(self, day: str) -> str:
        day = day.strip()
        if len(day) == 0:
            now = time.time()
            day = time.strftime('%Y-%m-%d', time.localtime(now))
        else:
            try:
                now = time.mktime(time.strptime(day, '%Y-%m-%d'))
            except ValueError as e:
                text = 'error date: %s, %s' % (day, e)
                self.error(msg=text)
                return text
        text = '| User | IP | Station | Times |\n'
        text += '|-----|----|---------|-------|\n'
        speeds = await g_recorder.get_speeds(now=now)
        self.info(msg='speeds: %s' % str(speeds))
        for item in speeds:
            sender = item.get('U')
            ip = item.get('client_ip')
            ip = parse_ip(ip=ip)
            mta = item.get('station')
            if isinstance(mta, str):
                pos = mta.find(':')
                if pos > 0:
                    mta = mta[:pos]
            rt = item.get('rt')
            rt, c = math_stat(array=rt)
            if c > 3:
                rt += ', count: %d' % c
            # get user info
            visa = await self.__get_visa(sender=sender)
            if visa is None:
                title = '**%s**' % sender
            else:
                title = md_user_url(visa=visa)
            text += '| **%s** | %s | %s | %s |\n' % (title, ip, mta, rt)
        text += '\n'
        text += 'Total: %d, Date: %s' % (len(speeds), day)
        return text

    ADMIN_COMMANDS = [
        'users',
        'speeds',
    ]

    HELP_PROMPT = '## Admin Commands\n' \
                  '* users\n' \
                  '* users {yyyy-mm-dd}\n' \
                  '* speeds\n' \
                  '* speeds {yyyy-mm-dd}\n'

    async def _help_info(self, supervisors: List[ID]) -> str:
        request_filter = self.request_filter
        text = '## Supervisors\n'
        for did in supervisors:
            name = await request_filter.get_nickname(identifier=did)
            if name is None or len(name) == 0:
                text += '* %s\n' % did
                continue
            text += '* "%s" - %s\n' % (name, did)
        prompt = template_replace(template=self.HELP_PROMPT, key='yyyy-mm-dd', value=yesterday())
        return '%s\n%s' % (prompt, text)

    async def _process_admin_command(self, cmd: str, sender: ID, supervisors: List[ID]) -> str:
        # check permissions before executing command
        if sender not in supervisors:
            self.warning(msg='permission denied: "%s", sender: %s' % (cmd, sender))
            text = 'Forbidden\n'
            text += '\n----\n'
            text += 'Permission Denied'
            return text
        #
        #  query users
        #
        if cmd.startswith('users'):
            array = cmd.split(' ')
            if len(array) == 1:
                day = ''
            else:
                day = array[1]
            return await self.__get_users(day=day)
        #
        #  query speeds
        #
        if cmd.startswith('speeds'):
            # query speeds
            array = cmd.split(' ')
            if len(array) == 1:
                day = ''
            else:
                day = array[1]
            return await self.__get_speeds(day=day)
        #
        #  error
        #
        text = 'Error\n'
        text += '\n----\n'
        text += 'Unknown command: "%s"' % cmd
        return text

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        text = content.text
        group = content.group
        sender = r_msg.sender
        request_filter = self.request_filter
        nickname = await request_filter.get_nickname(identifier=sender)
        if nickname is None or len(nickname) == 0:
            nickname = str(sender)
        self.info(msg='received text message from "%s" %s: "%s"' % (nickname, group, text))
        #
        #   filter text
        #
        naked = await request_filter.filter_text(text=text, content=content, envelope=r_msg.envelope)
        if naked is None:
            self.info(msg='ignore text from "%s" %s: "%s"' % (nickname, group, text))
            return []
        else:
            text = naked.strip()
            supervisors = await get_supervisors()
        #
        #   system commands
        #
        if text == 'help':
            res = await self._help_info(supervisors=supervisors)
        elif text in self.ADMIN_COMMANDS:
            res = await self._process_admin_command(cmd=text, sender=sender, supervisors=supervisors)
        elif text.startswith('users ') or text.startswith('speeds '):
            res = await self._process_admin_command(cmd=text, sender=sender, supervisors=supervisors)
        else:
            res = 'Unexpected command: "%s"' % text
            # TODO: parse text for your business
        #
        #   build response
        #
        response = TextContent.create(text=res)
        # respond in markdown format
        response['format'] = 'markdown'
        # calibrate the clock
        calibrate_time(content=response, request=content)
        if group is None:
            return [response]
        # else:
        #     response.group = group
        emitter = Emitter()
        await emitter.send_content(content=response, receiver=group)
        # return [response]
        return []


def calibrate_time(content: Content, request: Content, period: float = 1.0):
    res_time = content.time
    req_time = request.time
    if req_time is None:
        assert False, 'request error: %s' % req_time
    elif res_time is None or res_time <= req_time:
        content['time'] = req_time + period
