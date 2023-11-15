# -*- coding: utf-8 -*-
import ctypes
import sys

import cv2

from ..configure import boxcfg
from ..configure.config import rootdir
from datetime import timedelta
import os
import whisper
from ctypes.util import find_library

def transcribe_audio(audio_path, model, language):
    model = whisper.load_model(model, download_root=rootdir + "/models")  # Change this to your desired model
    print(f"Whisper model loaded.{language},{audio_path=}")
    transcribe = model.transcribe(audio_path, language="zh" if language in ["zh-cn", "zh-tw"] else language)
    segments = transcribe['segments']
    print(f"{segments=}")
    result = ""
    for segment in segments:
        print(segment)
        startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
        endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
        text = segment['text']
        segmentId = segment['id'] + 1
        result += f"{segmentId}\n{startTime} --> {endTime}\n{text.strip()}\n\n"
    return result

# 获取摄像头
def get_camera_list():
    if boxcfg.check_camera_ing:
        return
    boxcfg.check_camera_ing = True
    index = 0
    if len(boxcfg.camera_list) > 0:
        boxcfg.check_camera_ing = False
        return
    print("获取摄像头")
    try:
        while True:
            camera = cv2.VideoCapture(index)
            if not camera.read()[0]:
                break
            else:
                boxcfg.camera_list.append(index)
                index += 1
        camera.release()
    except Exception as e:
        print("获取摄像头出错")
    boxcfg.check_camera_ing = False


def find_lib():
    dll = None
    plugin_path = os.environ.get('PYTHON_VLC_MODULE_PATH', None)
    if 'PYTHON_VLC_LIB_PATH' in os.environ:
        try:
            dll = ctypes.CDLL(os.environ['PYTHON_VLC_LIB_PATH'])
        except OSError:
            return
    if plugin_path and not os.path.isdir(plugin_path):
        return
    if dll is not None:
        return dll, plugin_path

    if sys.platform.startswith('win'):
        libname = 'libvlc.dll'
        p = find_library(libname)
        if p is None:
            try:  # some registry settings
                # leaner than win32api, win32con
                import winreg as w
                for r in w.HKEY_LOCAL_MACHINE, w.HKEY_CURRENT_USER:
                    try:
                        r = w.OpenKey(r, 'Software\\VideoLAN\\VLC')
                        plugin_path, _ = w.QueryValueEx(r, 'InstallDir')
                        w.CloseKey(r)
                        break
                    except w.error:
                        pass
            except ImportError:  # no PyWin32
                pass
            if plugin_path is None:
                # try some standard locations.
                programfiles = os.environ["ProgramFiles"]
                homedir = os.environ["HOMEDRIVE"]
                for p in ('{programfiles}\\VideoLan{libname}', '{homedir}:\\VideoLan{libname}',
                          '{programfiles}{libname}', '{homedir}:{libname}'):
                    p = p.format(homedir=homedir,
                                 programfiles=programfiles,
                                 libname='\\VLC\\' + libname)
                    if os.path.exists(p):
                        plugin_path = os.path.dirname(p)
                        break
            if plugin_path is not None:  # try loading
                # PyInstaller Windows fix
                if 'PyInstallerCDLL' in ctypes.CDLL.__name__:
                    ctypes.windll.kernel32.SetDllDirectoryW(None)
                p = os.getcwd()
                os.chdir(plugin_path)
                # if chdir failed, this will raise an exception
                dll = ctypes.CDLL('.\\' + libname)
                # restore cwd after dll has been loaded
                os.chdir(p)
            else:  # may fail
                dll = ctypes.CDLL('.\\' + libname)
        else:
            plugin_path = os.path.dirname(p)
            dll = ctypes.CDLL(p)

    elif sys.platform.startswith('darwin'):
        # FIXME: should find a means to configure path
        d = '/Applications/VLC.app/Contents/MacOS/'
        c = d + 'lib/libvlccore.dylib'
        p = d + 'lib/libvlc.dylib'
        if os.path.exists(p) and os.path.exists(c):
            # pre-load libvlccore VLC 2.2.8+
            ctypes.CDLL(c)
            dll = ctypes.CDLL(p)
            for p in ('modules', 'plugins'):
                p = d + p
                if os.path.isdir(p):
                    plugin_path = p
                    break
        else:  # hope, some [DY]LD_LIBRARY_PATH is set...
            # pre-load libvlccore VLC 2.2.8+
            ctypes.CDLL('libvlccore.dylib')
            dll = ctypes.CDLL('libvlc.dylib')

    else:
        # All other OSes (linux, freebsd...)
        p = find_library('vlc')
        try:
            dll = ctypes.CDLL(p)
        except OSError:  # may fail
            dll = None
        if dll is None:
            try:
                dll = ctypes.CDLL('libvlc.so.5')
            except:
                raise NotImplementedError('Cannot find libvlc lib')

    return dll
