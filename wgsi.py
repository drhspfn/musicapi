import asyncio, io
import deezer_asy.util as DeezerUtil
import deezer_asy.constants as DeezerConstant
from aiohttp import web
from sys import exit
from pytube import YouTube
from shazamio import Shazam
import lyricsgenius
import pytube.exceptions as YTExceptions
import httpx, re, datetime, json, unidecode
from youtubesearchpython.__future__ import VideosSearch
from soundcloud import Format, Transcoding, User, Track, Media, Badges, Visual, Visuals, Product , CreatorSubscription
from musichelper.MusicHelper import MusicHelper as MHelper

from flask import Flask, jsonify, request, Response

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

app = Flask(__name__)

WEB_H_CONFIG = {}
def parse_config(file_path:str):
    global WEB_H_CONFIG
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            WEB_H_CONFIG = json.load(file)
            return 

    except FileNotFoundError:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump({}, file)

        return exit(1)


"""
music-helper 
pydeezer-asy 
asyncio 
pytube 
unidecode 
youtube-search-python 
cryptography 
aiohttp 
asyncio 
shazamio 
lyricsgenius




music-helper pydeezer-asy asyncio pytube unidecode youtube-search-python cryptography aiohttp asyncio shazamio lyricsgenius
"""

APP_LOOP = asyncio.get_event_loop()


parse_config('./config.json')
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        if isinstance(obj, Track):
            return obj.__dict__
        if isinstance(obj, Media):
            return obj.__dict__
        if isinstance(obj, Transcoding):
            return obj.__dict__
        if isinstance(obj, User):
            return obj.__dict__
        if isinstance(obj, Format):
            return obj.__dict__
        if isinstance(obj, Badges):
            return obj.__dict__
        if isinstance(obj, CreatorSubscription):
            return obj.__dict__
        if isinstance(obj, Product):
            return obj.__dict__
        if isinstance(obj, Visuals):
            return obj.__dict__
        if isinstance(obj, Visual):
            return obj.__dict__
        return super().default(obj)
async def sanitize_string(string_line:str, other_string_line:str=""):
        string_line = unidecode.unidecode_expect_nonascii(string_line) 
        string_line = re.sub(r'[^\w\s.-]', '', string_line)

        if other_string_line:
            string_line = string_line.replace(other_string_line, "")
            other_string_line = unidecode.unidecode_expect_nonascii(other_string_line) 
            other_string_line = re.sub(r'[^\w\s.-]', '', other_string_line)

        string_line = string_line.replace("-", "")

        for part in WEB_H_CONFIG['sanitize_parts']:
            if string_line.lower().find(part) != -1:
                string_line = string_line.replace(part, "")

            if other_string_line:
                if other_string_line.lower().find(part) != -1:
                    other_string_line = other_string_line.replace(part, "")

        

        if other_string_line:
            return (string_line.strip(), other_string_line.strip())

        
        return string_line.strip()  
async def convert_to_json(obj:list):
    res = []
    for x in obj:
        res.append(json.dumps(x, cls=CustomEncoder))
    return res

#$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$
#$$$$$$$$$$$$$$$$$$$$$$$$$


mHelper = MHelper(
    deezer_arl=WEB_H_CONFIG['deezer_api'], 
    ytm_oauth=WEB_H_CONFIG['ytm_oauth'] ,
    sc_data=(
        WEB_H_CONFIG['sc_data']['client_id'], 
        WEB_H_CONFIG['sc_data']['client_secret']), 
    loop=APP_LOOP)
shazamAPI = Shazam()
geniusAPI = lyricsgenius.Genius(WEB_H_CONFIG['genius_api']) 
#################################################################################
#################################################################################
#################################################################################
#################################################################################
#################################################################################
#################################################################################
#################################################################################
@app.route("/deezer/stream", methods = ['GET'])
async def stream_deezer():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    audio_id = request.args.get('id', None)
    if api_key is not None:
        if audio_id and api_key == WEB_H_CONFIG['api_key']:
            _track = await mHelper.deezer.get_track(audio_id, False)
            if _track:
                url, _ = await mHelper.deezer.get_track_download_url(_track['info'])
                blowfish_key = DeezerUtil.get_blowfish_key(_track['info']['DATA']["SNG_ID"])
                title = _track['tags']['title']

                chunk_size = 2 * 1024
                async with httpx.AsyncClient(headers=DeezerConstant.networking_settings.HTTP_HEADERS, cookies=await mHelper.deezer.get_cookies()) as client:
                    res = await client.get(url, follow_redirects=True)
                    total_filesize = int(res.headers.get('Content-Length', 0))
                    start = 0
                    end = total_filesize - 1
                    status_code = 200
                    range_header = request.headers.get('Range')

                    if range_header:
                        range_match = re.search(r'(\d+)-(\d*)', range_header)
                        if range_match:
                            start = int(range_match.group(1))
                            end = int(range_match.group(2)) if range_match.group(2) else total_filesize - 1
                            status_code = 206
                    def generate():
                        i = 0
                        data_iter = res.iter_bytes(chunk_size)
                        for chunk in data_iter:
                            if i % 3 > 0:
                                yield chunk
                            elif len(chunk) < chunk_size:
                                yield chunk
                                break
                            else:
                                cipher = Cipher(algorithms.Blowfish(blowfish_key),
                                            modes.CBC(
                                                bytes([i for i in range(8)])),
                                            default_backend())

                                decryptor = cipher.decryptor()
                                dec_data = decryptor.update(
                                    chunk) + decryptor.finalize()
                                
                                yield dec_data
                            i += 1


                    headers = {
                        'Accept-Ranges': 'bytes',
                        'Content-Type': 'audio/mpeg',
                        'Content-Length': total_filesize,
                        'Content-Range': f'bytes {start}-{end}/{total_filesize}',
                        'Content-Disposition': f'inline; filename="{title}.mp3"'
                    }
                    return Response(generate(), headers=headers, status=status_code)
                    
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status
@app.route("/deezer/search", methods = ['GET'])
async def search_deezer():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    search_qu = request.args.get('qu', None)
    search_limit = request.args.get('limit', 5)
    if api_key is not None:
        if search_qu and api_key == WEB_H_CONFIG['api_key']:
            try:
                response_data['data'] = await mHelper.deezer.search_tracks(search_qu, search_limit)
                response_data['status'] = True
                response_data['message'] = ""
                response_status = 200
            except Exception as excp:
                response_data['message'] = str(excp)
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
@app.route("/sc/stream", methods = ['GET'])
async def stream_sc():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    audio_id = request.args.get('id', None)
    if api_key is not None:
        if audio_id and api_key == WEB_H_CONFIG['api_key']:
            track_url = await mHelper.soundcloud.get_track_url(audio_id)
            
            total_filesize = 0
            async with httpx.AsyncClient() as client:
                response = await client.head(track_url)

                if response.status_code != 200:
                    return web.Response(status=response.status_code)

                total_filesize = int(response.headers.get('Content-Length', 0))


            start = 0
            end = total_filesize - 1
            status_code = 200
            range_header = request.headers.get('Range')
            if range_header and 1 == 0:
                range_match = re.search(r'(\d+)-(\d*)', range_header)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2)) if range_match.group(2) else total_filesize - 1
                    status_code = 206
                    
            cmd = ["ffmpeg", "-ss", str(start), "-i", track_url, "-t", str(end - start + 1), "-acodec", "libmp3lame", "-f", "mp3", "-"]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            mp3_data, _ = await proc.communicate()

            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Type': 'audio/mp3',
                'Content-Length': len(mp3_data),
                'Content-Range': f'bytes {start}-{end}/{total_filesize}'
            }
            return Response(mp3_data, content_type='audio/mp3', headers=headers, status=status_code)
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status
@app.route("/yt/search", methods = ['GET'])
async def search_sc():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    search_qu = request.args.get('qu', None)
    search_limit = request.args.get('limit', 5)
    if api_key is not None:
        if search_qu and api_key == WEB_H_CONFIG['api_key']:
            try:
                data = await mHelper.soundcloud.search(search_qu, filter='track', limit=int(search_limit))
                response_data['data'] = await convert_to_json(list(data))
                response_data['status'] = True
                response_data['message'] = ""
                response_status = 200
            except Exception as excp:
                response_data['message'] = str(excp)

    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
async def generate_yt_answer(qu:str, limit:int, ytm:bool):
    try:
        if ytm:
            data = await mHelper.ytm.search(qu, 'songs', limit=limit)
            if data:
                return data
            else:
                return await generate_yt_answer(qu, limit, not ytm)

        else:
            search_result = VideosSearch(qu, limit = limit + 2)
            search_result = await search_result.next()
            if search_result.get('result', []):
                answer = []
                for item in search_result['result']:
                    time_parts = item.get('duration', "1:10").split(':')

                    if len(time_parts) == 2: 
                        minutes, seconds = map(int, time_parts)
                        total_seconds = (minutes * 60) + seconds
                    elif len(time_parts) == 3:  
                        hours, minutes, seconds = map(int, time_parts)
                        total_seconds = (hours * 3600) + (minutes * 60) + seconds
                    
                    if total_seconds < 360:
                        video_title = item['title']
                        video_user = item['channel']['name']
                        

                        video_title, video_channelname = await sanitize_string(video_title, video_user)
                        answer.append({
                            'id': item['id'],
                            'title': video_title,
                            'artist': video_channelname,
                            'album': video_title,
                            'cover': item.get('thumbnails', [])[0].get('url', '')
                        })

                return answer
    except:
        ...

    return []
@app.route("/yt/search", methods = ['GET'])
async def search_yt():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    search_qu = request.args.get('qu', None)
    try:
        search_limit = int(request.args.get('limit', 5))
    except ValueError:
        search_limit = 5
    try:
        search_ytm = request.args.get('ytm', 0)
        search_ytm = bool(int(search_ytm))
    except ValueError:
        search_ytm = False
 
    if api_key is not None:
        if search_qu and api_key == WEB_H_CONFIG['api_key']:
            response_data['status'] = 200
            response_data['message'] = ""
            response_data['status'] = True
            response_data['data'] = await generate_yt_answer(search_qu, search_limit, search_ytm)
            
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status
@app.route("/yt/stream", methods = ['GET'])
async def stream_yt():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    video_id = request.args.get('id', None)

    if api_key is not None:
        if video_id and api_key == WEB_H_CONFIG['api_key']:
            try:
                a = YouTube(f'https://youtu.be/{video_id}')
                audio_stream = a.streams.filter(only_audio=True, file_extension='mp4').first()
                audio_length = a.length
                start = 0
                end = audio_length - 1
                status_code = 200
                range_header = request.headers.get('Range')
                if range_header and 1 == 0:
                    range_match = re.search(r'(\d+)-(\d*)', range_header)
                    if range_match:
                        start = int(range_match.group(1))
                        end = int(range_match.group(2)) if range_match.group(2) else audio_length - 1
                        status_code = 206
                


                cmd = ["ffmpeg", "-ss", str(start), "-i", audio_stream.url, "-t", str(end - start + 1), "-acodec", "libmp3lame", "-f", "mp3", "-"]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                mp3_data, _ = await proc.communicate()

                headers = {
                    'Accept-Ranges': 'bytes',
                    'Content-Type': 'audio/mp3',
                    'Content-Length': len(mp3_data),
                    'Content-Range': f'bytes {start}-{end}/{audio_length}'
                }
                return Response(mp3_data, content_type='audio/mp3', headers=headers, status=status_code)
            except YTExceptions as yt_eror:
                response_data['message'] = str(yt_eror)
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return web.json_response(response_data, status=response_status)
@app.route("/yt/clip", methods = ['GET'])
async def clip_yt():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    qu = request.args.get('qu', None)

    if api_key is not None:
        if qu and api_key == WEB_H_CONFIG['api_key']:
            try:
                search_result = VideosSearch(qu, limit = 1)
                search_result = await search_result.next()
                if search_result.get('result', []):
                    response_status = 200
                    response_data['message'] = ""
                    response_data['status'] = True
                    response_data['data'] = {
                        "video_id": search_result['result'][0]['id'],
                        "video_title": search_result['result'][0]['title'],
                        "thumbnail": search_result['result'][0].get('thumbnails', [])[-1].get('url', None)
                    }

            except:
                ...
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
############################################################################3c
@app.route("/shazam", methods = ['POST'])
async def shazam_audio():
    try:
        reader = await request.multipart()
        field = await reader.next()

        if field.name == 'audio_file':
            audio_data = await field.read()

            audio_bytes_io = io.BytesIO(audio_data)
            sondData = await shazamAPI.recognize_song(audio_bytes_io.read())
            return web.json_response(sondData)

    except Exception as e:
        return web.Response(status=400, text=f"Error: {str(e)}")
############################################################################3c
############################################################################3c
############################################################################3c

async def exec_genius(qu:str):
    genius_search = geniusAPI.search_songs(qu, 1)
    if genius_search:
        if genius_search.get("hits", []) != []:
            parseUrl = genius_search['hits'][0]['result']['url']
            
            resultLyric = geniusAPI.lyrics(song_url=parseUrl)
            resultLyric = resultLyric.split("\n")
            resultLyric.pop(0)
            resultLyric = '\n'.join(resultLyric)


            titleFixed = genius_search['hits'][0]['result']['full_title']
            if titleFixed.find("by") != -1:
                titleFixed = titleFixed.split("by")[0].strip()
            
            return {
                'link': parseUrl, 
                "lyric": resultLyric, 
                "artist": genius_search['hits'][0]['result']['artist_names'], 
                'title': titleFixed
            }
        
    return None
@app.route("/genius", methods = ['GET'])
async def search_genius(): 
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    search_qu = request.args.get('qu', None)

    if api_key is not None:
        if search_qu and api_key == WEB_H_CONFIG['api_key']:
            task = await APP_LOOP.run_in_executor(None, lambda: exec_genius(search_qu))
            result = await task
            if result:
                response_data['data'] = result
                response_data['message'] = ""
                response_data['status'] = True
                response_status = 200
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return web.json_response(response_data, status=response_status)



@app.route("/")
async def home_page():
    return jsonify({"hello": "world!"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
    #web.run_app(app, host="127.0.0.1", loop=APP_LOOP)