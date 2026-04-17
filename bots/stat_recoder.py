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
        https://github.com/dimchat/mkm-py/blob/master/mkm/protocol/entity.py

    Message type:
        https://github.com/dimchat/dkd-py/blob/master/dkd/protocol/types.py
"""

import threading
from typing import Optional, Tuple, Set, List, Dict

from dimples import DateTime
from dimples import CustomizedContent

from dimples.database import Storage

from dimples.utils import Config
from dimples.utils import Singleton, Logging
from dimples.utils import Runner

from libs.utils import parse_time


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

    async def _save_users(self, msg_time: float, users: List[Dict]):
        log_path = self._get_path(msg_time=msg_time, option='users_log')
        container: Dict = await Storage.read_json(path=log_path)
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
        return await Storage.write_json(container=container, path=log_path)

    async def _save_stats(self, msg_time: float, stats: List[Dict]):
        log_path = self._get_path(msg_time=msg_time, option='stats_log')
        container: Dict = await Storage.read_json(path=log_path)
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
        return await Storage.write_json(container=container, path=log_path)

    async def _save_speeds(self, msg_time: float, sender: str,
                           provider: str, stations: List[Dict], client: Optional[str]):
        log_path = self._get_path(msg_time=msg_time, option='speeds_log')
        container: Dict = await Storage.read_json(path=log_path)
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
        return await Storage.write_json(container=container, path=log_path)

    async def get_users(self, now: float) -> List[Dict]:
        log_path = self._get_path(msg_time=now, option='users_log')
        container = await Storage.read_json(path=log_path)
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

    async def get_speeds(self, now: float) -> List[Dict]:
        log_path = self._get_path(msg_time=now, option='speeds_log')
        container = await Storage.read_json(path=log_path)
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

    def start(self):
        thr = Runner.async_thread(coro=self.run())
        thr.start()

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
                await self._save_users(msg_time=msg_time, users=users)
            elif mod == 'stats':
                stats = content.get('stats')
                await self._save_stats(msg_time=msg_time, stats=stats)
            elif mod == 'speeds':
                sender = content.get('U')
                provider = content.get('provider')
                stations = content.get('stations')
                client = content.get('remote_address')
                if isinstance(client, List):  # or isinstance(client, Tuple):
                    assert len(client) == 2, 'socket address error: %s' % client
                    client = '%s:%d' % (client[0], client[1])
                await self._save_speeds(msg_time=msg_time, sender=sender,
                                        provider=provider, stations=stations, client=client)
            else:
                self.warning(msg='ignore mod: %s, %s' % (mod, content))
        except Exception as e:
            self.error(msg='failed to process content: %s, %s' % (e, content))
        return True


g_recorder = StatRecorder()
