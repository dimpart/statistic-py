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

        "stat_msg-{yyyy}-{mm}-{dd}.js"

            'S' - Sender type
            'M' - Message type
            'N' - Number

        "stat_online-{yyyy}-{mm}-{dd}.js"

            'S' - Sender type
            'A' - Active flag: 1 = online, 0 = offline
            'N' - Number

    Sender type:
        https://github.com/dimchat/mkm-py/blob/master/mkm/protocol/network.py

    Message type:
        https://github.com/dimchat/dkd-py/blob/master/dkd/protocol/types.py
"""

from typing import Optional, Union, List

from dimples import ID, ReliableMessage
from dimples import ContentType, Content, CustomizedContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import CustomizedContentProcessor
from dimples.utils import Path, Log, Logging
from dimples.client import ClientMessageProcessor
from dimples.client import ClientContentProcessorCreator

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.client import Checkpoint
from bots.shared import start_bot


g_checkpoint = Checkpoint()


class BotStatContentProcessor(CustomizedContentProcessor, Logging):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, CustomizedContent), 'stat content error: %s' % content
        app = content.application
        mod = content.module
        act = content.action
        if g_checkpoint.duplicated(msg=msg):
            self.warning(msg='duplicated content: %s, %s, %s' % (app, mod, act))
            return []
        self.debug(msg='received content: %s, %s, %s' % (app, mod, act))
        return super().process(content=content, msg=msg)

    # Override
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        if app == 'chat.dim.monitor':
            return None
        return super()._filter(app=app, content=content, msg=msg)

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        mod = content.module
        if mod == 'users':
            users = content.get('users')
            self.info(msg='receive log [users]: %s' % users)
        elif mod == 'stats':
            stats = content.get('stats')
            self.info(msg='receive log [stats]: %s' % stats)
        return []


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # application customized
        if msg_type == ContentType.CUSTOMIZED.value:
            return BotStatContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)


class BotMessageProcessor(ClientMessageProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return BotContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


if __name__ == '__main__':
    start_bot(default_config=DEFAULT_CONFIG,
              app_name='ServiceBot: Statistics',
              ans_name='statistic',
              processor_class=BotMessageProcessor)
