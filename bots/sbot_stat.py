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
"""

import sys
from typing import Optional, List

from dimples import ReliableMessage
from dimples import ContentType, Content
from dimples import CustomizedContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import CommonFacebook, CommonMessenger

from dimples.client import ClientMessageProcessor
from dimples.client.cpu import BaseCustomizedContentHandler
from dimples.client.cpu.app.filter import get_app_filter

from dimples.utils import SysArgvParser
from dimples.utils import init_logger
from dimples.utils import Log, LogLevel, Logging
from dimples.utils import Runner
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client import ClientContentProcessorCreator

from bots.shared import GlobalVariable
from bots.shared import create_config, start_bot
from bots.shared import show_help

from bots.stat_recoder import g_recorder
from bots.stat_text import TextContentProcessor


class StatHandler(BaseCustomizedContentHandler, Logging):

    def __init__(self):
        super().__init__()
        self.__users_listeners = None
        self.__stats_listeners = None
        self.__speeds_listeners = None

    # Override
    async def handle_action(self, content: CustomizedContent, msg: ReliableMessage,
                            messenger: CommonMessenger) -> List[Content]:
        mod = content.module
        if mod == 'users':
            users = content.get('users')
            self.info('received station log [%s] users: %s', content.time, users)
            g_recorder.add_log(content=content)
        elif mod == 'stats':
            stats = content.get('stats')
            self.info('received station log [%s] stats: %s', content.time, stats)
            g_recorder.add_log(content=content)
        elif mod == 'speeds':
            user = content.get('U')
            provider = content.get('provider')
            stations = content.get('stations')
            remote = content.get('remote_address')
            self.info('received client log [%s] speeds count: %d, %s, %s => %s',
                      content.time, len(stations), remote, user, provider)
            g_recorder.add_log(content=content)
        else:
            act = content.action
            self.error('unknown module: %s, action: %s, [%s] %s', mod, act, content.time, content)
        # respond nothing
        return []


# -----------------------------------------------------------------------------
#  Message Extensions
# -----------------------------------------------------------------------------


def register_customized_handlers():
    app_filter = get_app_filter()
    # 'chat.dim.monitor:*'
    handler = StatHandler()
    app = 'chat.dim.monitor'
    modules = ['users', 'stats', 'speeds']
    for mod in modules:
        app_filter.set_content_handler(app=app, mod=mod, handler=handler)


#
#   CPU - Content Processing Unit
#


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: str) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return TextContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)


class BotMessageProcessor(ClientMessageProcessor):

    # Override
    def _create_creator(self, facebook: CommonFacebook, messenger: CommonMessenger) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


#
#  show logs
#
LOG_LEVEL = LogLevel.DEVELOP

BOT_NAME = 'statistic'

APP_NAME = 'ServiceBot: Statistics'

DEFAULT_CONFIG = '/etc/dim/stat.ini'


async def main():
    #
    #  parse cmd parameters
    #
    sys_argv = SysArgvParser.parse(shortopts='hf:ld:',
                                   longopts=['help', 'config=', 'log-location', 'log-dir='])
    if sys_argv is None:
        show_help(app_name=APP_NAME, cmd=sys.argv[0], default_config=DEFAULT_CONFIG)
        sys.exit(1)
    #
    #  init logger
    #
    show_location = sys_argv.has_opt(opt='log-location')
    log_directory = sys_argv.get_opt(opt='log-dir')
    init_logger(name=BOT_NAME, level=LOG_LEVEL, show_location=show_location, directory=log_directory)
    #
    #  create config
    #
    config = await create_config(sys_argv=sys_argv, default_config=DEFAULT_CONFIG)
    if config is None:
        show_help(app_name=APP_NAME, cmd=sys.argv[0], default_config=DEFAULT_CONFIG)
        sys.exit(1)
    #
    #  register handlers
    #
    register_customized_handlers()
    #
    #  Start recorder
    #
    shared = GlobalVariable()
    g_recorder.config = shared.config
    g_recorder.start()
    #
    #  Create & start the bot
    #
    client = await start_bot(ans_name=BOT_NAME, processor_class=BotMessageProcessor)
    Log.warning('bot stopped: %s', client)


if __name__ == '__main__':
    Runner.sync_run(main=main())
