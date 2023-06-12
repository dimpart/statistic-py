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
from dimples import ContentType, Content, TextContent
from dimples import ContentProcessor, ContentProcessorCreator
from dimples import BaseContentProcessor
from dimples import CommonFacebook
from dimples.utils import Path, Log, Logging
from dimples.client import ClientMessageProcessor
from dimples.client import ClientContentProcessorCreator

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from bots.shared import GlobalVariable, start_bot


def get_config(option: str) -> Optional[str]:
    """ get option value from 'monitor' section in 'config.ini' """
    shared = GlobalVariable()
    config = shared.config
    return config.get_string(section='monitor', option=option)


def get_name(identifier: ID, facebook: CommonFacebook) -> str:
    doc = facebook.document(identifier=identifier)
    if doc is not None:
        name = doc.name
        if name is not None and len(name) > 0:
            return name
    name = identifier.name
    if name is not None and len(name) > 0:
        return name
    return str(identifier.address)


class BotTextContentProcessor(BaseContentProcessor, Logging):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, TextContent), 'text content error: %s' % content
        sender = msg.sender
        facebook = self.facebook
        assert isinstance(facebook, CommonFacebook), 'facebook error: %s' % facebook
        nickname = get_name(identifier=sender, facebook=facebook)
        text = content.text
        self.debug(msg='received text message from %s: %s' % (nickname, text))
        # TODO: parse text for your business
        return []


class BotContentProcessorCreator(ClientContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return BotTextContentProcessor(facebook=self.facebook, messenger=self.messenger)
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
