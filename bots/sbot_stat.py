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
                    "ID1",
                    "ID2"
                ]
            }

        "stats_log-{yyyy}-{mm}-{dd}.js"

            {
                "yyyy-mm-dd HH:MM": {
                    "S": 0,
                    "T": 1,
                    "N": 2
                }
            }

    Fields:
        'S' - Sender type
        'T' - Message type
        'N' - Number

    Sender type:
        https://github.com/dimchat/mkm-py/blob/master/mkm/protocol/network.py

    Message type:
        https://github.com/dimchat/dkd-py/blob/master/dkd/protocol/types.py
"""

from typing import Optional, Union, List

from dimples import ID, ReliableMessage
from dimples import ContentType, Content
from dimples import TextContent, CustomizedContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import BaseContentProcessor
from dimples import CustomizedContentProcessor
from dimples import Facebook
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


def get_name(identifier: ID, facebook: Facebook) -> str:
    doc = facebook.document(identifier=identifier)
    if doc is not None:
        name = doc.name
        if name is not None and len(name) > 0:
            return name
    name = identifier.name
    if name is not None and len(name) > 0:
        return name
    return str(identifier.address)


class TextContentProcessor(BaseContentProcessor, Logging):
    """ Process text message content """

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        text = content.text
        sender = msg.sender
        if g_checkpoint.duplicated(msg=msg):
            self.warning(msg='duplicated content from %s: %s' % (sender, text))
            return []
        nickname = get_name(identifier=sender, facebook=self.facebook)
        self.info(msg='received text message from %s: "%s"' % (nickname, text))
        # TODO: parse text for your business
        return []


class StatContentProcessor(CustomizedContentProcessor, Logging):
    """ Process customized stat content """

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, CustomizedContent), 'stat content error: %s' % content
        app = content.application
        mod = content.module
        act = content.action
        sender = msg.sender
        if g_checkpoint.duplicated(msg=msg):
            self.warning(msg='duplicated content from %s: %s, %s, %s' % (sender, app, mod, act))
            return []
        self.debug(msg='received content from %s: %s, %s, %s' % (sender, app, mod, act))
        return super().process(content=content, msg=msg)

    # Override
    def _filter(self, app: str, content: CustomizedContent, msg: ReliableMessage) -> Optional[List[Content]]:
        if app == 'chat.dim.monitor':
            # app ID matched
            return None
        # unknown app ID
        return super()._filter(app=app, content=content, msg=msg)

    # Override
    def handle_action(self, act: str, sender: ID, content: CustomizedContent, msg: ReliableMessage) -> List[Content]:
        mod = content.module
        if mod == 'users':
            users = content.get('users')
            self.info(msg='received station log [users]: %s' % users)
            # TODO: save login users
        elif mod == 'stats':
            stats = content.get('stats')
            self.info(msg='received station log [stats]: %s' % stats)
            # TODO: save message stats
        else:
            self.error(msg='unknown module: %s, action: %s' % (mod, act))
        # respond nothing
        return []


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


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim_bots/config.ini'


if __name__ == '__main__':
    start_bot(default_config=DEFAULT_CONFIG,
              app_name='ServiceBot: Statistics',
              ans_name='statistic',
              processor_class=BotMessageProcessor)
