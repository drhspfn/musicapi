import asyncio, io, os
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

SANITIZE_PARTS = ["lyric","lyrics", "(music video)","(official music video)", "feat.", "f."]



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

        for part in SANITIZE_PARTS:
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

DEEZER_API = os.environ.get("DEEZER_ARL", None)
YTM_OAUTH = os.environ.get("YTM_OAUTH", None)
SC_CLIENT = os.environ.get("SC_CLIENT", None)
SC_SECRET = os.environ.get("SC_SECRET", None)
GENIUS_API = os.environ.get("GENIUS_API", None)
APP_API_KEY = os.environ.get("APP_API_KEY", None)

mHelper = MHelper(
    deezer_arl=DEEZER_API, 
    ytm_oauth=YTM_OAUTH,
    sc_data=(
        SC_CLIENT, 
        SC_SECRET))
shazamAPI = Shazam()
geniusAPI = lyricsgenius.Genius(GENIUS_API) 
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
        if audio_id and api_key == APP_API_KEY:
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
        if search_qu and api_key == APP_API_KEY:
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
        if audio_id and api_key == APP_API_KEY:
            track_url = await mHelper.soundcloud.get_track_url(audio_id)
            
            total_filesize = 0
            async with httpx.AsyncClient() as client:
                _response = await client.head(track_url)

                if _response.status_code != 200:
                    return _response.status_code

                total_filesize = int(_response.headers.get('Content-Length', 0))


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
        if search_qu and api_key == APP_API_KEY:
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
        if search_qu and api_key == APP_API_KEY:
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
        if video_id and api_key == APP_API_KEY:
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

    return jsonify(response_data), response_status
@app.route("/yt/clip", methods = ['GET'])
async def clip_yt():
    response_data = {'status': False, 'message': "No mandatory arguments passed", 'data': []}
    response_status = 404
    api_key = request.args.get('secret', None)
    qu = request.args.get('qu', None)

    if api_key is not None:
        if qu and api_key == APP_API_KEY:
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
            return jsonify(sondData), 200

    except Exception as e:
        return jsonify({'status':False, "message": str(e)}), 400
    
    return 400
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
        if search_qu and api_key == APP_API_KEY:
            task = await asyncio.get_event_loop().run_in_executor(None, lambda: exec_genius(search_qu))
            result = await task
            if result:
                response_data['data'] = result
                response_data['message'] = ""
                response_data['status'] = True
                response_status = 200
    else:
        response_status = 401
        response_data['message'] = "The 'secret' parameter was not passed"

    return jsonify(response_data), response_status



@app.route("/")
async def home_page():
    return jsonify({"hello": "world!"})
