import struct

class Texture:
    def __init__(self, texture_block_bytes=None, texture_channel="", texture_name=None):
        if texture_block_bytes is not None:
            self.texture_channel = texture_block_bytes[4:4 + texture_block_bytes[3]].decode('ascii')
            self.texture_name = texture_block_bytes[4 + texture_block_bytes[3]:4 + texture_block_bytes[3] + 8]
        else:
            self.texture_channel = texture_channel
            self.texture_name = texture_name if texture_name is not None else bytearray(8)

    @staticmethod
    def file_name_to_bytes(texture_name):
        return texture_name.encode('ascii')

    def get_bytes(self):
        texture_block_bytes = bytearray()
        texture_length = len(self.texture_channel)
        texture_block_bytes.extend(struct.pack('>I', texture_length))
        texture_block_bytes.extend(self.texture_channel.encode('ascii'))
        texture_block_bytes.extend(self.texture_name)
        return bytes(texture_block_bytes)

