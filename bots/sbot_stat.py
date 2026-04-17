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

from typing import Optional, Union, List

from dimples import ReliableMessage
from dimples import ContentType, Content
from dimples import CustomizedContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import CommonFacebook, CommonMessenger
from dimples import MessageExtensions, shared_message_extensions

from dimples.client import ClientMessageProcessor
from dimples.client.cpu import BaseCustomizedContentHandler
from dimples.client.cpu import AppCustomizedFilter
from dimples.client.cpu import CustomizedFilterExtensions

from dimples.utils import Log, Logging
from dimples.utils import Path, Runner

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client import ClientContentProcessorCreator

from bots.shared import GlobalVariable
from bots.shared import create_config, start_bot
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
            self.info(msg='received station log [%s] users: %s' % (content.time, users))
            g_recorder.add_log(content=content)
        elif mod == 'stats':
            stats = content.get('stats')
            self.info(msg='received station log [%s] stats: %s' % (content.time, stats))
            g_recorder.add_log(content=content)
        elif mod == 'speeds':
            user = content.get('U')
            provider = content.get('provider')
            stations = content.get('stations')
            remote = content.get('remote_address')
            self.info(msg='received client log [%s] speeds count: %d, %s, %s => %s'
                          % (content.time, len(stations), remote, user, provider))
            g_recorder.add_log(content=content)
        else:
            act = content.action
            self.error(msg='unknown module: %s, action: %s, [%s] %s' % (mod, act, content.time, content))
        # respond nothing
        return []


# -----------------------------------------------------------------------------
#  Message Extensions
# -----------------------------------------------------------------------------


def message_extensions() -> Union[MessageExtensions, CustomizedFilterExtensions]:
    return shared_message_extensions


def get_app_filter() -> AppCustomizedFilter:
    ext = message_extensions()
    app_filter = ext.customized_filter
    if not isinstance(app_filter, AppCustomizedFilter):
        app_filter = AppCustomizedFilter()
        ext.customized_filter = app_filter
    return app_filter


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
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/stat.ini'


async def main():
    # create global variable
    shared = GlobalVariable()
    config = await create_config(app_name='ServiceBot: Statistics', default_config=DEFAULT_CONFIG)
    await shared.prepare(config=config)
    # register handlers
    register_customized_handlers()
    #
    #  Start recorder
    #
    g_recorder.config = shared.config
    g_recorder.start()
    #
    #  Create & start the bot
    #
    client = await start_bot(ans_name='statistic', processor_class=BotMessageProcessor)
    Log.warning(msg='bot stopped: %s' % client)


if __name__ == '__main__':
    Runner.sync_run(main=main())
