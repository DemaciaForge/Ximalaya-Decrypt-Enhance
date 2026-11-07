import base64
import io
import sys
import magic
import pathlib
import os
import glob
import mutagen
import tkinter as tk
from tkinter import filedialog
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from mutagen.easyid3 import ID3
import wasmtime


class XMInfo:
    def __init__(self):
        self.title = ""
        self.artist = ""
        self.album = ""
        self.tracknumber = 0
        self.size = 0
        self.header_size = 0
        self.ISRC = ""
        self.encodedby = ""
        self.encoding_technology = ""

    def iv(self):
        if self.ISRC != "":
            return bytes.fromhex(self.ISRC)
        return bytes.fromhex(self.encodedby)


def get_str(x):
    if x is None:
        return ""
    return x


def read_file(x):
    with open(x, "rb") as f:
        return f.read()


def get_xm_info(data: bytes):
    if len(data) < 10 or data[:3] != b"ID3":
        raise ValueError(
            "文件开头不是 ID3v2 标签，当前仅支持标准 XM 文件；"
            "请确认文件完整且扩展名正确"
        )
    try:
        id3 = ID3(io.BytesIO(data), v2_version=3)
    except mutagen.MutagenError as exc:
        raise ValueError("XM 文件的 ID3 元数据损坏或不受支持") from exc
    id3value = XMInfo()
    try:
        id3value.title = str(id3["TIT2"])
        id3value.album = str(id3["TALB"])
        id3value.artist = str(id3["TPE1"])
        id3value.size = int(str(id3["TSIZ"]))
        id3value.encoding_technology = str(id3["TSSE"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("XM 文件缺少必要的 ID3 元数据") from exc
    # 提取官方文件头里自带的真实集数序号
    try:
        id3value.tracknumber = int(str(id3["TRCK"]))
    except:
        id3value.tracknumber = 0
        
    id3value.ISRC = "" if id3.get("TSRC") is None else str(id3["TSRC"])
    id3value.encodedby = "" if id3.get("TENC") is None else str(id3["TENC"])
    id3value.header_size = id3.size
    if id3value.size <= 0 or id3value.header_size + id3value.size > len(data):
        raise ValueError("XM 文件的加密数据长度无效，文件可能不完整")
    try:
        iv = id3value.iv()
    except ValueError as exc:
        raise ValueError("XM 文件缺少有效的 AES 初始向量") from exc
    if len(iv) != AES.block_size:
        raise ValueError("XM 文件的 AES 初始向量长度无效")
    return id3value


def get_printable_count(x: bytes):
    for i, c in enumerate(x):
        if c < 0x20 or c > 0x7e:
            return i
    return len(x)


def get_printable_bytes(x: bytes):
    return x[:get_printable_count(x)]


def xm_decrypt(raw_data):
    wasm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xm_encryptor.wasm")
    store = wasmtime.Store()
    module = wasmtime.Module.from_file(store.engine, wasm_path)
    xm_encryptor = wasmtime.Instance(store, module, [])
    exports = xm_encryptor.exports(store)
    
    xm_info = get_xm_info(raw_data)
    encrypted_data = raw_data[xm_info.header_size:xm_info.header_size + xm_info.size:]

    # Stage 1 aes-256-cbc
    xm_key = b"ximalayaximalayaximalayaximalaya"
    cipher = AES.new(xm_key, AES.MODE_CBC, xm_info.iv())
    if not encrypted_data:
        raise ValueError("XM 加密数据长度无效，文件可能不完整")
    # Some XM variants store a partial final block; pad only that case.
    decrypt_data = encrypted_data if len(encrypted_data) % 16 == 0 else pad(encrypted_data, 16)
    de_data = cipher.decrypt(decrypt_data)
    
    # Stage 2 xmDecrypt
    de_data = get_printable_bytes(de_data)
    track_id = str(xm_info.tracknumber).encode()
    stack_pointer = exports["a"](store, -16)
    assert isinstance(stack_pointer, int)
    de_data_offset = exports["c"](store, len(de_data))
    assert isinstance(de_data_offset, int)
    track_id_offset = exports["c"](store, len(track_id))
    assert isinstance(track_id_offset, int)
    memory_i = exports["i"]
    memory_i.write(store, de_data, de_data_offset)
    memory_i.write(store, track_id, track_id_offset)

    exports["g"](store, stack_pointer, de_data_offset, len(de_data), track_id_offset, len(track_id))
    result_header = memory_i.read(store, stack_pointer, stack_pointer + 8)
    result_pointer = int.from_bytes(result_header[0:4], "little", signed=True)
    result_length = int.from_bytes(result_header[4:8], "little", signed=True)
    
    result_data = bytes(memory_i.read(store, result_pointer, result_pointer + result_length)).decode()
    
    # Stage 3 combine
    decrypted_data = base64.b64decode(xm_info.encoding_technology + result_data)
    final_data = decrypted_data + raw_data[xm_info.header_size + xm_info.size::]
    return xm_info, final_data


def find_ext(data):
    exts = ["m4a", "mp3", "flac", "wav"]
    value = magic.from_buffer(data).lower()
    for ext in exts:
        if ext in value:
            return ext
    raise Exception(f"unexpected format {value}")


def replace_invalid_chars(name):
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    name = name.strip().rstrip(".")
    for char in invalid_chars:
        if char in name:
            name = name.replace(char, " ")
    name = " ".join(name.split())
    if not name or name in {".", ".."}:
        return "未命名"
    device_name = name.split(".", 1)[0].upper()
    if device_name in {"CON", "PRN", "AUX", "NUL"} or (device_name.startswith(("COM", "LPT")) and device_name[3:].isdigit()):
        return f"_{name}"
    return name


def unique_output_file(path):
    """Return a non-existing path, preserving the original extension."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    index = 1
    while True:
        candidate = f"{stem} ({index}){ext}"
        if not os.path.exists(candidate):
            return candidate
        index += 1


def decrypt_xm_file(from_file, output_path, do_rename=False):
    data = read_file(from_file)
    info, audio_data = xm_decrypt(data)
    
    album_name = replace_invalid_chars(info.album)
    title_name = replace_invalid_chars(info.title)
    ext = find_ext(audio_data[:0xff])
    
    album_path = os.path.join(output_path, album_name)
    output_root = os.path.abspath(output_path)
    if os.path.commonpath([output_root, os.path.abspath(album_path)]) != output_root:
        raise ValueError("专辑名称包含非法路径")
    if not os.path.exists(album_path):
        os.makedirs(album_path)
        
    # 【原生级集数重命名】
    if do_rename and info.tracknumber > 0:
        formatted_name = f"{info.tracknumber:04d} - {title_name}.{ext}"
        output_file = os.path.join(album_path, formatted_name)
    else:
        output_file = os.path.join(album_path, f"{title_name}.{ext}")
    output_file = unique_output_file(output_file)
    
    buffer = io.BytesIO(audio_data)
    
    # 【内存级音频双重完整性校验】
    try:
        tags = mutagen.File(buffer, easy=True)
        if tags is None:
            raise ValueError("无法识别音频格式，文件可能已严重损坏")
            
        duration = getattr(tags.info, 'length', 0)
        bitrate = getattr(tags.info, 'bitrate', 0)
        
        if duration > 0 and bitrate > 0:
            expected_size = (duration * bitrate) / 8
            actual_size = len(audio_data)
            completion_rate = actual_size / expected_size
            
            if completion_rate < 0.85:
                raise ValueError(f"下载断层 (完整度仅 {completion_rate*100:.1f}%)")
                
    except mutagen.MutagenError:
        raise ValueError("音频流格式破坏，源文件下载不完整")
        
    tags["title"] = info.title
    tags["album"] = info.album
    tags["artist"] = info.artist
    tags.save(buffer)
    
    with open(output_file, "wb") as f:
        buffer.seek(0)
        f.write(buffer.read())


def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    root.destroy()
    return file_path


def select_directory():
    root = tk.Tk()
    root.withdraw()
    directory_path = filedialog.askdirectory()
    root.destroy()
    return directory_path


def main_loop():
    while True:
        print("\n" + "="*50)
        print(" 欢迎使用喜马拉雅音频解密工具 (v1.0.7)")
        print(" 核心算法: @sld272 | 维护加强: @a176073240-cmd ")
        print("="*50)
        print("1. 解密单个文件")
        print("2. 批量解密文件")
        print("3. 退出")
        choice = input("请输入选项: ")
        
        if choice == "1" or choice == "2":
            if choice == "1":
                files_to_decrypt = [select_file()]
                if files_to_decrypt == [""]:
                    print("检测到文件选择窗口被关闭")
                    continue
            elif choice == "2":
                dir_to_decrypt = select_directory()
                if dir_to_decrypt == "":
                    print("检测到目录选择窗口被关闭")
                    continue
                files_to_decrypt = glob.glob(os.path.join(dir_to_decrypt, "*.xm"))
                
            total_files = len(files_to_decrypt)
            if total_files == 0:
                print("未找到待处理的 .xm 文件！")
                continue
                
            print("\n请选择是否需要在文件名前面加上序号（按顺序重命名）：")
            print("1. 不进行按顺序重命名 (输出例如：马拉车.m4a)")
            print("2. 进行按顺序重命名   (输出例如：0204 - 马拉车.m4a)")
            rename_choice = input("请输入 (1/2): ")
            do_rename = (rename_choice == "2")

            print("\n请选择是否需要设置输出路径：（不设置默认为本程序目录下的output文件夹）")
            print("1. 设置输出路径")
            print("2. 不设置输出路径")
            out_choice = input("请输入 (1/2): ")
            
            if out_choice == "1":
                output_path = select_directory()
                if output_path == "":
                    print("检测到目录选择窗口被关闭")
                    continue
            else:
                output_path = os.path.join(os.getcwd(), "output")
                
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            success_count = 0
            failed_list = []
            
            print(f"\n🚀 开始火力全开处理，共 {total_files} 个文件...")
            print("（运行期间将隐藏成功提示，保持静默，请耐心等待进度条走完）\n")
            
            for i, file in enumerate(files_to_decrypt, 1):
                file_name = os.path.basename(file)
                
                print(f"\r⏳ 正在解密进度: [ {i} / {total_files} ]", end="", flush=True)
                
                try:
                    if os.path.getsize(file) == 0:
                        raise Exception("文件大小为 0KB (空文件)")
                        
                    decrypt_xm_file(file, output_path, do_rename)
                    success_count += 1
                except Exception as e:
                    failed_list.append((file_name, str(e)))
            
            print("\n\n" + "="*50)
            print(" 📊 解密任务分类报告")
            print("="*50)
            
            print(f"✅ 完美解密文件: {success_count} 个")
            
            if failed_list:
                print(f"\n🚨 智能拦截残次品/失败: {len(failed_list)} 个，清单如下：")
                print("-" * 45)
                for fail_name, reason in failed_list:
                    print(f"❌ {fail_name}")
                    print(f"   -> 状态: {reason}")
                print("-" * 45)
                print("\n💡 提示：请根据以上清单，回客户端重新下载这几个文件即可。")
            else:
                print("\n🎉 恭喜！本次转码零失误，全部完美保存！")
            
            print("="*50)
            
        elif choice == "3":
            sys.exit()
        else:
            print("输入错误，请重新输入！")

if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        print(f"\n\n🚨 哎呀！程序发生了意外的崩溃！")
        print(f"崩溃原因: {e}")
    finally:
        input("\n按回车键退出窗口...")
