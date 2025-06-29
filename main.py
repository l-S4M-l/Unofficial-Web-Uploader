#Unofficial Web Uploader
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from mainui import Ui_Form
from popup import Ui_Form as popup_form
from QtTitleBarManager import title_bar_handler
from components.github_handler import GithubHandler
import os
from typing import cast
from components.rpcs3_handle import rpcs3_mem
from components.psg import logoconverter
from recipe_library.Recipe import Recipe, RecipeTypes
from recipe_library.GraphicBlock import GraphicBlock
from recipe_library.Asset import Asset
from recipe_library.AssetList import AssetList
from recipe_library.Model import Model
from recipe_library.texture import Texture
from recipe_library.Helpers import Helpers
from components.database_handler import database
import psutil
import pygetwindow as gw
import win32process
import hashlib
import shutil
import time
import random


class logo_worker(QtCore.QThread):
    update_percent = QtCore.pyqtSignal(int)
    done_signal = QtCore.pyqtSignal()

    


class mainUi(QtWidgets.QWidget, Ui_Form):
    def setup(self,Form):
        
        self.cwd = os.getcwd().replace("\\","/")
        self.backup_on = False
        self.db_handle = database()
        self.psg_handler = logoconverter()
        title_bar_handler(Form, self.titlebar_cont, self.close_but, self.mini_but)

        self.delete_old_repos = True
        self.DeleteRepos = cast(QtWidgets.QCheckBox, self.DeleteRepos)
        self.DeleteRepos.setChecked(self.delete_old_repos)
        self.popup_ui = popup_ui()

        if os.path.exists("github_token.txt"):
                with open("github_token.txt", "r") as file:
                    token = file.read().strip()
                    
                    user, login_valid = GithubHandler().check_github_login(token)

                    if GithubHandler().check_github_login(token)[1] == True:
                        self.github_handle = GithubHandler(token)

                        self.github_handle.username = user
                        self.github_status(True)

        try:
            if os.path.exists(f"{self.cwd}/backup_recipes") == True:
                if "recipe" in os.listdir(f"{self.cwd}/backup_recipes")[0]:
                    self.backup_button:QtWidgets.QPushButton = self.backup_button
                    self.backup_on = True
        except:
            pass



        self.events()
    
    def events(self):
        self.github.clicked.connect(self.github_clicked)
        self.attach_game.clicked.connect(self.attach_game_func)
        self.clickme.clicked.connect(self.recipe_clicked)
        self.backup_button.clicked.connect(self.load_backup_recipe)
        self.DeleteRepos.clicked.connect(self.delete_repos)
        
    def delete_repos(self):
        self.delete_old_repos = self.DeleteRepos.isChecked()

    def github_clicked(self):
        self.github_handle = GithubHandler()
        
        self.github_handle.token = self.github_handle.login_with_github()
        if self.github_handle.token != None:
            with open("github_token.txt", "w+") as file:
                file.write(self.github_handle.token)

            self.github_handle.username, login_status = self.github_handle.check_github_login(self.github_handle.token)
            self.github_status(login_status)
    
    def github_status(self,status:bool):
        if status == True:
            self.statusCircle.setStyleSheet("""
            background-color: rgb(0, 255, 0);
            border-radius:10px;
            """)
            self.status.setText("Connected")

            self.attach_game = cast(QtWidgets.QPushButton, self.attach_game)

            self.attach_game.setEnabled(True)
        
        elif status == False:
            self.statusCircle.setStyleSheet("""
            background-color: rgb(255, 0, 0);
            border-radius:10px;
            """)
            self.status.setText("Disconnected")

            self.attach_game = cast(QtWidgets.QPushButton, self.attach_game)

            self.attach_game.setEnabled(False)



    def attach_game_func(self,auto=False):
        try:
            self.rpcs3_process = rpcs3_mem()

            self.attach_status.setText("RPCS3 Attached")

            self.clickme.setEnabled(True)

            self.backup_button.setEnabled(self.backup_on)

        except:
            print("failed to attach to rpcs3")
    
    def get_skate3_path(self):
        PID = self.rpcs3_process.process.process_id
        proc = psutil.Process(PID)
        exe_path = proc.exe()
        
        for window in gw.getAllWindows():
            try:
                hwnd = window._hWnd
                _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
                if win_pid == PID and window.title:  # Only if it has a title
                    window_title = window.title
            except Exception:
                continue
        
        if window_title == None:
            self.popup("failed to get skate 3 version handle")
            self.clickme.setEnabled(False)

            self.backup_button.setEnabled(False)
            return
        
        blus = "blus" in window_title.lower()
        bles = "bles" in window_title.lower()
        
        if blus == True:
            region = "blus"
        elif bles == True:
            region = "bles"
        else:
            region = "blus"


        return exe_path, region

    
    def load_backup_recipe(self):
        folder = f"{self.cwd}/backup_recipes"
        files = sorted(os.listdir(folder), key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)

        with open(f"{folder}/{files[0]}","rb") as file:
            backup_recipe_bytes = file.read()
        
        self.rpcs3_process.write_recipe(backup_recipe_bytes)

    def recipe_clicked(self):

        # reading and converting textures
        recipe_bytes = self.rpcs3_process.read_recipe()

        recipe = Recipe(recipe_bytes=recipe_bytes, recipe_type=RecipeTypes.CREATEACHARACTER)

        if os.path.exists(f"{self.cwd}/backup_recipes") == False:
            os.mkdir(f"{self.cwd}/backup_recipes")

        
        with open(f"{self.cwd}/backup_recipes/{int(time.time())}.recipe","wb") as file:
            recipe_bytes = recipe.get_bytes()
            padded_result = recipe_bytes.ljust(6500, b'\x00')
            file.write(padded_result)
            self.backup_button.setEnabled(True)


        Texture_list = {}

        for asset in recipe.asset_lists:
            for texture in asset.assets[0].Models[0].Textures:
                if texture.texture_channel == "diffuse":
                    Texture_list[asset.asset_folder_name] = Helpers.file_name_bytes_to_string(texture.texture_name)

        

        exe_path, region = self.get_skate3_path()

        root_path = "/".join(exe_path.split("\\")[:-1])

        with open(f"{root_path}/config/games.yml") as file:
            games_data = file.read()
            file.close()

        games_data = games_data.split("\n")

        for i in games_data:
            if region.lower() in i.lower():
                game_path = i.split(": ")[1].replace("//","/")

        try:
            if game_path != None:

                createacharacter_path = f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter/texture"


                changed_textures = {}
                for asset_name in Texture_list.keys():
                    texture = Texture_list[asset_name]

                    with open(f"{createacharacter_path}/{texture}", "rb") as file:
                        psg_bytes = file.read()

                    current_hash = hashlib.md5(psg_bytes).hexdigest()
                    file_hash = self.db_handle.get_file_hash(texture)

                    if file_hash != current_hash:
                        changed_textures[asset_name] = texture
                
                if os.path.exists(f"{self.cwd}/output_textures") == False:
                    os.mkdir(f"{self.cwd}/output_textures")
                
                final_texture_filenames = {}

                for asset_name in changed_textures.keys():
                    out_filename = random.randint(0,9999999999)

                    final_texture_filenames[asset_name] = (changed_textures[asset_name], out_filename)

                    self.psg_handler.psg_to_png(f"{createacharacter_path}/{changed_textures[asset_name]}", f"{self.cwd}/output_textures", out_filename, 512)
                    os.remove(f"{self.cwd}/assets/{changed_textures[asset_name][:-4]}.dds")

                if os.path.exists(f"{self.cwd}/output_psgs") == False:
                    os.mkdir(f"{self.cwd}/output_psgs")

                for asset_name in final_texture_filenames.keys():
                    self.psg_handler.convert(f"{self.cwd}/output_textures", final_texture_filenames[asset_name][1], f"{self.cwd}/output_psgs") # add opacity option when reconverting
                
                shutil.rmtree(f"{self.cwd}/output_textures")



                #github code
                
                #delete_old_repos
                if self.delete_old_repos == True:
                    repo_list = self.github_handle.list_repos()

                    for repos in repo_list:
                        if "Skate_3_textures" in repos:

                            self.github_handle.delete_repo(repos)

                repo = random.randint(0,9999999999)
                self.github_handle.create_repo(f"{repo}-Skate_3_textures")

                link_list = {}

                for psg_name in os.listdir(f"{self.cwd}/output_psgs"):
                    with open(f"{self.cwd}/output_psgs/{psg_name}","rb") as file:
                        filebytes = file.read()

                    download_url = self.github_handle.upload_file(f"{repo}-Skate_3_textures", psg_name, filebytes)
                    if download_url != None:
                        for asset_name in final_texture_filenames.keys():
                            if f"{final_texture_filenames[asset_name][1]}.psg" == psg_name:
                                link_list[asset_name] = download_url
                
                shutil.rmtree(f"{self.cwd}/output_psgs")

                recipe = self.final_recipe_write(recipe, link_list)

                self.rpcs3_process.write_recipe(recipe.get_bytes())
                print("done")






            else:
                return None
        except Exception as e:
            raise e
            print(e)
            
    def final_recipe_write(self, recipe:Recipe, logo_link_list:dict):
        recipe.remove_low_lod_models()

        used_ids_list = []
        for link_asset in logo_link_list.keys():
            random_arena = Helpers.random_high_res_arena()
            while random_arena in used_ids_list:
                print("already in list")
                random_arena = Helpers.random_high_res_arena()
            


            recipe = self.add_texture_block(recipe,logo_link_list[link_asset], random_arena, link_asset)

        return recipe

    def add_texture_block(self, recipe, link, overwrite_texture, asset_name):
        misc_exists = False
        for asset_list in recipe.asset_lists:
            if asset_list.asset_folder_name == "Misc":
                misc_exists = True
                break

        if misc_exists != True:
            print("No misc block found, creating a new one.")
            misc_block = AssetList(asset_folder_name="Misc")

            recipe.asset_lists.append(misc_block)

            for i in recipe.asset_lists:
                if i.asset_folder_name == "Misc":
                    i.assets.append(Asset())
                    break

        for asset in recipe.asset_lists:
            if asset.asset_folder_name == "Misc":
                model = Model()
                model.ModelName = bytearray(b"\x00\x00\x0f\xC0\x03\xE3\x88\x11")
                

                model.Textures.append(Texture(texture_channel = "decal", texture_name = overwrite_texture))
                
                asset.assets[0].Models.append(model)


                for asset_2 in recipe.asset_lists:
                    if asset_2.asset_folder_name == asset_name:
                        for texture in asset_2.assets[0].Models[0].Textures:
                            if texture.texture_channel == "diffuse":
                                texture.texture_name = overwrite_texture
                break

        graphic = graphic = GraphicBlock()
        graphic.URL = link.replace("https://raw.githubusercontent.com","http://127.0.0.1")
        graphic.MaterialID = model.MaterialID


        for asset in recipe.asset_lists:
            if asset.asset_folder_name == "Misc":
                graphic.AssetID = asset.assets[0].AssetID
                recipe.graphic_blocks.append(graphic)
                break

        return recipe

    def popup(self, message, titlebar_title = "Popup"):
        self.popup_ui.setupUi(self.popup_ui, message, titlebar_title)
        self.popup_ui.setWindowModality(QtCore.Qt.ApplicationModal)
        self.popup_ui.show()


class popup_ui(QtWidgets.QWidget, popup_form):
    def setupUi(self, Form, message, titlebar_title):
        super().setupUi(Form)
        title_bar_handler(Form, self.titlebar_cont, self.close_but, self.mini_but)
        self.popup_title.setText(titlebar_title)
        self.message.setText(message)
        
        self.events()

    def events(self):
        pass



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = mainUi()
    ui.setupUi(Form)
    ui.setup(Form)
    Form.show()
    sys.exit(app.exec_())
