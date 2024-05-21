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

"""
    Service Bot
    ~~~~~~~~~~~
    Bot for statistics

    Data format:

        "users_log-{yyyy}-{mm}-{dd}.js"

            {
                "yyyy-mm-dd HH:MM": [
                    {
                        "U" : "user_id",
                        "IP": "127.0.0.1"
                    }
                ]
            }

        "stats_log-{yyyy}-{mm}-{dd}.js"

            {
                "yyyy-mm-dd HH:MM": [
                    {
                        "S": 0,
                        "T": 1,
                        "C": 2
                    }
                ]
            }

        "speeds_log-{yyyy}-{mm}-{dd}.js"

            {
                "yyyy-mm-dd HH:MM": [
                    {
                        "U"            : "user_id",
                        "provider"     : "provider_id",
                        "station"      : "host:port",
                        "client"       : "host:port",
                        "response_time": 0.125
                    }
                ]
            }

    Fields:
        'S' - Sender type
        'C' - Counter
        'U' - User ID
        'T' - message Type

    Sender type:
        https://github.com/dimchat/mkm-py/blob/master/mkm/protocol/network.py

    Message type:
        https://github.com/dimchat/dkd-py/blob/master/dkd/protocol/types.py
"""

import threading
import time
from typing import Optional, Union, Tuple, Set, List, Dict

from dimples import DateTime
from dimples import ID, ReliableMessage
from dimples import ContentType, Content
from dimples import TextContent, CustomizedContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import BaseContentProcessor
from dimples import CustomizedContentProcessor
from dimples import CommonFacebook, CommonMessenger
from dimples.database import Storage
from dimples.client import ClientMessageProcessor
from dimples.client import ClientContentProcessorCreator

from dimples.utils import Config
from dimples.utils import Singleton, Log, Logging
from dimples.utils import Path, Runner
from dimples.utils import get_msg_sig

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from bots.shared import GlobalVariable, start_bot


async def get_name(identifier: ID, facebook: CommonFacebook) -> str:
    doc = await facebook.get_document(identifier=identifier)
    if doc is not None:
        name = doc.name
        if name is not None and len(name) > 0:
            return name
    name = identifier.name
    if name is not None and len(name) > 0:
        return name
    return str(identifier.address)


def two_digits(value: int) -> str:
    if value < 10:
        return '0%s' % value
    else:
        return '%s' % value


def parse_time(msg_time: float) -> Tuple[str, str, str, str, str]:
    local_time = time.localtime(msg_time)
    assert isinstance(local_time, time.struct_time), 'time error: %s' % local_time
    year = str(local_time.tm_year)
    month = two_digits(value=local_time.tm_mon)
    day = two_digits(value=local_time.tm_mday)
    hours = two_digits(value=local_time.tm_hour)
    minutes = two_digits(value=local_time.tm_min)
    return year, month, day, hours, minutes


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


@Singleton
class StatRecorder(Runner, Logging):

    def __init__(self):
        super().__init__(interval=Runner.INTERVAL_SLOW)
        self.__lock = threading.Lock()
        self.__contents: List[CustomizedContent] = []
        self.__config: Config = None

    @property
    def config(self) -> Optional[Config]:
        return self.__config

    @config.setter
    def config(self, conf: Config):
        self.__config = conf

    def _get_path(self, option: str, msg_time: float) -> str:
        temp = self.__config.get_string(section='statistic', option=option)
        assert temp is not None, 'failed to get users_log: %s' % self.__config
        year, month, day, _, _ = parse_time(msg_time=msg_time)
        return temp.replace('{yyyy}', year).replace('{mm}', month).replace('{dd}', day)

    def add_log(self, content: CustomizedContent):
        with self.__lock:
            self.__contents.append(content)

    def _next(self) -> Optional[CustomizedContent]:
        with self.__lock:
            if len(self.__contents) > 0:
                return self.__contents.pop(0)

    def _save_users(self, msg_time: float, users: List[Dict]):
        log_path = self._get_path(msg_time=msg_time, option='users_log')
        container: Dict = Storage.read_json(path=log_path)
        if container is None:
            container = {}
        year, month, day, hours, minutes = parse_time(msg_time=msg_time)
        log_tag = '%s-%s-%s %s:%s' % (year, month, day, hours, minutes)
        array: List[Dict] = container.get(log_tag)
        # convert List to Set
        records: Set[Tuple[str, Optional[str]]] = set()
        if array is not None:
            for item in array:
                if isinstance(item, Dict):
                    uid = item.get('U')
                    ips = item.get('IP')  # List[str]
                    if isinstance(ips, List):
                        ips = set(ips)
                    else:
                        assert isinstance(ips, str), 'IP error: %s' % ips
                        tmp = set()
                        tmp.add(ips)
                        ips = tmp
                else:
                    assert isinstance(item, str), 'old user item error: %s' % item
                    uid = item
                    ips = set()
                if len(ips) == 0:
                    records.add((uid, None))
                else:
                    for ip in ips:
                        records.add((uid, ip))
        # add new users
        for item in users:
            if isinstance(item, Dict):
                uid = item.get('U')
                ip = item.get('IP')  # str
            else:
                assert isinstance(item, str), 'new user item error: %s' % item
                uid = item
                ip = None
            records.add((uid, ip))
        # convert Set to Dict
        table: Dict[str, Set[str]] = {}
        for item in records:
            uid = item[0]
            ips = table.get(uid)
            if ips is None:
                ips = set()
                table[uid] = ips
            ip = item[1]
            if ip is not None:
                ips.add(ip)
        # convert Dict to List
        array = []
        for uid in table:
            ips = table[uid]
            assert isinstance(ips, Set), 'table error: %s => %s' % (uid, ips)
            array.append({
                'U': uid,
                'IP': list(ips)
            })
        container[log_tag] = array
        # update log file
        return Storage.write_json(container=container, path=log_path)

    def _save_stats(self, msg_time: float, stats: List[Dict]):
        log_path = self._get_path(msg_time=msg_time, option='stats_log')
        container: Dict = Storage.read_json(path=log_path)
        if container is None:
            container = {}
        year, month, day, hours, minutes = parse_time(msg_time=msg_time)
        log_tag = '%s-%s-%s %s:%s' % (year, month, day, hours, minutes)
        array = container.get(log_tag)
        if array is None:
            array = []
            container[log_tag] = array
        # append records
        for item in stats:
            array.append(item)
        # update log file
        return Storage.write_json(container=container, path=log_path)

    def _save_speeds(self, msg_time: float, sender: str, provider: str, stations: List[Dict], client: Optional[str]):
        log_path = self._get_path(msg_time=msg_time, option='speeds_log')
        container: Dict = Storage.read_json(path=log_path)
        if container is None:
            container = {}
        year, month, day, hours, minutes = parse_time(msg_time=msg_time)
        log_tag = '%s-%s-%s %s:%s' % (year, month, day, hours, minutes)
        array = container.get(log_tag)
        if array is None:
            array = []
            container[log_tag] = array
        # append speeds
        for srv in stations:
            host = srv.get('host')
            port = srv.get('port')
            response_time = srv.get('response_time')
            socket_address = srv.get('socket_address')
            if socket_address is not None:
                client = socket_address
            self.info(msg='station speed: %s' % srv)
            item = {
                'U': sender,
                'provider': provider,
                'station': '%s:%d' % (host, port),
                'client': client,
                'response_time': response_time,
            }
            array.append(item)
        # update log file
        return Storage.write_json(container=container, path=log_path)

    def get_users(self, now: float) -> List[Dict]:
        log_path = self._get_path(msg_time=now, option='users_log')
        container = Storage.read_json(path=log_path)
        if container is None:
            return []
        users: List[Dict] = []
        for tag in container:
            array: List[Dict] = container.get(tag)
            if array is None or len(array) == 0:
                continue
            for item in array:
                if isinstance(item, Dict):
                    user_id = item.get('U')
                    ip_list = item.get('IP')  # List[str]
                else:
                    assert isinstance(item, str), 'user item error: %s' % item
                    user_id = item
                    ip_list = None
                if user_id is None:  # or not isinstance(user_id, str):
                    self.error('user item error: %s' % item)
                    continue
                # seek user result
                result: Dict = None
                for res in users:
                    if res.get('U') == user_id:
                        # got it
                        result = res
                        break
                if result is None:
                    result = {
                        'U': user_id,
                        'IP': set(),
                    }
                    users.append(result)
                # client ip
                if isinstance(ip_list, List):
                    ips: Set = result['IP']
                    for ip in ip_list:
                        ips.add(ip)
                elif isinstance(ip_list, str):
                    ips: Set = result['IP']
                    ips.add(ip_list)
        return users

    def get_speeds(self, now: float) -> List[Dict]:
        log_path = self._get_path(msg_time=now, option='speeds_log')
        container = Storage.read_json(path=log_path)
        if container is None:
            return []
        speeds: List[Dict] = []
        for tag in container:
            array: List[Dict] = container.get(tag)
            if array is None or len(array) == 0:
                continue
            for item in array:
                sender = item.get('U')
                provider = item.get('provider')
                station = item.get('station')
                client = item.get('client')
                response_time = item.get('response_time')
                if response_time is None or response_time <= 0:
                    self.error(msg='speed item error: %s' % item)
                    continue
                if isinstance(client, str):
                    client = client.split(':')[0]
                elif isinstance(client, List):
                    client = client[0]
                # seek speed result
                result: Dict = None
                for res in speeds:
                    if res.get('station') != station or res.get('client_ip') != client:
                        continue
                    pid = res.get('provider')
                    if pid is not None and pid != provider:
                        continue
                    uid = res.get('U')
                    if uid is not None and uid != sender:
                        continue
                    # got it
                    result = res
                    break
                if result is None:
                    result = {
                        'station': station,
                        'client_ip': client,
                        'rt': []
                    }
                    speeds.append(result)
                if sender is not None:
                    result['U'] = sender
                if provider is not None:
                    result['provider'] = provider
                # response times
                rt = result['rt']
                rt.append(response_time)
        return speeds

    # Override
    async def process(self) -> bool:
        content = self._next()
        if content is None:
            # nothing to do now, return False to have a rest
            return False
        now = DateTime.current_timestamp()
        msg_time = content.time
        msg_time = 0 if msg_time is None else msg_time.timestamp
        if msg_time is None or msg_time < now - 3600*24*7:
            self.warning(msg='message expired: %s' % content)
            return True
        try:
            mod = content.module
            if mod == 'users':
                users = content.get('users')
                self._save_users(msg_time=msg_time, users=users)
            elif mod == 'stats':
                stats = content.get('stats')
                self._save_stats(msg_time=msg_time, stats=stats)
            elif mod == 'speeds':
                sender = content.get('U')
                provider = content.get('provider')
                stations = content.get('stations')
                client = content.get('remote_address')
                if isinstance(client, List):  # or isinstance(client, Tuple):
                    assert len(client) == 2, 'socket address error: %s' % client
                    client = '%s:%d' % (client[0], client[1])
                self._save_speeds(msg_time=msg_time, sender=sender, provider=provider, stations=stations, client=client)
            else:
                self.warning(msg='ignore mod: %s, %s' % (mod, content))
        except Exception as e:
            self.error(msg='failed to process content: %s, %s' % (e, content))
        return True


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

    async def __get_name(self, sender: str) -> Optional[str]:
        identifier = ID.parse(identifier=sender)
        if identifier is None:
            return None
        doc = await self.facebook.get_document(identifier=identifier)
        if doc is None:
            name = None
        else:
            name = doc.name
        if name is None or len(name) == 0:
            return identifier.name
        else:
            return name

    async def __get_locale(self, sender: str) -> Optional[str]:
        identifier = ID.parse(identifier=sender)
        if identifier is not None:
            doc = await self.facebook.get_document(identifier=identifier)
            if doc is not None:
                app = doc.get_property(key='app')
                language = app.get('language') if isinstance(app, Dict) else None
                sys = doc.get_property(key='sys')
                locale = sys.get('locale') if isinstance(sys, Dict) else None
                if language is None:
                    return locale
                elif locale is None:
                    return language
                else:
                    return '%s(%s)' % (language, locale)

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
        text = '| ID | Name - Locale | IP |\n'
        text += '|---|---------------|----|\n'
        users = g_recorder.get_users(now=now)
        self.info(msg='users: %s' % str(users))
        for item in users:
            sender = item.get('U')
            name = await self.__get_name(sender=sender)
            locale = await self.__get_locale(sender=sender)
            ip = item.get('IP')
            if isinstance(ip, Set):
                ip = list(ip)
            if name is not None:
                name = '"%s"' % name
            text += '| %s | **%s** - %s | %s |\n' % (sender, name, locale, ip)
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
        text = '| Name | IP | Station | Times |\n'
        text += '|-----|----|---------|-------|\n'
        speeds = g_recorder.get_speeds(now=now)
        self.info(msg='speeds: %s' % str(speeds))
        for item in speeds:
            sender = item.get('U')
            ip = item.get('client_ip')
            mta = item.get('station')
            if isinstance(mta, str):
                pos = mta.find(':')
                if pos > 0:
                    mta = mta[:pos]
            rt = item.get('rt')
            rt, c = math_stat(array=rt)
            if c > 3:
                rt += ', count: %d' % c
            name = await self.__get_name(sender=sender)
            text += '| **%s** | %s | %s | %s |\n' % (name, ip, mta, rt)
        text += '\n'
        text += 'Total: %d, Date: %s' % (len(speeds), day)
        return text

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        text = content.text
        sender = r_msg.sender
        nickname = await get_name(identifier=sender, facebook=self.facebook)
        self.info(msg='received text message from "%s": "%s"' % (nickname, text))
        # parse text for your business
        response = None
        text = content.text
        if text.startswith('users'):
            # query users
            array = text.split(' ')
            if len(array) == 1:
                day = ''
            else:
                day = array[1]
            text = await self.__get_users(day=day)
            response = TextContent.create(text=text)
        elif text.startswith('speeds'):
            # query speeds
            array = text.split(' ')
            if len(array) == 1:
                day = ''
            else:
                day = array[1]
            text = await self.__get_speeds(day=day)
            response = TextContent.create(text=text)
        if response is None:
            return []
        # calibrate the clock
        req_time = content.time
        res_time = response.time
        print('checking respond time: %s, %s' % (res_time, req_time))
        if res_time is None or res_time <= req_time:
            response['time'] = req_time + 1
        # respond in markdown format
        response['format'] = 'markdown'
        return [response]


class StatContentProcessor(CustomizedContentProcessor, Logging):
    """ Process customized stat content """

    # Override
    async def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, CustomizedContent), 'stat content error: %s' % content
        app = content.application
        mod = content.module
        act = content.action
        sender = r_msg.sender
        self.debug(msg='received content from %s: %s, %s, %s' % (sender, app, mod, act))
        return await super().process_content(content=content, r_msg=r_msg)

    # Override
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        if app == 'chat.dim.monitor':
            # app ID matched
            return None
        # unknown app ID
        return super()._filter(app=app, content=content, msg=msg)

    # Override
    async def handle_action(self, act: str, sender: ID,
                            content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        recorder = StatRecorder()
        mod = content.module
        self.__increase_counter(msg=msg)
        if mod == 'users':
            users = content.get('users')
            self.info(msg='received station log [%s] users: %s' % (content.time, users))
            recorder.add_log(content=content)
        elif mod == 'stats':
            stats = content.get('stats')
            self.info(msg='received station log [%s] stats: %s' % (content.time, stats))
            recorder.add_log(content=content)
        elif mod == 'speeds':
            user = content.get('U')
            provider = content.get('provider')
            stations = content.get('stations')
            remote = content.get('remote_address')
            self.info(msg='received client log [%s] speeds count: %d, %s, %s => %s'
                          % (content.time, len(stations), remote, user, provider))
            recorder.add_log(content=content)
        else:
            self.error(msg='unknown module: %s, action: %s, [%s] %s' % (mod, act, content.time, content))
        # respond nothing
        return []

    def __increase_counter(self, msg: ReliableMessage):
        now = DateTime.now()
        if self.__start_time is None:
            self.__start_time = now
        self.__count += 1
        # check duplicated
        sig = get_msg_sig(msg=msg)
        cnt = self.__signatures.get(sig)
        if cnt is None:
            cnt = 1
        else:
            cnt += 1
            self.__duplicates += 1
        self.__signatures[sig] = cnt
        print('>>> stat msg count: %d, elapsed: %f; (%s) duplicated: %d'
              % (self.__count, now - self.__start_time, sig, self.__duplicates))

    __start_time = None
    __count = 0
    __signatures = {}
    __duplicates = 0


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return TextContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # application customized
        if msg_type == ContentType.CUSTOMIZED:
            return StatContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)


class BotMessageProcessor(ClientMessageProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


g_recorder = StatRecorder()


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim_bots/config.ini'


async def main():
    # client & start bot
    client = await start_bot(default_config=DEFAULT_CONFIG,
                             app_name='ServiceBot: Statistics',
                             ans_name='statistic',
                             processor_class=BotMessageProcessor)
    # start recorder
    shared = GlobalVariable()
    g_recorder.config = shared.config
    Runner.thread_run(runner=g_recorder)
    # main run loop
    await client.start()
    await client.run()
    # await client.stop()
    Log.warning(msg='bot stopped: %s' % client)


if __name__ == '__main__':
    Runner.sync_run(main=main())
