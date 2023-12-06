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

from typing import Optional

from dimples import InstantMessage, SecureMessage
from dimples import FileContent
from dimples.client import ClientMessagePacker

from .emitter import Emitter


class ClientPacker(ClientMessagePacker):

    # Override
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        # make sure visa.key exists before encrypting message
        content = msg.content
        if isinstance(content, FileContent):
            if content.get('data') is not None:  # and content.get('URL') is not None:
                # call emitter to encrypt & upload file data before send out
                key = self.messenger.get_encrypt_key(msg=msg)
                assert key is not None, 'failed to get msg key for: %s -> %s' % (msg.sender, msg.receiver)
                # call emitter to encrypt & upload file data before send out
                emitter = Emitter()
                if not emitter.upload_file_data(content=content, password=key, msg=msg):
                    # failed
                    return None
                elif content.url is None:
                    # waiting
                    return None
        try:
            s_msg = super().encrypt_message(msg=msg)
        except Exception as error:
            self.error(msg='failed to encrypt message: %s' % error)
            return None
        # receiver = msg.receiver
        # if receiver.is_group:
        #     # reuse group message keys
        #     messenger = self.messenger
        #     key = messenger.cipher_key(sender=msg.sender, receiver=receiver)
        #     key['reused'] = True
        # # TODO: reuse personal message key?
        return s_msg

    # Override
    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        i_msg = super().decrypt_message(msg=msg)
        if i_msg is None:
            # failed to decrypt message, visa.key changed?
            pass
            # self._push_visa(contact=msg.sender)
        else:
            content = i_msg.content
            if isinstance(content, FileContent):
                if content.get('data') is None and content.get('URL') is not None:
                    # now received file content with remote data,
                    # which must be encrypted before upload to CDN;
                    # so keep the password here for decrypting after downloaded.
                    key = self.messenger.get_decrypt_key(msg=msg)
                    assert key is not None, 'failed to get password: %s -> %s' % (i_msg.sender, i_msg.receiver)
                    # keep password to decrypt data after downloaded
                    content.password = key
        return i_msg

    # def _push_visa(self, contact: ID):
    #     checker = QueryFrequencyChecker()
    #     if not checker.document_response_expired(identifier=contact):
    #         # response not expired yet
    #         self.debug(msg='visa response not expired yet: %s' % contact)
    #         return False
    #     else:
    #         self.info(msg='push visa to: %s' % contact)
    #     user = self.facebook.current_user
    #     visa = None if user is None else user.visa
    #     if visa is None or not visa.valid:
    #         self.error(msg='user visa error: %s => %s' % (user, visa))
    #         return False
    #     me = user.identifier
    #     command = DocumentCommand.response(identifier=me, document=visa)
    #     self.messenger.send_content(sender=me, receiver=contact, content=command, priority=1)
    #     return True
