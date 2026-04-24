# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2026 Albert Moky
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

import weakref
from typing import Optional

from dimples import DateTime
from dimples import EntityType, ID
from dimples import Content, Envelope
from dimples import CommonFacebook
from dimples import DocumentUtils

from ..utils import Log


class RequestFilter:

    def __init__(self, facebook: CommonFacebook):
        super().__init__()
        self.__facebook = weakref.ref(facebook)

    @property
    def facebook(self) -> Optional[CommonFacebook]:
        return self.__facebook()

    async def get_nickname(self, identifier: ID) -> Optional[str]:
        facebook = self.facebook
        visa = await facebook.get_visa(user=identifier)
        if visa is not None:
            return visa.name
        doc = await facebook.get_document(identifier=identifier)
        if doc is not None:
            return DocumentUtils.get_document_name(document=doc)

    async def filter_text(self, text: str, content: Content, envelope: Envelope) -> Optional[str]:
        sender = envelope.sender
        #
        #  ignore bot message
        #
        if EntityType.BOT == sender.type:
            Log.info('ignore message from another bot: %s, "%s"' % (sender, text))
            return None
        elif EntityType.STATION == sender.type:
            Log.info('ignore message from station: %s, "%s"' % (sender, text))
            return None
        #
        #  ignore timeout message
        #
        req_time = content.time
        assert req_time is not None, 'request error: %s' % envelope
        dt = DateTime.now() - req_time
        if dt > 600:
            # Old message, ignore it
            Log.warning(msg='ignore expired message from %s: %s' % (sender, req_time))
            return None
        #
        #  only filter for group message
        #
        if content.group is None:
            # personal message
            return text
        #
        #   checking for group message
        #
        receiver = envelope.receiver
        bot_name = await self.get_nickname(identifier=receiver)
        if bot_name is not None and len(bot_name) > 0:
            at = '@%s ' % bot_name
            naked = text.replace(at, '')
            at = '@%s' % bot_name
            if naked.endswith(at):
                naked = naked[:-len(at)]
            if naked != text:
                return naked
        else:
            assert False, 'sender error: %s' % sender
        Log.info('ignore group message that not querying me("%s" %s): "%s"' % (bot_name, receiver, text))
