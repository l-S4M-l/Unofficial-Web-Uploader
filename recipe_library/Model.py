import random
import struct
from typing import List, Optional
from recipe_library.Helpers import Helpers

# External dependencies that need to be available
# from texture import Texture  # Assuming Texture class is in texture module
# from helpers import Helpers  # Assuming Helpers class is in helpers module

class Model:
    def __init__(self, *args):
        # Initialize properties
        self.Textures: List = []  # List[Texture] when Texture is available
        self.ArenaID: bytearray = bytearray(8)
        self.ModelName: bytearray = bytearray(8)
        self.MaterialID: bytearray = bytearray(8)
        
        # Handle different constructor overloads based on arguments
        if len(args) == 0:
            # Default constructor - Generate random Asset ID
            random_gen = random.Random()
            for i in range(8):
                self.ArenaID[i] = random_gen.randint(0, 255)
            
            for i in range(8):
                self.MaterialID[i] = random_gen.randint(0, 255)
                
        elif len(args) == 1 and isinstance(args[0], (bytes, bytearray)):
            # Constructor with ModelBlockBytes
            ModelBlockBytes = args[0]
            self.ArenaID = bytearray(ModelBlockBytes[1:9])
            self.ModelName = bytearray(ModelBlockBytes[9:17])
            self.MaterialID = bytearray(ModelBlockBytes[0x19:0x19+8])
            
        elif len(args) == 2:
            ArenaID, ModelName = args
            self.ArenaID = bytearray(ArenaID) if isinstance(ArenaID, (bytes, bytearray)) else bytearray(ArenaID)
            
            if isinstance(ModelName, str):
                # Constructor with ArenaID and ModelName (string)
                self.ModelName = bytearray(Helpers.FileNameToBytes(ModelName))
            else:
                # Constructor with ArenaID and ModelName (bytes)
                self.ModelName = bytearray(ModelName) if isinstance(ModelName, (bytes, bytearray)) else bytearray(ModelName)
            
            # Generate random material ID
            random_gen = random.Random()
            for i in range(8):
                self.MaterialID[i] = random_gen.randint(0, 255)
                
        elif len(args) == 3:
            ArenaID, ModelName, MaterialID = args
            self.ArenaID = bytearray(ArenaID) if isinstance(ArenaID, (bytes, bytearray)) else bytearray(ArenaID)
            self.MaterialID = bytearray(MaterialID) if isinstance(MaterialID, (bytes, bytearray)) else bytearray(MaterialID)
            
            if isinstance(ModelName, str):
                # Constructor with ArenaID, ModelName (string), and MaterialID
                self.ModelName = bytearray(Helpers.FileNameToBytes(ModelName))
            else:
                # Constructor with ArenaID, ModelName (bytes), and MaterialID
                self.ModelName = bytearray(ModelName) if isinstance(ModelName, (bytes, bytearray)) else bytearray(ModelName)

    def get_bytes(self, LODIndex: int) -> bytes:
        modelBlockBytes = []
        
        modelBlockBytes.append(LODIndex & 0xFF)  # Convert to byte equivalent
        modelBlockBytes.extend(self.ArenaID)
        modelBlockBytes.extend(self.ModelName)
        modelBlockBytes.extend([0, 0, 0, 1, 0, 0, 0, 1])
        modelBlockBytes.extend(self.MaterialID)
        
        # Convert Textures.Count to bytes using SmallToBigEndian
        texture_count_big_endian = Helpers.SmallToBigEndian(len(self.Textures))
        texture_count_bytes = struct.pack('<I', texture_count_big_endian)  # 4 bytes, little endian
        modelBlockBytes.extend(texture_count_bytes)
        
        for i in range(len(self.Textures)):
            modelBlockBytes.extend(self.Textures[i].get_bytes())
        
        return bytes(modelBlockBytes)
