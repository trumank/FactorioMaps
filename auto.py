import os, sys
import subprocess, signal
import json
import threading, psutil
import time
import re
import random
import math
from subprocess import call
import datetime
import urllib.request, urllib.error, urllib.parse
from shutil import copy, rmtree, get_terminal_size as tsize
from zipfile import ZipFile
import tempfile
from PIL import Image, ImageChops

from crop import crop
from ref import ref
from zoom import zoom



def auto(*args):


	def printErase(arg):
		try:
			tsiz = tsize()[0]
			print("\r{}{}\n".format(arg, " " * (tsiz*math.ceil(len(arg)/tsiz)-len(arg) - 1)), end="", flush=True)
		except e:
			raise e
			try:
				print("PRINTERROR %s" % arg)
			except:
				pass




	def parseArg(arg):
		if arg[0:2] != "--":
			return True
		kwargs[arg[2:].split("=",2)[0].lower()] = arg[2:].split("=",2)[1].lower() if len(arg[2:].split("=",2)) > 1 else True
		return False

	kwargs = {}
	args = list(filter(parseArg, args))
	if len(args) > 0:
		foldername = args[0]
	else:
		foldername = os.path.splitext(os.path.basename(max([os.path.join("../../saves", basename) for basename in os.listdir("../../saves") if basename not in { "_autosave1.zip", "_autosave2.zip", "_autosave3.zip" }], key=os.path.getmtime)))[0]
		print("No save name passed. Using most recent save: %s" % foldername)
	savenames = args[1:] or [ foldername ]

	possiblePaths = [
		"C:/Program Files/Factorio/bin/x64/factorio.exe",
		"D:/Program Files/Factorio/bin/x64/factorio.exe",
		"E:/Program Files/Factorio/bin/x64/factorio.exe",
		"F:/Program Files/Factorio/bin/x64/factorio.exe",
		"C:/Games/Factorio/bin/x64/factorio.exe",
		"D:/Games/Factorio/bin/x64/factorio.exe",
		"E:/Games/Factorio/bin/x64/factorio.exe",
		"F:/Games/Factorio/bin/x64/factorio.exe",
		"C:/Program Files (x86)/Steam/steamapps/common/Factorio/bin/x64/factorio.exe",
		"D:/Program Files (x86)/Steam/steamapps/common/Factorio/bin/x64/factorio.exe",
		"E:/Program Files (x86)/Steam/steamapps/common/Factorio/bin/x64/factorio.exe",
		"F:/Program Files (x86)/Steam/steamapps/common/Factorio/bin/x64/factorio.exe",
		"../../bin/x64/factorio"
	]
	try:
		factorioPath = next(x for x in map(os.path.abspath, [kwargs["factorio"]] if "factorio" in kwargs else possiblePaths) if os.path.isfile(x))
	except StopIteration:
		raise Exception("Can't find factorio.exe. Please pass --factorio=PATH as an argument.")

	print("factorio path: {}".format(factorioPath))

	psutil.Process(os.getpid()).nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS if os.name == 'nt' else 5)

	basepath = os.path.join("../../script-output", kwargs["basepath"] if "basepath" in kwargs else "FactorioMaps")
	workthread = None

	workfolder = os.path.join(basepath, foldername)
	print("output folder: {}".format(os.path.relpath(workfolder, "../..")))




	if "noupdate" not in kwargs:
		try:
			print("checking for updates")
			latestUpdates = json.loads(urllib.request.urlopen('https://cdn.jsdelivr.net/gh/L0laapk3/FactorioMaps@latest/updates.json', timeout=10).read())
			with open("updates.json", "r") as f:
				currentUpdates = json.load(f)
			if "reverseupdatetest" in kwargs:
				latestUpdates, currentUpdates = currentUpdates, latestUpdates

			updates = []
			majorUpdate = False
			currentVersion = (0, 0, 0)
			for verStr, changes in currentUpdates.items():
				ver = tuple(map(int, verStr.split(".")))
				if currentVersion[0] < ver[0] or (currentVersion[0] == ver[0] and currentVersion[1] < ver[1]):
					currentVersion = ver
			for verStr, changes in latestUpdates.items():
				if verStr not in currentUpdates:
					ver = tuple(map(int, verStr.split(".")))
					updates.append((verStr, changes))
			updates.sort(key = lambda u: u[0])
			if len(updates) > 0:

				padding = max(map(lambda u: len(u[0]), updates))
				changelogLines = []
				for update in updates:
					if isinstance(update[1], str):
						updateText = update[1]
					else: 
						updateText = str(("\r\n      " + " "*padding).join(update[1]))
					if updateText[0] == "!":
						majorUpdate = True
						updateText = updateText[1:]
					changelogLines.append("    %s: %s" % (update[0].rjust(padding), updateText))
				print("")
				print("")
				print("================================================================================")
				print("")
				print(("  an " + ("important" if majorUpdate else "incremental") + " update has been found!"))
				print("")
				print("  heres what changed:")
				for line in changelogLines:
					print(line)
				print("")
				print("")
				print("  Download: https://mods.factorio.com/mod/L0laapk3_FactorioMaps")
				print("            OR")
				print("            https://github.com/L0laapk3/FactorioMaps")
				if majorUpdate:
					print("")
					print("You can dismiss this by using --noupdate (not recommended)")
				print("")
				print("================================================================================")
				print("")
				print("")
				if majorUpdate or "reverseupdatetest" in kwargs:
					sys.exit(1)(1)


		except urllib.error.URLError as e:
			print("Failed to check for updates. %s: %s" % (type(e).__name__, e))


	if os.path.isfile("autorun.lua") or "reverseupdatetest" in kwargs:
		os.remove("autorun.lua")



	#TODO: integrety check, if done files arent there or there are any bmp's left, complain.


	def linkDir(src, dest):
		if os.name == 'nt':
			subprocess.call(("MKLINK", "/J", os.path.abspath(src), os.path.abspath(dest)), shell=True)
		else:
			subprocess.call(("ln", "-s", os.path.abspath(src), os.path.abspath(dest)), shell=True)

	print("enabling FactorioMaps mod")
	modListPath = os.path.join(kwargs["modpath"], "mod-list.json") if "modpath" in kwargs else "../mod-list.json"
	
	if "modpath" in kwargs and not os.path.samefile(kwargs["modpath"], "../../mods"):
		for file in os.listdir(kwargs["modpath"]):
			if re.match(r'^L0laapk3_FactorioMaps_', file, flags=re.IGNORECASE):
				print("Found other factoriomaps mod in custom mod folder, deleting.")
				path = os.path.join(kwargs["modpath"], file)
				if os.path.islink(path):
					os.unlink(path)
				else:
					os.remove(path)

		linkDir(os.path.join(kwargs["modpath"], os.path.basename(os.path.abspath("."))), ".")
	
		
	
	def changeModlist(newState):
		done = False
		with open(modListPath, "r") as f:
			modlist = json.load(f)
		for mod in modlist["mods"]:
			if mod["name"] == "L0laapk3_FactorioMaps":
				mod["enabled"] = newState
				done = True
		if not done:
			modlist["mods"].append({"name": "L0laapk3_FactorioMaps", "enabled": newState})
		with open(modListPath, "w") as f:
			json.dump(modlist, f, indent=2)

	changeModlist(True)


	
	rawTags = {}
	rawTagsUsed = False
	def printGameLog(pipe):
		with os.fdopen(pipe) as reader:
			while True:
				line = reader.readline().rstrip('\n')
				m = re.match(r'^\ *\d+(?:\.\d+)? *Script *@__L0laapk3_FactorioMaps__\/data-final-fixes\.lua:\d+: FactorioMaps_Output_RawTagPaths:([^:]+):(.*)$', line, re.IGNORECASE)
				if m is not None:
					rawTags[m.group(1)] = m.group(2)
					if rawTagsUsed:
						raise Exception("Tags added after they were used.")
				elif "err" in line.lower() or "warn" in line.lower() or "exception" in line.lower() or "fail" in line.lower() or (kwargs.get("verbosegame", False) and len(line) > 0):
					printErase("[GAME] %s" % line)


	logIn, logOut = os.pipe()
	logthread = threading.Thread(target=printGameLog, args=[logIn])
	logthread.daemon = True
	logthread.start()




	datapath = os.path.join(workfolder, "latest.txt")
	allTmpDirs = []

	try:

		for index, savename in () if "dry" in kwargs else enumerate(savenames):



			printErase("cleaning up")
			if os.path.isfile(datapath):
				os.remove(datapath)


			
			if "delete" in kwargs:
				try:
					rmtree(workfolder)
				except (FileNotFoundError, NotADirectoryError):
					pass



			printErase("building autorun.lua")
			if (os.path.isfile(os.path.join(workfolder, "mapInfo.json"))):
				with open(os.path.join(workfolder, "mapInfo.json"), "r") as f:
					mapInfoLua = re.sub(r'"([^"]+)" *:', lambda m: '["'+m.group(1)+'"] = ', f.read().replace("[", "{").replace("]", "}"))
			else:
				mapInfoLua = "{}"
			if (os.path.isfile(os.path.join(workfolder, "chunkCache.json"))):
				with open(os.path.join(workfolder, "chunkCache.json"), "r") as f:
					chunkCache = re.sub(r'"([^"]+)" *:', lambda m: '["'+m.group(1)+'"] = ', f.read().replace("[", "{").replace("]", "}"))
			else:
				chunkCache = "{}"

			with open("autorun.lua", "w") as f:
				f.write(
					f'fm.autorun = {{\n'
					f'HD = {str("hd" in kwargs).lower()},\n'
					f'day = {str("nightonly" not in kwargs).lower()},\n'
					f'night = {str("dayonly" not in kwargs).lower()},\n'
					f'alt_mode = {str("no-altmode" not in kwargs).lower()},\n'
					f'around_tag_range = {float("tag-range") if "tag-range" in kwargs else 5.2},\n'
					f'around_build_range = {float("build-range") if "build-range" in kwargs else 5.2},\n'
					f'around_smaller_range = {float("connect-range") if "connect-range" in kwargs else 1.2},\n'
					f'smaller_types = {{"lamp", "electric-pole", "radar", "straight-rail", "curved-rail", "rail-signal", "rail-chain-signal", "locomotive", "cargo-wagon", "fluid-wagon", "car"}},\n'
					f'date = "{(datetime.date.strptime(kwargs["date"], "%d/%m/%y") if "date" in kwargs else datetime.date.today()).strftime("%d/%m/%y")}",\n'
					f'name = "{foldername + "/"}",\n'
					f'mapInfo = {mapInfoLua},\n'
					f'chunkCache = {chunkCache}\n'
					f'}}'
				)


			printErase("starting factorio")
			tmpdir = os.path.join(tempfile.gettempdir(), "FactorioMaps-%s" % random.randint(1, 999999999))
			allTmpDirs.append(tmpdir)
			try:
				rmtree(tmpdir)
			except (FileNotFoundError, NotADirectoryError):
				pass
			os.makedirs(os.path.join(tmpdir, "config"))
			configPath = os.path.join(tmpdir, "config/config.ini")
			configInserted = False
			with open(configPath, 'w+') as outf, open("../../config/config.ini", "r") as inf:
				for line in inf:
					if re.match(r'^ *write-data *=.*', line, re.IGNORECASE) is None:
						outf.write(line)
					if not configInserted and re.match(r'^ *\[path\].*', line, re.IGNORECASE) is not None:
						outf.write("write-data=%s\n" % tmpdir)
						configInserted = True
				if not configInserted:
					outf.write("[path]\n")
					outf.write("write-data=%s\n" % tmpdir)

			linkDir(os.path.join(tmpdir, "script-output"), "../../script-output")
			copy("../../player-data.json", os.path.join(tmpdir, "player-data.json"))

			
			p = subprocess.Popen((factorioPath, '--load-game', os.path.abspath(os.path.join("../../saves", savename+".zip")), '--disable-audio', '--config', configPath, "--mod-directory", os.path.abspath(kwargs["modpath"] if "modpath" in kwargs else "../../mods")), stdout=logOut)
			time.sleep(1)
			if p.poll() is not None:
				print("WARNING: running in limited support mode trough steam. Consider using standalone factorio instead.\n\tPlease confirm the steam 'start game with arguments' popup.")

			if not os.path.exists(datapath):
				while not os.path.exists(datapath):
					time.sleep(0.4)

			latest = []
			with open(datapath, 'r') as f:
				for line in f:
					latest.append(line.rstrip("\n"))

			
			firstOtherInputs = latest[0].split(" ")
			firstOutFolder = firstOtherInputs.pop(0).replace("/", " ")
			waitfilename = os.path.join(basepath, firstOutFolder, "Images", firstOtherInputs[0], firstOtherInputs[1], "done.txt")

			
			isKilled = [False]
			def waitKill(isKilled):
				while not isKilled[0]:
					if os.path.isfile(waitfilename):
						isKilled[0] = True
						if p.poll() is None:
							p.send_signal(signal.CTRL_C_EVENT)
						else:
							if os.name == 'nt':
								os.system("taskkill /im factorio.exe")
							else:
								os.system("killall factorio")
						printErase("killed factorio")
						break
					else:
						time.sleep(0.4)

			killthread = threading.Thread(target=waitKill, args=(isKilled,))
			killthread.daemon = True
			killthread.start()



			if workthread and workthread.isAlive():
				#print("waiting for workthread")
				workthread.join()





			for jindex, screenshot in enumerate(latest):
				otherInputs = list(map(lambda s: s.replace("|", " "), screenshot.split(" ")))
				outFolder = otherInputs.pop(0).replace("/", " ")
				print("Processing {}/{} ({} of {})".format(outFolder, "/".join(otherInputs), len(latest) * index + jindex + 1, len(latest) * len(savenames)))
				#print("Cropping %s images" % screenshot)
				crop(outFolder, otherInputs[0], otherInputs[1], otherInputs[2], basepath, **kwargs)
				waitlocalfilename = os.path.join(basepath, outFolder, "Images", otherInputs[0], otherInputs[1], otherInputs[2], "done.txt")
				if not os.path.exists(waitlocalfilename):
					#print("waiting for done.txt")
					while not os.path.exists(waitlocalfilename):
						time.sleep(0.4)



				def refZoom():
					#print("Crossreferencing %s images" % screenshot)
					ref(outFolder, otherInputs[0], otherInputs[1], otherInputs[2], basepath, **kwargs)
					#print("downsampling %s images" % screenshot)
					zoom(outFolder, otherInputs[0], otherInputs[1], otherInputs[2], basepath, **kwargs)

				if screenshot != latest[-1]:
					refZoom()
				else:
					if not isKilled[0]:
						isKilled[0] = True
						if p.poll() is None:
							p.send_signal(signal.CTRL_C_EVENT)
						else:
							if os.name == 'nt':
								os.system("taskkill /im factorio.exe")
							else:
								os.system("killall factorio")
						printErase("killed factorio")

					if savename == savenames[-1]:
						refZoom()
					else:
						workthread = threading.Thread(target=refZoom)
						workthread.daemon = True
						workthread.start()


		os.close(logOut)


			

		if os.path.isfile(os.path.join(workfolder, "mapInfo.out.json")):
			print("generating mapInfo.json")
			with open(os.path.join(workfolder, "mapInfo.json"), 'r+') as outf, open(os.path.join(workfolder, "mapInfo.out.json"), "r") as inf:
				data = json.load(outf)
				for mapIndex, mapStuff in json.load(inf)["maps"].items():
					for surfaceName, surfaceStuff in mapStuff["surfaces"].items():
						data["maps"][int(mapIndex)]["surfaces"][surfaceName]["chunks"] = surfaceStuff["chunks"]
				outf.seek(0)
				json.dump(data, outf)
				outf.truncate()
			os.remove(os.path.join(workfolder, "mapInfo.out.json"))



		print("updating labels")
		tags = {}
		with open(os.path.join(workfolder, "mapInfo.json"), 'r+') as mapInfoJson:
			data = json.load(mapInfoJson)
			for mapStuff in data["maps"]:
				for surfaceName, surfaceStuff in mapStuff["surfaces"].items():
					for tag in surfaceStuff["tags"]:
						tags[tag["iconType"] + tag["iconName"][0].upper() + tag["iconName"][1:]] = tag

		rmtree(os.path.join(workfolder, "Images", "labels"), ignore_errors=True)
		
		modVersions = sorted(
				map(lambda m: (m.group(2).lower(), (m.group(3), m.group(4), m.group(5), m.group(6) is None), m.group(1)),
					filter(lambda m: m,
						map(lambda f: re.search(r"^((.*)_(\d)+\.(\d)+\.(\d))+(\.zip)?$", f, flags=re.IGNORECASE),
							os.listdir(os.path.join(basepath, "../../mods"))))),
				key = lambda t: t[1])


		rawTagsUsed = True
		for _, tag in tags.items():
			dest = os.path.join(workfolder, tag["iconPath"])
			os.makedirs(os.path.dirname(dest), exist_ok=True)
			

			rawPath = rawTags[tag["iconType"] + tag["iconName"][0].upper() + tag["iconName"][1:]]


			icons = rawPath.split('|')
			img = None
			for i, path in enumerate(icons):
				m = re.match(r"^__([^\/]+)__[\/\\](.*)$", path)
				if m is None:
					raise Exception("raw path of %s %s: %s not found" % (tag["iconType"], tag["iconName"], path))

				iconColor = m.group(2).split("?")
				icon = iconColor[0]
				if m.group(1) in ("base", "core"):
					src = os.path.join(factorioPath, "../../../data", m.group(1), icon + ".png")
				else:
					mod = next(mod for mod in modVersions if mod[0] == m.group(1).lower())
					if not mod[1][3]: #true if mod is zip
						zipPath = os.path.join(basepath, "../../mods", mod[2] + ".zip")
						with ZipFile(zipPath, 'r') as zipObj:
							if len(icons) == 1:
								zipInfo = zipObj.getinfo(os.path.join(mod[2], icon + ".png").replace('\\', '/'))
								zipInfo.filename = os.path.basename(dest)
								zipObj.extract(zipInfo, os.path.dirname(os.path.realpath(dest)))
								src = None
							else:
								src = zipObj.extract(os.path.join(mod[2], icon + ".png").replace('\\', '/'), os.path.join(tempfile.gettempdir(), "FactorioMaps"))
					else:
						src = os.path.join(basepath, "../../mods", mod[2], icon + ".png")
				
				if len(icons) == 1:
					if src is not None:
						copy(src, dest)
				else:
					newImg = Image.open(src).convert("RGBA")
					if len(iconColor) > 1:
						newImg = ImageChops.multiply(newImg, Image.new("RGBA", img.size, color=tuple(map(lambda s: int(round(float(s))), iconColor[1].split("%")))))
					if i == 0:
						img = newImg
					else:
						img.paste(newImg.convert("RGB"), (0, 0), newImg)
			if len(icons) > 1:
				img.save(dest)







		#TODO: download leaflet shit

		print("generating mapInfo.js")
		with open(os.path.join(workfolder, "mapInfo.js"), 'w') as outf, open(os.path.join(workfolder, "mapInfo.json"), "r") as inf:
			outf.write("window.mapInfo = JSON.parse('")
			outf.write(inf.read())
			outf.write("');")
			
			
		print("creating index.html")
		copy("index.html.template", os.path.join(workfolder, "index.html"))



	except KeyboardInterrupt:
		if p.poll() is None:
			p.send_signal(signal.CTRL_C_EVENT)
		else:
			if os.name == 'nt':
				os.system("taskkill /im factorio.exe")
			else:
				os.system("killall factorio")
		print("killed factorio")
		raise

	finally:
		print("disabling FactorioMaps mod")
		changeModlist(False)



		print("cleaning up")
		open("autorun.lua", 'w').close()
		for tmpDir in allTmpDirs:
			try:
				os.unlink(os.path.join(tmpdir, "script-output"))
				rmtree(tmpDir)
			except (FileNotFoundError, NotADirectoryError):
				pass









if __name__ == '__main__':
	auto(*sys.argv[1:])