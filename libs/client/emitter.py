# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from typing import Optional, Dict

from dimples import TransportableData
from dimples import SymmetricKey, ID
from dimples import InstantMessage
from dimples import Content, TextContent, FileContent
from dimples.client import ClientMessenger

from ..utils import md5, hex_encode
from ..utils import Singleton, Log, Logging


@Singleton
class Emitter(Logging):

    def __init__(self):
        super().__init__()
        self.__messenger: Optional[ClientMessenger] = None
        # filename => task
        self.__outgoing: Dict[str, InstantMessage] = {}

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: ClientMessenger):
        self.__messenger = transceiver

    def _add_task(self, filename: str, msg: InstantMessage):
        self.__outgoing[filename] = msg

    def _pop_task(self, filename: str) -> Optional[InstantMessage]:
        return self.__outgoing.pop(filename, None)

    def purge(self):
        # TODO: remove expired messages in the map
        pass

    def upload_success(self, filename: str, url: str):
        """ callback when file data uploaded to CDN and download URL responded """
        msg = self._pop_task(filename=filename)
        if msg is None:
            self.error(msg='failed to get task: %s, url: %s' % (filename, url))
            return
        self.info(msg='get task for file: %s, url: %s' % (filename, url))
        # file data uploaded to FTP server, replace it with download URL
        # and send the content to station
        content = msg.content
        assert isinstance(content, FileContent), 'file content error: %s' % content
        # content.data = None
        content.url = url
        self._send_instant_message(msg=msg)

    def upload_failed(self, filename: str):
        """ callback when failed to upload file data """
        msg = self._pop_task(filename=filename)
        if msg is None:
            self.error(msg='failed to get task: %s' % filename)
            return
        self.info(msg='get task for file: %s' % filename)
        # file data failed to upload, mark it error
        msg['error'] = {
            'message': 'failed to upload file'
        }
        self._save_instant_message(msg=msg)

    def upload_file_data(self, content: FileContent, password: SymmetricKey, msg: InstantMessage) -> bool:
        """
        Send file data encrypted with password

        :param content:  file content
        :param password: encrypt/decrypt key
        :param msg:      outgoing message
        :return: False on error
        """
        # 0. check file content
        data = content.data
        if data is None:
            self.warning(msg='already uploaded: %s' % content.url)
            return False
        assert content.password is not None, 'file content error: %s' % content
        assert content.url is not None, 'file content error: %s' % content
        # 1. save original file data
        filename = content.filename
        assert filename is not None, 'file content error: %s' % content
        size = cache_file_data(data=data, filename=filename)
        if size != len(data):
            self.error(msg='failed to save file data (len=%d): %s' % (len(data), filename))
            return False
        # 2. add upload task with encrypted data
        encrypted = password.encrypt(data=data, extra=content.dictionary)
        filename = filename_from_data(data=encrypted, filename=filename)
        sender = msg.sender
        # 3. upload encrypted file data
        url = upload_encrypted_data(data=encrypted, filename=filename, sender=sender)
        if url is None:
            # uploading in background thread?
            self.info(msg='wait for uploading: %s -> %s' % (content.filename, filename))
            self._add_task(filename=filename, msg=msg)
        else:
            # upload success
            self.info(msg='uploaded filename: %s -> %s => %s' % (content.filename, filename, url))
            content.url = url
        # 3. replace file data with URL & decrypt key
        content.password = password
        content.data = None
        return True

    def _save_instant_message(self, msg: InstantMessage):
        # TODO: save into local storage
        pass

    def _send_instant_message(self, msg: InstantMessage):
        self.info(msg='send message (type=%d): %s -> %s' % (msg.content.type, msg.sender, msg.receiver))
        # send by shared messenger
        messenger = self.messenger
        messenger.send_instant_message(msg=msg, priority=1)
        self._save_instant_message(msg=msg)

    def send_content(self, content: Content, receiver: ID):
        messenger = self.messenger
        i_msg, r_msg = messenger.send_content(sender=None, receiver=receiver, content=content)
        if r_msg is None:
            self.warning(msg='not send yet (type=%d): %s' % (content.type, receiver))
            return
        # save instant message
        self._save_instant_message(msg=i_msg)

    def send_image_message(self, image: bytes, thumbnail: bytes, receiver: ID):
        """
        Send image message to receiver

        :param image:     image data
        :param thumbnail: image thumbnail
        :param receiver:  destination
        """
        filename = '%s.jpeg' % hex_encode(data=md5(data=image))
        ted = TransportableData.create(data=image)
        content = FileContent.image(filename=filename, data=ted)
        content['length'] = len(image)
        content.thumbnail = thumbnail
        self.send_content(content=content, receiver=receiver)

    def send_text_message(self, text: str, receiver: ID):
        """
        Send text message to receiver

        :param text:     text message
        :param receiver: destination
        """
        content = TextContent.create(text=text)
        self.send_content(content=content, receiver=receiver)


#
#   CDN Utils
#


def filename_from_data(data: bytes, filename: str) -> str:
    pos = filename.rfind('.')
    if pos < 0:
        ext = 'jpeg'
    else:
        ext = filename[pos+1:]
        filename = filename[:pos]
    if len(filename) != 32:
        filename = hex_encode(data=md5(data=data))
    return '%s.%s' % (filename, ext)


def cache_file_data(data: bytes, filename: str) -> int:
    # TODO: save file data
    size = len(data)
    Log.info(msg='save file: %s, length: %d' % (filename, size))
    return size


def upload_encrypted_data(data: bytes, filename: str, sender: ID) -> Optional[str]:
    # TODO: save file data
    size = len(data)
    Log.info(msg='upload file: %s, length: %d, sender: %s' % (filename, size, sender))
    return None
