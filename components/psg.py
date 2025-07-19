import subprocess
import os
import shutil
import tempfile
from PIL import Image as Pil_Image

class logoconverter():
    def __init__(self):
        self.cwd = os.getcwd().replace('\\', '/')
        self.rw_64_PRIME = 0x100000001b3

    def image_to_dds(self,texture_path,input_image_path):
        subprocess.run(f'assets/texconv.exe -y -f DXT5 -m 10 -o "{texture_path}" "{input_image_path}"')

    def dds_to_psg(self,dds_path,alias):
        os.chdir(f"{self.cwd}/assets/PsgCliTool")
        subprocess.run(f'PsgCliTool.exe "{dds_path}" {alias}.psg')
        os.chdir(f"{self.cwd}")

    def rw_hash64_string(self, s: str, hash_value: int) -> bytes:
        for b in s.encode('utf-8'):
            hash_value *= self.rw_64_PRIME
            hash_value ^= b
            hash_value &= 0xFFFFFFFFFFFFFFFF

        data = hash_value.to_bytes(8, 'big')
    
        return data
    
    def convert(self, texture_path, alias, output_path):
        input_image_path = f"{texture_path}/{alias}.png"
        dds_path = f"{texture_path}/{alias}.dds"

        # Convert PNG to DDS
        self.image_to_dds(texture_path, input_image_path)

        # Convert DDS to PSG
        self.dds_to_psg(dds_path, alias)

        # Clean up DDS file
        if os.path.exists(dds_path):
            os.remove(dds_path)

        if os.path.exists(f"{self.cwd}/assets/PsgCliTool/{alias}.psg"):
            shutil.copy(f"{self.cwd}/assets/PsgCliTool/{alias}.psg", f"{output_path}/{alias}.psg")
            os.remove(f"{self.cwd}/assets/PsgCliTool/{alias}.psg")

        hash:bytes = self.rw_hash64_string(f"{alias}.Texture", 0xcbf29ce484222325)

        with open(f"{output_path}/{alias}.psg", "r+b") as file:
            file.seek(0x1AC)
            file.write(hash)

    def psg_to_png(self, psg_path, output_path, output_filename, out_res, opacity=10):
        os.chdir(f"{self.cwd}/assets/PsgCliTool")
        # Run the tool and capture stdout as bytes
        psg_dds_sub = subprocess.run(
            f'PsgCliTool.exe "{psg_path}"',
            shell=True,
            stdout=subprocess.PIPE
        )
        os.chdir(f"{self.cwd}")

        if psg_dds_sub.returncode != 0:
            print("Error: PsgCliTool failed")
            return None

        dds_bytes = (psg_dds_sub.stdout).decode().split(" ")
        final_bytes = bytearray()
        for outbyte in dds_bytes:
            if outbyte == "":
                continue

            if outbyte == "0x00":

                final_bytes.append(0x00)
            else:
                byte = int(outbyte, 16).to_bytes(1, byteorder="big")
                final_bytes.append(byte[0])

        final_bytes = bytes(final_bytes)
        
        filename = os.path.basename(psg_path)[:-4]

        with open(f"{self.cwd}/assets/{filename}.dds", "wb") as f:
            f.write(final_bytes)

        subprocess.run(f'{self.cwd}/assets/texconv.exe -ft PNG -o "{output_path}/" "{self.cwd}/assets/{filename}.dds"')

        image = Pil_Image.open(f"{output_path}/{filename}.png").convert("RGB")

        image = image.convert("RGBA")

        image = image.resize((out_res, out_res))

        image = self.scale_opacity(img=image, scale_factor=opacity/100)

        image.save(f"{output_path}/{output_filename}.png")
        os.remove(f"{output_path}/{filename}.png")
        
    @staticmethod 
    def scale_opacity(img, scale_factor):
            # Ensure scale_factor is between 0 and 1
            if scale_factor < 0:
                scale_factor = 0
            elif scale_factor > 1:
                scale_factor = 1

            # Get the data of the image
            datas = img.getdata()

            # Create a new list to store modified pixel data
            new_data = []
            for item in datas:
                # Scale the alpha value
                new_alpha = int(item[3] * scale_factor)
                new_data.append((item[0], item[1], item[2], new_alpha))

            # Update image data
            img.putdata(new_data)
            return img


        
if __name__ == "__main__":
    logoconverter2 = logoconverter()
    #a = logoconverter.rw_hash64_string(f"206.Texture", 0xcbf29ce484222325)
    #a = logoconverter.convert(logoconverter.cwd, "206")
    hash:bytes = logoconverter2.rw_hash64_string(f"7812768368712.Texture", 0xcbf29ce484222325)

    print(hash.hex())