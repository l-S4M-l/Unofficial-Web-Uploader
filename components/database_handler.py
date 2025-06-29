import sqlite3


class database():
    def __init__(self):
        self.db = sqlite3.connect("texture_data.db")
        self.c = self.db.cursor()

    def get_file_hash(self, filename):
        filename:str = filename[:-4]
        filename = filename.lower()

        self.c.execute("""SELECT original_hashes FROM texture_data WHERE ingamename=?""",(filename,))
        
        try:
            data = self.c.fetchall()[0][0]
        except IndexError:
            return ""

        return data
    




if __name__ == "__main__":
    db = database()

    hash = db.get_file_hash("0x2C7F381800172629.psg")
    print(hash)