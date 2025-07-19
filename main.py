from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from mainui import Ui_Form
from popup import Ui_Form as popup_form
from toManyTex import Ui_Form as toManyTex_form
from QtTitleBarManager import title_bar_handler
from components.github_handler import GithubHandler
import os
from typing import cast
import urllib.parse
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
import hashlib
import shutil
import time
import random
from flask import Flask, request
import requests
import webbrowser
from components.env import env_class
from werkzeug.serving import make_server


class logo_worker(QtCore.QThread):
	update_percent = QtCore.pyqtSignal(str,int)
	done_signal = QtCore.pyqtSignal(dict,Recipe)

	def __init__(self, changed_textures, createacharacter_path, delete_old_repos, github_handle, recipe, parent = None):
		super().__init__(parent)
		self.changed_textures = changed_textures
		self.createacharacter_path = createacharacter_path
		self.delete_old_repos = delete_old_repos
		self.github_handle = github_handle
		self.recipe = recipe

		self.cwd = os.getcwd().replace("\\","/")
		self.psg_handler = logoconverter()


	def run(self):
		self.texture_convert()

	def texture_convert(self):
		if os.path.exists(f"{self.cwd}/output_textures") == False:
			os.mkdir(f"{self.cwd}/output_textures")

		final_texture_filenames = {}

		self.update_percent.emit("starting converting textures", 40)

		for asset_name in self.changed_textures.keys():
			out_filename = random.randint(0,9999999999)

			self.update_percent.emit(f"converting {asset_name} diffuse to a png", 40)

			final_texture_filenames[asset_name] = (self.changed_textures[asset_name], out_filename)

			self.psg_handler.psg_to_png(f"{self.createacharacter_path}/{self.changed_textures[asset_name]}", f"{self.cwd}/output_textures", out_filename, 512)
			os.remove(f"{self.cwd}/assets/{self.changed_textures[asset_name][:-4]}.dds")

		if os.path.exists(f"{self.cwd}/output_psgs") == False:
			os.mkdir(f"{self.cwd}/output_psgs")

		for asset_name in final_texture_filenames.keys():

			self.update_percent.emit(f"converting {asset_name} diffuse to a psg", 50)
			self.psg_handler.convert(f"{self.cwd}/output_textures", final_texture_filenames[asset_name][1], f"{self.cwd}/output_psgs") # add opacity option when reconverting
		
		shutil.rmtree(f"{self.cwd}/output_textures")

		self.git_hub_setup(final_texture_filenames)



	def git_hub_setup(self, final_texture_filenames):

		if self.delete_old_repos == True:
			repo_list = self.github_handle.list_repos()
			self.update_percent.emit(f"removing old repos", 60)
			for repos in repo_list:
				if "Skate_3_textures" in repos:

					self.github_handle.delete_repo(repos)

		repo = random.randint(0,9999999999)
		self.update_percent.emit(f"making {repo}-Skate_3_textures", 70)
		self.github_handle.create_repo(f"{repo}-Skate_3_textures")

		link_list = {}

		for psg_name in os.listdir(f"{self.cwd}/output_psgs"):
			with open(f"{self.cwd}/output_psgs/{psg_name}","rb") as file:
				filebytes = file.read()

			self.update_percent.emit(f"uploading {psg_name}", 70)
			download_url = self.github_handle.upload_file(f"{repo}-Skate_3_textures", psg_name, filebytes)
			if download_url != None:
				for asset_name in final_texture_filenames.keys():
					if f"{final_texture_filenames[asset_name][1]}.psg" == psg_name:
						link_list[asset_name] = download_url
		
		shutil.rmtree(f"{self.cwd}/output_psgs")

		self.done_signal.emit(link_list, self.recipe)

class OAuthServerThread(QtCore.QThread):
	token_received = QtCore.pyqtSignal(str)

	def __init__(self, parent=None):
		super().__init__(parent)
		self._token = None

	def run(self):
		app = Flask(__name__)
		REDIRECT_URI = "http://localhost:8000/callback"
		self._token = None
		self._should_stop = False

		@app.route("/callback")
		def callback():
			code = request.args.get("code")
			if not code:
				return "Missing code", 400

			# Exchange code for token
			token_url = "https://github.com/login/oauth/access_token"
			headers = {'Accept': 'application/json'}
			data = {
				"client_id": "Ov23liIjsHpUC27r5Xe2",
				"client_secret": env_class().github_secret,
				"code": code,
				"redirect_uri": REDIRECT_URI,
			}

			print("Exchanging code for token...")
			r = requests.post(token_url, headers=headers, data=data)
			token = r.json().get("access_token")

			print(token)
			self.token_received.emit(token)

			return "You may close this window."

		@app.route("/kill_server")
		def kill_server():
			self._should_stop = True
			return "Server is shutting down..."

		self.server = make_server("127.0.0.1", 8000, app)
		self.server.timeout = 1  # seconds

		while not self._should_stop:
			self.server.handle_request()
		print("OAuthServerThread finished")


class mainUi(QtWidgets.QWidget, Ui_Form):
	def setupUi(self,Form):
		super().setupUi(Form)
		
		self.cwd = os.getcwd().replace("\\","/")
		self.backup_on = False
		self.db_handle = database()
		title_bar_handler(Form, self.titlebar_cont, self.close_but, self.mini_but)

		self.worker_threads:list[QtCore.QThread] = []
		self.overlay = cast(QtWidgets.QFrame, self.overlay)
		self.overlay.setGeometry(QtCore.QRect(-20, 10000, 851, 511))

		self.delete_old_repos = True
		self.DeleteRepos = cast(QtWidgets.QCheckBox, self.DeleteRepos)
		self.DeleteRepos.setChecked(self.delete_old_repos)

		if os.path.exists("github_token.txt"):
				with open("github_token.txt", "r") as file:
					token = file.read().strip()
					
					user, login_valid = GithubHandler().check_github_login(token)

					if login_valid == True:
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
		self.shuffle_arena.clicked.connect(self.shuffle_recipe)
		
	def delete_repos(self):
		self.delete_old_repos = self.DeleteRepos.isChecked()

	def github_clicked(self):
		self.github_login_worker = OAuthServerThread()
		self.github_login_worker.token_received.connect(self.github_return)
		self.github_login_worker.start()

		params = {
            "client_id": "Ov23liIjsHpUC27r5Xe2",
            "redirect_uri": "http://localhost:8000/callback",
            "scope": 'repo,delete_repo',
        }
		url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
		webbrowser.open(url)

	def github_return(self,token):

		if token != None:
			with open("github_token.txt", "w+") as file:
				file.write(token)

			self.github_handle = GithubHandler(token)

			self.github_handle.username, login_status = self.github_handle.check_github_login(token)
			self.github_status(login_status)

		a = requests.get("http://localhost:8000/kill_server")
		print(a.text)

		self.github_login_worker.wait()

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
			self.shuffle_arena.setEnabled(True)

			self.backup_button.setEnabled(self.backup_on)

		except:
			self.popup("failed to attach to rpcs3")
	
	def get_skate3_path(self):
		PID = self.rpcs3_process.process.process_id
		proc = psutil.Process(PID)
		exe_path = proc.exe()
		window_title = None

		for window in gw.getAllWindows():
			try:
				title = window.title
				if ("FPS" in title and "Skate 3" in title) and ("BLUS" in title or "BLES" in title):
					window_title = title
					
			except Exception as e:
				print(e)
		
		if window_title == None:
			self.popup("failed to get skate 3 version handle")
			self.clickme.setEnabled(False)
			self.shuffle_arena.setEnabled(False)

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

		if os.path.exists(folder) == False:
			self.popup("no backup folder found")
			return
		
		if len(os.listdir(folder)) == 0:
			self.popup("no backup file exists")

		files = sorted(os.listdir(folder), key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)

		with open(f"{folder}/{files[0]}","rb") as file:
			backup_recipe_bytes = file.read()
		
		self.rpcs3_process.write_recipe(backup_recipe_bytes)

		self.popup("backup Loaded")


	def progress_update(self, message, percentage):
		self.progress_message = cast(QtWidgets.QLabel, self.progress_message)
		self.progress_message.setText(message)

		self.progress_bar = cast(QtWidgets.QProgressBar, self.progress_bar)
		self.progress_bar.setValue(percentage)
		
	def progress_cancel(self):
		self.overlay.setGeometry(QtCore.QRect(-20, 10000, 851, 511))
		self.progress_bar.setValue(0)


	def recipe_clicked(self):
		try:
			self.overlay.setGeometry(QtCore.QRect(-20, 0, 851, 511)) # putting the overlay on

			self.progress_update("reading recipe", 10)

			# reading and converting textures
			recipe_bytes = self.rpcs3_process.read_recipe()

			recipe = Recipe(recipe_bytes=recipe_bytes, recipe_type=RecipeTypes.CREATEACHARACTER)

			for graphics_block in recipe.graphic_blocks:
				graphics_block
				if "http://127.0.0.1" in graphics_block.URL:
					self.popup("this recipe already has custom graphics")
					self.progress_cancel()
					return

			if os.path.exists(f"{self.cwd}/backup_recipes") == False:
				os.mkdir(f"{self.cwd}/backup_recipes")

			
			with open(f"{self.cwd}/backup_recipes/{int(time.time())}.recipe","wb") as file:
				recipe_bytes = recipe.get_bytes()
				padded_result = recipe_bytes.ljust(6500, b'\x00')
				file.write(padded_result)
				self.backup_button.setEnabled(True)

			self.progress_update("reading diffuse texture list", 20)

			Texture_list = {}

			for asset in recipe.asset_lists:
				for texture in asset.assets[0].Models[0].Textures:
					if texture.texture_channel == "diffuse":
						Texture_list[asset.asset_folder_name] = Helpers.file_name_bytes_to_string(texture.texture_name)

			
			self.progress_update("getting rpcs3 and game path", 35)

			exe_path, region = self.get_skate3_path()

			root_path = "/".join(exe_path.split("\\")[:-1])

			with open(f"{root_path}/config/games.yml") as file:
				games_data = file.read()
				file.close()

			games_data = games_data.split("\n")

			for i in games_data:
				if (f"{region.lower()}00760" in i.lower()) or (f"{region.lower()}30464" in i.lower()):
					game_path = i.split(": ")[1].replace("//","/")

			try:
				if game_path != None:

					createacharacter_path = f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter/texture"

					print(createacharacter_path)
					print(f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter/texture")
					print(os.path.exists(f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter/texture") == False)
					print(f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter.big")
					print(os.path.exists(f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter.big") == True)

					if os.path.exists(f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter/texture") == False:
						self.popup("you don't have your createacharacter.big\nfile extracted.")
						self.progress_cancel()
						return


					if os.path.exists(f"{game_path}PS3_GAME/USRDIR/data/content/createacharacter.big") == True:
						self.popup("you don't have your createacharacter.big\nfile extracted.")
						self.progress_cancel()
						return

					changed_textures = {}
					for asset_name in Texture_list.keys():
						texture = Texture_list[asset_name]
						
						if os.path.exists(f"{createacharacter_path}/{texture}"):
							with open(f"{createacharacter_path}/{texture}", "rb") as file:
								psg_bytes = file.read()


							current_hash = hashlib.md5(psg_bytes).hexdigest()
							file_hash = self.db_handle.get_file_hash(texture)

							if file_hash != current_hash:
								changed_textures[asset_name] = texture
						
						else:
							print("most likley dlc skipping item")
					
					if len(changed_textures.keys()) > 5:
						self.popup("too many textures max is 5", ok_callback=self.toomany_logos_pop_callback, callback_args=(changed_textures,createacharacter_path, recipe))

					else:
						self.worker_start(changed_textures,createacharacter_path,recipe)






				else:
					return None
			except Exception as e:
				raise e
				print(e)

		except Exception as e:
			self.popup(f"failed\n{e}")
			self.progress_cancel()

	def shuffle_recipe(self):
		recipe_bytes = self.rpcs3_process.read_recipe()
		
		recipe = Recipe(recipe_bytes=recipe_bytes, recipe_type=RecipeTypes.CREATEACHARACTER)

		github_graphics = False

		for graphics_block in recipe.graphic_blocks:
				graphics_block
				if "http://127.0.0.1" in graphics_block.URL:
					
					github_graphics = True


		if github_graphics == False:
			return
		
		current_asset_list = []

		for graphic_block in recipe.graphic_blocks:
			if "http://127.0.0.1" in graphics_block.URL:

				for asset_list in recipe.asset_lists:
					asset_list = cast(AssetList, asset_list)

					if asset_list.asset_folder_name == "Misc":
						misc = asset_list
						for decal in misc.assets[0].Models:
							if decal.MaterialID == graphic_block.MaterialID:
								graphic_decal = decal
								
		
		for asset_list in recipe.asset_lists:
			if asset_list.asset_folder_name != "Misc":
				asset_list = cast(AssetList, asset_list)
				for texture in asset_list.assets[0].Models[0].Textures:
					texture = cast(Texture, texture)

					if texture.texture_channel == "diffuse":
						
						if texture.texture_name == graphic_decal.Textures[0].texture_name:
							random_arena = Helpers.random_high_res_arena()
							texture.texture_name = random_arena
							graphic_decal.Textures[0].texture_name = random_arena


		self.rpcs3_process.write_recipe(recipe.get_bytes())

	def toomany_logos_pop_callback(self,args:tuple=()):
		self.toomanylogos_ui = too_many_textures()
		self.toomanylogos_ui.setupUi(self.toomanylogos_ui,args)
		self.toomanylogos_ui.setWindowModality(QtCore.Qt.ApplicationModal)
		self.toomanylogos_ui.texture_list_smaller.connect(self.worker_start)
		self.toomanylogos_ui.texture_list_smaller.connect(lambda:self.toomanylogos_ui.close())
		self.toomanylogos_ui.show()

	def worker_start(self,changed_textures,createacharacter_path, recipe):
		for worker in self.worker_threads:
			worker.terminate()

		self.worker = logo_worker(
			changed_textures=changed_textures,
			createacharacter_path=createacharacter_path,
			delete_old_repos=self.delete_old_repos,
			github_handle=self.github_handle,
			recipe=recipe
			)
		
		self.worker.done_signal.connect(self.logo_worker_done)
		self.worker.update_percent.connect(self.progress_update)
		self.worker.start()

	def logo_worker_done(self,link_list, recipe):
		self.progress_update(f"writing the final recipe", 90)
		recipe = self.final_recipe_write(recipe, link_list)

		self.progress_update(f"final check", 100)

		self.overlay.setGeometry(QtCore.QRect(-20, 10000, 851, 511))
		self.rpcs3_process.write_recipe(recipe.get_bytes())
		self.popup("recipe done and injected")
			
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


	def popup(self, message, ok_callback = lambda:None, titlebar_title = "Popup", callback_args:tuple=()):
		self.popup_ui = popup_ui()
		self.popup_ui.setupUi(self.popup_ui, message, titlebar_title, callback_args=callback_args)
		self.popup_ui.setWindowModality(QtCore.Qt.ApplicationModal)
		self.popup_ui.ok_signal.connect(ok_callback)
		self.popup_ui.ok_signal.connect(self.popup_ui.close)
		self.popup_ui.show()

class popup_ui(QtWidgets.QWidget, popup_form):
	ok_signal = QtCore.pyqtSignal(tuple)

	def setupUi(self, Form, message, titlebar_title, callback_args:tuple = ()):
		super().setupUi(Form)
		title_bar_handler(Form, self.titlebar_cont, self.close_but, self.mini_but)
		self.popup_title.setText(titlebar_title)
		self.message.setText(message)
		
		self.callback_args = callback_args

		self.events()

	def events(self):
		self.ok_button.clicked.connect(lambda: self.ok_signal.emit(self.callback_args))
		self.ok_button.clicked.connect(lambda: self.close())
		self.close_but.clicked.connect(lambda: self.ok_signal.emit(self.callback_args))


class too_many_textures(QtWidgets.QWidget, toManyTex_form):
	texture_list_smaller = QtCore.pyqtSignal(dict,str,Recipe)
	def setupUi(self, Form, args):
		super().setupUi(Form)
		title_bar_handler(Form, self.titlebar_cont, self.close_but, self.mini_but)

		self.texture_list = args[0]
		self.create_a_character_path = args[1]
		self.recipe = args[2]
		self.texture_handle(self.texture_list)
		

		self.events()
	
	def events(self):
		self.done_button.clicked.connect(self.done_send)

	def texture_handle(self,texture_list):

		for index, asset_name in enumerate(texture_list.keys()):
			self.add_item(asset_name, texture_list[asset_name], index)

		length = len(texture_list.keys())

		self.texture_count.setText(f"{length}/5")
		
		self.main.setGeometry(QtCore.QRect(10, 20, 491,  (60 + (length*71))+30 ))
		self.bg_main.setGeometry(QtCore.QRect(0, 0, 491, (60 + (length*71))+30 ))
			
	def add_item(self, asset_name, psg_name, index):

		setattr(self, f"checkbox_cont_{asset_name}", QtWidgets.QFrame(self.main))
		checkbox_cont:QtWidgets.QFrame = getattr(self, f"checkbox_cont_{asset_name}")
		checkbox_cont.setGeometry(QtCore.QRect(0, (60 + (index*71)), 491, 71))
		checkbox_cont.setStyleSheet("")
		checkbox_cont.setFrameShape(QtWidgets.QFrame.StyledPanel)
		checkbox_cont.setFrameShadow(QtWidgets.QFrame.Raised)
		checkbox_cont.setObjectName(f"checkbox_cont_{asset_name}")


		setattr(self, f"asset_name_{asset_name}", QtWidgets.QCheckBox(checkbox_cont))
		asset_name_checkbox:QtWidgets.QCheckBox = getattr(self, f"asset_name_{asset_name}")

		asset_name_checkbox.setGeometry(QtCore.QRect(10, 6, 461, 61))
		asset_name_checkbox.setStyleSheet("QCheckBox {\n"
		"    spacing: 8px;\n"
		"    color: white;\n"
		"    font-size: 13px;\n"
		"}\n"
		"\n"
		"QCheckBox::indicator {\n"
		"    width: 36px;\n"
		"    height: 36px;\n"
		"    border: 1px solid #aaa;\n"
		"    border-radius: 3px;\n"
		"    background: #fff;\n"
		"}\n"
		"\n"
		"QCheckBox::indicator:hover {\n"
		"    border: 1px solid #666;\n"
		"}\n"
		"\n"
		"QCheckBox::indicator:checked {\n"
		"    background-color: rgb(0, 255, 42);\n"
		"    border: 1px solid #0078d7;\n"
		"}\n"
		"\n"
		"QCheckBox::indicator:checked:hover {\n"
		"    background-color: #0063b1;\n"
		"    border: 1px solid #0063b1;\n"
		"}\n"
		"\n"
		"QCheckBox::indicator:disabled {\n"
		"    background: #ddd;\n"
		"    border: 1px solid #ccc;\n"
		"}\n"
		"")
		asset_name_checkbox.setObjectName(f"asset_name_{asset_name}")
		asset_name_checkbox.setText(f"{asset_name}: {psg_name}")
		asset_name_checkbox.setChecked(True)
		asset_name_checkbox.clicked.connect(self.checkbox_ticked)


		setattr(self, f"shadow{asset_name}", QtWidgets.QLabel(checkbox_cont))
		shadow:QtWidgets.QFrame = getattr(self, f"shadow{asset_name}")
		shadow.setEnabled(True)
		shadow.setGeometry(QtCore.QRect(0, 40, 491, 31))
		shadow.setStyleSheet("background-color: qlineargradient(spread:pad, x1:1, y1:1, x2:1, y2:0, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(255, 255, 255, 0));")
		shadow.setText("")
		shadow.setObjectName(f"shadow{asset_name}")


		shadow.raise_()
		asset_name_checkbox.raise_()

	def checkbox_ticked(self):
		sender:QtWidgets.QCheckBox = self.sender()
		self.texture_count = cast(QtWidgets.QLabel, self.texture_count)
		amount = int(self.texture_count.text().split("/")[0])

		if sender.isChecked() == True:
			self.texture_count.setText(f"{amount+1}/5")
			if (amount+1) > 5:
				self.texture_count.setStyleSheet("""color:red;""")
				self.done_button.setEnabled(False)
			
		
		elif sender.isChecked() == False:
			self.texture_count.setText(f"{amount-1}/5")
			if (amount-1) <= 5:
				self.texture_count.setStyleSheet("""color:green;""")
				self.done_button = cast(QtWidgets.QPushButton, self.done_button)
				self.done_button.setEnabled(True)
	
	def done_send(self):
		final_list = {}

		for asset_name in self.texture_list.keys():
			asset_name_checkbox:QtWidgets.QCheckBox = getattr(self, f"asset_name_{asset_name}")

			if asset_name_checkbox.isChecked() == True:
				final_list[asset_name] = self.texture_list[asset_name]


		self.texture_list_smaller.emit(final_list, self.create_a_character_path, self.recipe)


if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	Form = QtWidgets.QWidget()
	ui = mainUi()
	ui.setupUi(Form)
	Form.show()
	sys.exit(app.exec_())
