import struct

class S3RGB:
    def __init__(self):
        self.r = 0.0
        self.g = 0.0
        self.b = 0.0

class Asset:
    def __init__(self):
        self.AssetID = bytearray(8)
        self.Models = [Model()]

class Model:
    def __init__(self):
        self.MaterialID = bytearray(8)

class RGBBlock:
    def __init__(self, BlockBytes:bytes = None, RGB = None, Asset = None):

        if BlockBytes != None:
            self.RGB = S3RGB()
            self.AssetID = bytearray(8)
            self.MaterialID = bytearray(8)

            # Red
            RBytes = BlockBytes[4:8][::-1]
            self.RGB.r = struct.unpack('f', RBytes)[0]
            # Green
            GBytes = BlockBytes[8:12][::-1]
            self.RGB.g = struct.unpack('f', GBytes)[0]
            # Blue
            BBytes = BlockBytes[12:16][::-1]
            self.RGB.b = struct.unpack('f', BBytes)[0]

            # Store ArenaID and Material ID that the RGB takes effect on
            self.AssetID = BlockBytes[0x1C:0x1C+8]
            self.MaterialID = BlockBytes[0x24:0x24+8]
        elif Asset != None:
            self.RGB = RGB
            self.AssetID = Asset.AssetID
            self.MaterialID = Asset.Models[0].MaterialID
        else:
            print("failed to load, correct data was not parsed")

    def get_bytes(self, index):
        RGBBlockBytes = bytearray()

        RGBBlockBytes.extend(bytearray([0, 0, 0, index]))  # RGB Block Index
        RGBBlockBytes.extend(struct.pack('f', self.RGB.r)[::-1])  # Red
        RGBBlockBytes.extend(struct.pack('f', self.RGB.g)[::-1])  # Green
        RGBBlockBytes.extend(struct.pack('f', self.RGB.b)[::-1])  # Blue
        RGBBlockBytes.extend(struct.pack('f', self.RGB.r)[::-1])  # Red
        RGBBlockBytes.extend(struct.pack('f', self.RGB.g)[::-1])  # Green
        RGBBlockBytes.extend(struct.pack('f', self.RGB.b)[::-1])  # Blue
        RGBBlockBytes.extend(self.AssetID)
        RGBBlockBytes.extend(self.MaterialID)

        return bytes(RGBBlockBytes)

