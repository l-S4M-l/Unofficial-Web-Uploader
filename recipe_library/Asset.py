import random
import struct

class Asset:
    def __init__(self, asset_bytes=None):
        self.Models = []
        self.AssetID = bytearray(8)

        if asset_bytes is not None:
            self.AssetID = asset_bytes[:8]
        else:
            # Generate random Asset ID
            for i in range(8):
                self.AssetID[i] = random.randint(0, 255)

    def change_textures(self, new_texture_bytes, texture_channel):
        for model in self.Models:
            if any(x.texture_channel == texture_channel for x in model.textures):
                next(x for x in model.textures if x.texture_channel == texture_channel).texture_name = new_texture_bytes

    def get_bytes(self):
        asset_block_bytes = bytearray()

        asset_block_bytes.extend(self.AssetID)
        asset_block_bytes.extend(struct.pack('>I', len(self.Models)))  # Big-endian

        for i, model in enumerate(self.Models):
            lod_index = 0 if i == 0 else 2
            asset_block_bytes.extend(model.get_bytes(lod_index))

        return bytes(asset_block_bytes)

