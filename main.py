import logging
from platform import release
import requests
import json
import datetime
import os
import re
import shutil
import config
import captions
import validators

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.types import InputFile
from deezloader.deezloader import DeeLogin
from deezloader.exceptions import InvalidLink
from urllib.parse import urlparse
from states import UploadState
from utils import spotify_auth
from utils import check_label

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

download = DeeLogin(arl = config.deezer_arl)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("*🔥 Привет! Я бот для скачивания треков с Deezer\n🤖 Вот что я умею:\n/isrc* - _скачивание трека по ISRC за 9 часов до релиза_\n*/upc* - _скачивание альбома по UPC за 9 часов до релиза_\n*/link* - _скачивание релиза по ссылке за 9 часов до релиза_\n*/spotify* - _скачивание релиза по ссылке из spotify_\n\n*🧑‍💻 Разработчик: @uzkwphq*", parse_mode="markdown")


@dp.message_handler(commands=['upc'], state=None)
async def album_download(message: types.Message):
    await message.reply("Введите UPC:")
    await UploadState.sending_upc.set()

@dp.message_handler(commands=['isrc'], state=None)
async def album_download(message: types.Message):
    await message.reply("Введите ISRC:")
    await UploadState.sending_isrc.set()

@dp.message_handler(commands=['link'], state=None)
async def link_download(message: types.Message):
    await message.reply("*Отправьте ссылку на релиз в Deezer\nПример ссылки:* _https://www.deezer.com/album/284305192_", parse_mode="markdown")
    await UploadState.sending_link.set()

@dp.message_handler(commands=['spotify'], state=None)
async def spotify_download(message: types.Message):
    await message.reply("Отправь ссылку на трек в Spotify")
    await UploadState.sending_spotify_link.set()

@dp.message_handler(state=UploadState.sending_upc)
async def process_upc(message: types.Message, state: FSMContext):
    upc = message.text
    link = f"https://api.deezer.com/album/upc:" + upc
    response = requests.get(link).text
    data = json.loads(response)
    if 'error' in data:
        await message.reply("К сожалению по этому треку нет информации\nUPC: " + upc)
        await state.finish()
    else:
        album_link = data["link"]
        artist = data["artist"]["name"]
        title = data["title"]
        date = data["release_date"]	
        track_link = data["link"]
        cover = data["cover_xl"]
        covermd5 = data["md5_image"]
        nb_tracks = data["nb_tracks"]
        label = data["label"]
        if label == "Firect Music":
            await message.reply("Загрузка релизов лейбла [Firect Music](https://firectmusic.ru) запрещена!", parse_mode="markdown")
            await state.finish()
            return
        if nb_tracks == 1:
            duration = data["duration"]
            explicit_lyrics = data["explicit_lyrics"]
            dur = str(datetime.timedelta(seconds=duration))
            if explicit_lyrics == False:
                exp = "Нет"
            else:
                exp = "Да"
        os.makedirs("tracks", exist_ok=True)
        output_dir = f"tracks/{artist} - {title}"
        md5link = f"http://e-cdn-images.dzcdn.net/images/cover/{covermd5}/1000x1000-000000-80-0-0.jpg"
        if nb_tracks > 1:
            if cover is None:
                await bot.send_photo(message.from_user.id, md5link, f"*{artist} - {title}*\n\n*UPC:* _{upc}_\n*Лейбл:* _{label}_\n*Дата релиза:* _{date}_\n*Количество треков:* _{nb_tracks}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
            else:
                await bot.send_photo(message.from_user.id, cover, f"*{artist} - {title}*\n\n*UPC:* _{upc}_\n*Лейбл:* _{label}_\n*Дата релиза:* _{date}_\n*Количество треков:* _{nb_tracks}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
        elif nb_tracks == 1:
            trackid = data["tracks"]["data"][0]["id"]
            link = f"https://api.deezer.com/track/" + str(trackid)
            response = requests.get(link).text
            data = json.loads(response)
            isrc = data["isrc"]
            if cover is None:
                await bot.send_photo(message.from_user.id, md5link, f"*{artist} - {title}*\n\n*Длительность:* _{dur}_\n*Ненормативная лексика:* _{exp}_\n*Дата релиза:* _{date}_\n*UPC:* _{upc}_\n*ISRC:* _{isrc}_\n*Лейбл:* _{label}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
            else:
                await bot.send_photo(message.from_user.id, cover, f"*{artist} - {title}*\n\n*Длительность:* _{dur}_\n*Ненормативная лексика:* _{exp}_\n*Дата релиза:* _{date}_\n*UPC:* _{upc}_\n*ISRC:* _{isrc}_\n*Лейбл:* _{label}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
        startdownload = await bot.send_message(message.from_user.id, "*Начинаю скачивание!*", parse_mode="markdown")
        download.download_albumdee(f"{album_link}",output_dir=output_dir,quality_download="MP3_128",recursive_quality=False,recursive_download=True,not_interface=False,method_save=0)

        aye = f"tracks/{artist} - {title}"
        xd = os.listdir(aye)
        funnymoment = f"{aye}/{xd[0]}"
        kolvotracks = os.listdir(funnymoment)
        captionid = "captions." + "id" + str(message.chat.id)

        for x in kolvotracks:
            f = open(f"{funnymoment}/{x}","rb")
            try:
                audio_caption = eval(captionid)[0]
                await bot.send_audio(message.from_user.id, f, caption=audio_caption, parse_mode="markdown")
            except:
                await bot.send_audio(message.from_user.id, f, caption='[DeezRobot](t.me/deez_robot)', parse_mode="markdown")
            
        await message.reply("*Готово!*", parse_mode="markdown")
        await startdownload.delete()
        await state.finish()
        shutil.rmtree(aye, ignore_errors=True)
        

@dp.message_handler(state=UploadState.sending_isrc)
async def process_isrc(message: types.Message, state: FSMContext):
    isrc = message.text
    link = f"https://api.deezer.com/track/isrc:" + isrc
    response = requests.get(link).text
    data = json.loads(response)
    if 'error' in data:
        await message.reply("К сожалению по этому треку нет информации")
        await state.finish()
    else:
        track_link = data["link"]
        artist = data["artist"]["name"]
        title = data["title"]
        album = data["album"]["title"]
        date = data["release_date"]	
        track_link = data["link"]
        duration = data["duration"]
        cover = data["album"]["cover_xl"]
        covermd5 = data["album"]["md5_image"]
        explicit_lyrics = data["explicit_lyrics"]
        track_position = data["track_position"]
        albumid = data["album"]["id"]
        md5link = f"http://e-cdn-images.dzcdn.net/images/cover/{covermd5}/1000x1000-000000-80-0-0.jpg"
        dur = str(datetime.timedelta(seconds=duration))
        if explicit_lyrics == False:
            exp = "Нет"
        else:
            exp = "Да"

        link = f"https://api.deezer.com/album/" + str(albumid)
        response = requests.get(link).text
        data = json.loads(response)
        label = data["label"]
        if label == "Firect Music":
            await message.reply("Загрузка релизов лейбла [Firect Music](https://firectmusic.ru) запрещена!", parse_mode="markdown")
            await state.finish()
            return
        os.makedirs("tracks", exist_ok=True)
        output_dir = f"tracks/{artist} - {album}"
        download.download_trackdee(f"{track_link}",output_dir=output_dir,quality_download="MP3_128",recursive_quality=False,recursive_download=True,not_interface=False,method_save=0)

        aye = f"tracks/{artist} - {album}"
        xd = os.listdir(aye)
        funnymoment = f"{aye}/{xd[0]}"
        upc = re.findall(r'\b\d+\b', xd[0])
        
        if cover is None:
            await bot.send_photo(message.chat.id, md5link, f"*{artist} - {title}*\n\n*Альбом:* _{album}_\n*Длительность:* _{dur}_\n*Ненормативная лексика:* _{exp}_\n*Дата релиза:* _{date}_\n*Позиция в альбоме:* _{track_position}_\n*ISRC:* _{isrc}_\n*UPC:* _{upc[0]}_\n*Лейбл:* _{label}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
        else:
            await bot.send_photo(message.chat.id, cover, f"*{artist} - {title}*\n\n*Альбом:* _{album}_\n*Длительность:* _{dur}_\n*Ненормативная лексика:* _{exp}_\n*Дата релиза:* _{date}_\n*Позиция в альбоме:* _{track_position}_\n*ISRC:* _{isrc}_\n*UPC:* _{upc[0]}_\n*Лейбл:* _{label}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
        sendingtrack = await bot.send_message(message.from_user.id, "*Отправляю трек!*", parse_mode="markdown")
        captionid = "captions." + "id" + str(message.chat.id)
        f = open(f"{funnymoment}/{album} CD 1 TRACK {track_position} (128).mp3","rb")
        try:
            audio_caption = eval(captionid)[0]
            await bot.send_audio(message.from_user.id, f, caption=audio_caption, parse_mode="markdown")
        except:
            await bot.send_audio(message.from_user.id, f, caption='[DeezRobot](t.me/deez_robot)', parse_mode="markdown")
        await message.reply("*Готово!*", parse_mode="markdown")
        await sendingtrack.delete()
        await state.finish()
        shutil.rmtree(aye, ignore_errors=True)

@dp.message_handler(state=UploadState.sending_link)
async def process_link(message: types.Message, state: FSMContext):
    link = message.text
    parse_object = urlparse(link)
    albumid = re.findall('\d+', parse_object.path)[0]
    link = f"https://api.deezer.com/album/" + str(albumid)
    response = requests.get(link).text
    data = json.loads(response)
    if 'error' in data:
        await message.reply("К сожалению по этому треку нет информации\nAlbumId: " + str(albumid))
        await state.finish()
    else:
        upc = data["upc"]
        album_link = data["link"]
        artist = data["artist"]["name"]
        title = data["title"]
        date = data["release_date"]	
        track_link = data["link"]
        cover = data["cover_xl"]
        covermd5 = data["md5_image"]
        nb_tracks = data["nb_tracks"]
        label = data["label"]
        if label == "Firect Music":
            await message.reply("Загрузка релизов лейбла [Firect Music](https://firectmusic.ru) запрещена!", parse_mode="markdown")
            await state.finish()
            return
        if nb_tracks == 1:
            duration = data["duration"]
            explicit_lyrics = data["explicit_lyrics"]
            dur = str(datetime.timedelta(seconds=duration))
            if explicit_lyrics == False:
                exp = "Нет"
            else:
                exp = "Да"
        os.makedirs("tracks", exist_ok=True)
        output_dir = f"tracks/{artist} - {title}"
        md5link = f"http://e-cdn-images.dzcdn.net/images/cover/{covermd5}/1000x1000-000000-80-0-0.jpg"
        if nb_tracks > 1:
            if cover is None:
                await bot.send_photo(message.from_user.id, md5link, f"*{artist} - {title}*\n\n*UPC:* _{upc}_\n*Лейбл:* _{label}_\n*Дата релиза:* _{date}_\n*Количество треков:* _{nb_tracks}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
            else:
                await bot.send_photo(message.from_user.id, cover, f"*{artist} - {title}*\n\n*UPC:* _{upc}_\n*Лейбл:* _{label}_\n*Дата релиза:* _{date}_\n*Количество треков:* _{nb_tracks}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
        elif nb_tracks == 1:
            trackid = data["tracks"]["data"][0]["id"]
            link = f"https://api.deezer.com/track/" + str(trackid)
            response = requests.get(link).text
            data = json.loads(response)
            isrc = data["isrc"]
            if cover is None:
                await bot.send_photo(message.from_user.id, md5link, f"*{artist} - {title}*\n\n*Длительность:* _{dur}_\n*Ненормативная лексика:* _{exp}_\n*Дата релиза:* _{date}_\n*UPC:* _{upc}_\n*ISRC:* _{isrc}_\n*Лейбл:* _{label}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
            else:
                await bot.send_photo(message.from_user.id, cover, f"*{artist} - {title}*\n\n*Длительность:* _{dur}_\n*Ненормативная лексика:* _{exp}_\n*Дата релиза:* _{date}_\n*UPC:* _{upc}_\n*ISRC:* _{isrc}_\n*Лейбл:* _{label}_\n\n[Слушать на Deezer]({track_link})", parse_mode="markdown")
        startdownload = await bot.send_message(message.from_user.id, "*Начинаю скачивание!*", parse_mode="markdown")
        download.download_albumdee(f"{album_link}",output_dir=output_dir,quality_download="MP3_128",recursive_quality=False,recursive_download=True,not_interface=False,method_save=0)

        aye = f"tracks/{artist} - {title}"
        xd = os.listdir(aye)
        funnymoment = f"{aye}/{xd[0]}"
        kolvotracks = os.listdir(funnymoment)
        captionid = "captions." + "id" + str(message.chat.id)

        for x in kolvotracks:
            f = open(f"{funnymoment}/{x}","rb")
            try:
                audio_caption = eval(captionid)[0]
                await bot.send_audio(message.from_user.id, f, caption=audio_caption, parse_mode="markdown")
            except:
                await bot.send_audio(message.from_user.id, f, caption='[DeezRobot](t.me/deez_robot)', parse_mode="markdown")

        await message.reply("*Готово!*", parse_mode="markdown")
        await startdownload.delete()
        await state.finish()
        shutil.rmtree(aye, ignore_errors=True)

@dp.message_handler(state=UploadState.sending_spotify_link)
async def process_spotify_link(message: types.Message, state: FSMContext):

    link = message.text
    if not validators.url(link):
        await message.reply("*Вы отправили невалидную ссылку!\nПримеры ссылок:* _https://open.spotify.com/album/5S3Bj5Sd4ubU3OJnqGw9PC?si=ouzDkAhoRsSMgZRIgdiSfw\nhttps://open.spotify.com/album/5S3Bj5Sd4ubU3OJnqGw9PC\nhttps://open.spotify.com/track/3uxpenfPxDNLVqywtBpBA6?si=e75f57271b4c4948\nhttps://open.spotify.com/track/3uxpenfPxDNLVqywtBpBA6_", parse_mode="markdown")
        await state.finish()
        return
    separator = "/"
    parse_object = urlparse(link)
    aboba = parse_object.path
    data = aboba.split(separator)
    os.makedirs("tracks", exist_ok=True)
    if data[1] == "album":
        output_dir = f"tracks/albums"
        req = f"https://api.spotify.com/v1/albums/{data[2]}"
        response = requests.get(req, headers=spotify_auth.headers).text
        albumdata = json.loads(response)
        upc = albumdata["external_ids"]["upc"]
        cover = albumdata["images"][0]["url"]
        release_date = albumdata["release_date"]
        total_tracks = albumdata["total_tracks"]
        copyright = albumdata["copyrights"][0]["text"]
        if "Firect Music" in copyright:
            await message.reply("Загрузка релизов лейбла [Firect Music](https://firectmusic.ru) запрещена!", parse_mode="markdown")
            await state.finish()
            return

        deezer_req = f"https://api.deezer.com/album/upc:" + str(upc)
        response = requests.get(deezer_req).text
        dee_data = json.loads(response)
        dee_album_link = dee_data["link"]
        startdownload = await bot.send_message(message.from_user.id, "*Начинаю скачивание!*", parse_mode="markdown")
        download.download_albumspo(f"https://open.spotify.com/album/{data[2]}", output_dir=output_dir,quality_download="MP3_128",recursive_quality=False,recursive_download=True,not_interface=False,method_save=1)
        releasedir = f"{output_dir}/{os.listdir(output_dir)[0]}" 
        separator = " - "
        separator_title = "/"
        splited = releasedir.split(separator)
        artists = splited[1]
        title_tosplit = splited[0]
        title = title_tosplit.split(separator_title)[2]
        kolvotracks = os.listdir(releasedir)
        captionid = "captions." + "id" + str(message.chat.id)
        await bot.send_photo(message.from_user.id, cover, f"*{artists} - {title}*\n\n*Дата релиза:* _{release_date}_\n*UPC:* _{upc}_\n*Лейбл:* _© {copyright}_\n\n[Слушать в Deezer]({dee_album_link})", parse_mode="markdown")
        for x in kolvotracks:
            f = open(f"{releasedir}/{x}","rb")
            try:
                audio_caption = eval(captionid)[0]
                await bot.send_audio(message.from_user.id, f, caption=audio_caption, parse_mode="markdown")
            except:
                await bot.send_audio(message.from_user.id, f, caption='[DeezRobot](t.me/deez_robot)', parse_mode="markdown")

        await message.reply("*Готово!*", parse_mode="markdown")
        await startdownload.delete()
        await state.finish()
        # shutil.rmtree(releasedir, ignore_errors=True)
        
    elif data[1] == "track":
        req = f"https://api.spotify.com/v1/tracks/{data[2]}"
        response = requests.get(req, headers=spotify_auth.headers).text
        trackdata = json.loads(response)
        album = trackdata["album"]["name"]
        cover = trackdata["album"]["images"][0]["url"]
        release_date = trackdata["album"]["release_date"]
        track_number = trackdata["track_number"]
        isrc = trackdata["external_ids"]["isrc"]
        title = trackdata["name"]
        if check_label.check_label(trackdata["album"]["id"]) == False:
            await message.reply("Загрузка релизов лейбла [Firect Music](https://firectmusic.ru) запрещена!", parse_mode="markdown")
            await state.finish()
            return

        deezer_req = f"https://api.deezer.com/track/isrc:" + str(isrc)
        response = requests.get(deezer_req).text
        dee_data = json.loads(response)
        dee_album_link = dee_data["link"]
        dee_album_id = dee_data["album"]["id"]

        deezer_requpc = f"https://api.deezer.com/album/" + str(dee_album_id)
        response = requests.get(deezer_requpc).text
        dee_datakek = json.loads(response)
        dee_upc = dee_datakek["upc"]
        
        output_dir = f"tracks/singles/{title}"
        disc_number = trackdata["disc_number"]
        startdownload = await bot.send_message(message.from_user.id, "*Начинаю скачивание!*", parse_mode="markdown")
        download.download_trackspo(f"https://open.spotify.com/track/{data[2]}", output_dir=output_dir,quality_download="MP3_128",recursive_quality=False,recursive_download=True,not_interface=False,method_save=1)
        releasedir = f"{output_dir}/{os.listdir(output_dir)[0]}" 
        separator = " - "
        splited = releasedir.split(separator)
        artists = splited[1]
        captionid = "captions." + "id" + str(message.chat.id)
        kolvotracks = os.listdir(releasedir)
        await bot.send_photo(message.from_user.id, cover, f"*{artists} - {title}*\n\n*Альбом:* _{album}_\n*Дата релиза:* _{release_date}_\n*UPC:* _{dee_upc}_\n*ISRC:* _{isrc}_\n*Позиция в альбоме:* _{track_number}_\n\n[Слушать в Deezer]({dee_album_link})", parse_mode="markdown")
        for x in kolvotracks:
            f = open(f"{releasedir}/{x}","rb")
            try:
                audio_caption = eval(captionid)[0]
                await bot.send_audio(message.from_user.id, f, caption=audio_caption, parse_mode="markdown")
            except:
                await bot.send_audio(message.from_user.id, f, caption='[DeezRobot](t.me/deez_robot)', parse_mode="markdown")
                await message.reply("*Готово!*", parse_mode="markdown")
        await startdownload.delete()
        await state.finish()
        shutil.rmtree(releasedir, ignore_errors=True)
        

if __name__ == '__main__':
    executor.start_polling(dp)

