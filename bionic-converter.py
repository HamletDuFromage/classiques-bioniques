import math
import re
import glob
import textwrap
import threading
from os import mkdir
from subprocess import run
from PIL import Image, ImageDraw, ImageFont


wordPattern = re.compile(r"([A-Za-zÀ-ÿ']+)")
titlePattern = re.compile(r"(#.+)")
infoPattern = re.compile(r"(---[\s\S]+?---)")

mainfont = "./fonts/Roboto/Roboto-Regular.ttf"
boldfont = "./fonts/Roboto/Roboto-Bold.ttf"
italicfont = "./fonts/Roboto/Roboto-Italic.ttf"
bolditalicfont = "./fonts/Roboto/Roboto-ItalicBold.ttf"

out_dir = "./out/"
try:
    mkdir(out_dir)
except FileExistsError:
    pass

def bolden(word):
    length = len(word)
    if length == 3:
        n = 1
    else:
        n = math.ceil(length/2)
    return f"**{word[:n]}**{word[n:]}"

def unbolden(word):
    return word.replace("**", "")

def delete(word):
    return ""

def replace(pattern, text, function, replace_all=True):
    newstring = ''
    start = 0
    for match in re.finditer(pattern, text):
        end, newstart = match.span()
        newstring += text[start:end]
        rep = function(match.group(1))
        newstring += rep
        start = newstart
        if not replace_all:
            break
    newstring += text[start:]
    return newstring

def threadedRun(func, n):
    threads = []
    for _ in range(n):
        x = threading.Thread(target=func)
        threads.append(x)
        x.start()

    for thread in threads:
        thread.join()

class EasyRead:
    def __init__(self):
        self.count = 0

    def getInfo(self, text):
        match = re.match(infoPattern, text)
        info = match.group(1)
        res = {}
        for tag in ["identifier", "creator", "date", "title"]:
            value = re.search(f"{tag}: (.*)", info).group(1)
            res[tag] = value.replace(f"{tag}: ", "").strip(" .")
        res["title"] = "\"" + res["title"] + "\""
        return res

    def additionalInfo(self, infos):
        infos["original-filename"] = f"bionic_{infos['identifier']}.md"
        cover_filename = f"bionic_{infos['identifier']}.png"
        author = infos["creator"].split(", ")
        try: 
            infos["author"] = f"{author[1]} {author[0]}"
        except IndexError:
            infos["author"] = infos["creator"]
        infos["cover-image"] = out_dir + cover_filename
        infos["css"] = "epub.css"
        infos["mainfont"] = mainfont
        infos["mainfontoptions"] = f"\n\t- BoldFont={boldfont}\n\t- ItalicFont={italicfont}\n\t- BoldItalicFont={bolditalicfont}"
        return infos

    def createMetadata(self, infos):
        res = ""
        for key, value in infos.items():
            res += key + ": " + value + "\n"
        return "---\n" + res + "---\n"

    def createCover(self, title_str, author_str, collection_str, filename):
        dimensions = (611, 1000)
        img = Image.new('RGB', dimensions, color = (212, 212, 212))
        
        font = ImageFont.truetype(mainfont, 30)
        title = ImageDraw.Draw(img)
        title_wrapped = textwrap.wrap(title_str, 34)
        title.text((1/10*dimensions[0], 2/3*dimensions[1]), '\n'.join(title_wrapped), font=font, fill = (0, 0, 0))
        
        font = ImageFont.truetype(mainfont, 20)
        author = ImageDraw.Draw(img)
        author.text((1/10*dimensions[0], (2/3-1/40)*dimensions[1]), author_str, font=font, fill = (124, 124, 124))
        
        font = ImageFont.truetype(mainfont, 18)
        collection = ImageDraw.Draw(img)
        w = collection.textlength(collection_str, font=font)
        collection.text((19/20*dimensions[0] - w, 9.3/10*dimensions[1]), collection_str, font=font, fill=(100, 100, 100))
        
        img.save(filename)

    def threadedConversion(self):
        while True:
            try:
                fname = self.input_files.pop()
            except IndexError:
                break
            self.count += 1
            print(f"converting {self.count}/{self.files_number} - ({fname})")
            with open(fname, "r") as mkdown:
                text = mkdown.read()
            infos = self.getInfo(text)
            infos = self.additionalInfo(infos)

            out = replace(infoPattern, text, delete, replace_all=False)
            out = replace(wordPattern, out, bolden)
            out = replace(titlePattern, out, unbolden)

            out = self.createMetadata(infos) + out

            self.createCover(infos["title"].strip("\""), infos["author"], "Classiques Bioniques", infos["cover-image"])

            with open(f"{out_dir}/{infos['original-filename']}", "w") as mkdown:
                mkdown.write(out)

    def convertBooks(self):
        self.input_files = glob.glob(r"./oeuvres.github.io/markdown/*.md")
        self.files_number = len(self.input_files)
        threadedRun(self.threadedConversion, 4)

class Epub:
    def __init__(self):
        self.lock = threading.Lock()
        self.count = 0

    def threadedConversion(self):
        while True:
            try:
                fname = self.converted_files.pop()
            except IndexError:
                break
            self.count += 1
            print(f"compiling to epub {self.count}/{self.files_number} - ({fname})")
            run(f"pandoc {fname} -o {fname[:-3]}.epub", shell=True)

    def toEpub(self):
        self.converted_files = glob.glob(r"./out/*.md")
        self.files_number = len(self.converted_files)
        threadedRun(self.threadedConversion, 4)

EasyRead().convertBooks()
Epub().toEpub()

