import os
import subprocess
import shutil
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 配置参数
SUPPORTED_FORMATS = [".mov", ".avi", ".rmvb", ".mkv", ".flv"]  # 支持转换的格式
OUTPUT_FORMAT = ".mp4"

# 自动判断操作系统并设置 FFmpeg 路径
if platform.system() == "Windows":
   # Windows 优先从环境变量中查找
    FFMPEG_PATH = shutil.which("ffmpeg") or "C:\\ffmpeg\\bin\\ffmpeg.exe"
    FFPROBE_PATH = shutil.which("ffprobe") or "C:\\ffmpeg\\bin\\ffprobe.exe" #自定义路径

else:
    # Mac/Linux 检查常见安装路径
    possible_paths = [
        "/usr/local/bin/ffmpeg",      # Intel Mac 默认路径
        "/opt/homebrew/bin/ffmpeg",   # Apple Silicon Mac 默认路径
        "/usr/bin/ffmpeg"             # Linux 常见路径
    ]
    FFMPEG_PATH = next((p for p in possible_paths if os.path.exists(p)), "ffmpeg")
    FFPROBE_PATH = FFMPEG_PATH.replace("ffmpeg", "ffprobe")

class VideoConverter:
    def __init__(self, progress_bar, current_progress_bar,status_label, window):
        self.progress_bar = progress_bar
        self.status_label = status_label
        self.current_progress_bar = current_progress_bar
        self.window = window
        self.original_files = []  # 用于存储所有原始文件路径

    def convert_video(self, input_path, output_path, codec, preset, crf):
        # 获取视频总时长
        duration = self.get_video_duration(input_path)
        if duration is None:
            raise Exception("无法获取视频时长")

        # 初始化当前文件进度条
        self.current_progress_bar["value"] = 0
        self.current_progress_bar["maximum"] = duration
        
        # 调用 FFmpeg 转换
        command = [
            FFMPEG_PATH,
            "-i", input_path,
            "-c:v", codec,          # 编码模式（h264 或 h265）
            "-preset", preset,      # 平衡速度与质量
            "-crf", str(crf),       # 画质控制
            "-c:a", "aac",          # 音频编码
            output_path
        ]
        
        process = subprocess.Popen(command, stderr=subprocess.PIPE, universal_newlines=True)
        # 实时解析 FFmpeg 输出
        while True:
            line = process.stderr.readline()
            if line == "" and process.poll() is not None:
                break

            # 解析时间进度
            if "time=" in line:
                time_str = line.split("time=")[1].split(" ")[0]
                current_time = self.time_to_seconds(time_str)
                self.current_progress_bar["value"] = current_time
                self.current_progress_bar.update()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
        
        #try:
           # subprocess.run(command, check=True)
        #except subprocess.CalledProcessError as e:
            #messagebox.showerror("错误", f"转换失败: {str(e)}")
        #except FileNotFoundError:
            #messagebox.showerror("错误", f"未找到 FFmpeg，请检查路径配置: {FFMPEG_PATH}")

    def get_video_duration(self, input_path):
        # 获取视频总时长（秒）
        command = [
            FFPROBE_PATH,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path
        ]
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
            output = output.decode("utf-8").strip()  # 解码并去除空白字符
            if output.lower() == "n/a" or not output:
                raise ValueError(f"无效的视频时长: {output}")
            return float(output)
        except subprocess.CalledProcessError as e:
            print(f"FFprobe 错误: {e.output}")
            return None
        except ValueError as e:
            print(f"视频时长解析失败: {str(e)}")
            return None

    def time_to_seconds(self, time_str):
        if(time_str == "N/A"):
            return print(f"无法解析时间格式: {time_str}") #临时跳过的方案，防止苹果预览文件及部分文件转换时时间获取异常的情况
        # 将时间字符串（HH:MM:SS.ms 或 MM:SS.ms 或 SS.ms）转换为秒
        parts = time_str.split(":")
        if len(parts) == 3:  # HH:MM:SS
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:  # MM:SS
            m, s = parts
            return int(m) * 60 + float(s)
        elif len(parts) == 1:  # SS
            return float(parts[0])
        else:
            raise ValueError(f"无法解析时间格式: {time_str}")
    
    def batch_convert(self, target_folder, codec, preset, crf):
        # 递归遍历文件夹及其子文件夹
        video_files = []
        for root, _, files in os.walk(target_folder):
            for file in files:
                if os.path.splitext(file)[1].lower() in SUPPORTED_FORMATS:
                    video_files.append(os.path.join(root, file))

        total_files = len(video_files)

        if total_files == 0:
            messagebox.showinfo("提示", "文件夹及其子文件夹中没有支持转换的视频文件！")
            return

        # 初始化进度条
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = total_files

        # 批量转换
        for index, input_path in enumerate(video_files):
            output_path = os.path.splitext(input_path)[0] + OUTPUT_FORMAT
             
            self.status_label.config(text=f"正在转换: {os.path.basename(input_path)} ({index + 1}/{total_files})")
            
            # 更新进度条
            self.progress_bar["value"] = index + 1
            self.progress_bar.update()
            
            # 检查是否已存在同名 MP4 文件
            if os.path.exists(output_path):
               self.status_label.config(text=f"跳过已存在文件: {os.path.basename(input_path)} ({index + 1}/{total_files})")
               self.progress_bar["value"] = index + 1
               self.progress_bar.update()
               # 记录原始文件路径
               self.original_files.append(input_path)
               continue
           

            try:
                # 转换视频
                self.convert_video(input_path, output_path, codec, preset, crf)
                # 记录原始文件路径
                self.original_files.append(input_path)
                
            except Exception as e:
                messagebox.showerror("错误", f"转换失败: {str(e)}")
      

        # 全部转换完成后提示是否删除原始文件
        self.status_label.config(text="批量转换完成！")
        if self.original_files and messagebox.askyesno("删除原始文件", "所有视频已转换完成！\n是否删除所有原始文件？"):
            for file in self.original_files:
                try:
                    os.remove(file)
                    print(f"已删除原文件: {file}")
                except Exception as e:
                    print(f"删除失败: {file} - {str(e)}")
            messagebox.showinfo("提示", "原始文件已删除！")

        # 允许关闭窗口
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

def select_folder():
    # 弹出文件夹选择窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    folder = filedialog.askdirectory(title="选择监控文件夹")
    return folder

def main():
    # 创建主窗口
    window = tk.Tk()
    window.title("视频转换工具")
    window.geometry("400x320")

    # 编码模式选择
    codec_label = tk.Label(window, text="编码模式:")
    codec_label.grid(row=0, column=0, padx=10, pady=10)
    codec_var = tk.StringVar(value="libx264")  # 默认 h264
    codec_menu = ttk.Combobox(window, textvariable=codec_var, values=["libx264", "libx265"])
    codec_menu.grid(row=0, column=1, padx=10, pady=10)

    # 平衡速度与质量选项
    preset_label = tk.Label(window, text="速度与质量:")
    preset_label.grid(row=1, column=0, padx=10, pady=10)
    preset_var = tk.StringVar(value="fast")  # 默认 fast
    preset_menu = ttk.Combobox(window, textvariable=preset_var, values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
    preset_menu.grid(row=1, column=1, padx=10, pady=10)

    # 画质控制
    crf_label = tk.Label(window, text="画质 (CRF):")
    crf_label.grid(row=2, column=0, padx=10, pady=10)
    crf_var = tk.IntVar(value=23)  # 默认 23
    crf_entry = tk.Entry(window, textvariable=crf_var)
    crf_entry.grid(row=2, column=1, padx=10, pady=10)
    
    # 添加总文件进度条
    progress_bar_label = tk.Label(window, text="总文件进度:")
    progress_bar_label.grid(row=3,column=0, padx=10, pady=10)
    progress_bar = ttk.Progressbar(window, orient="horizontal", length=260, mode="determinate")
    progress_bar.grid(row=3, column=1, columnspan=2, padx=10, pady=10)

    # 当前文件进度条
    current_progress_label = tk.Label(window, text="当前文件进度:")
    current_progress_label.grid(row=4, column=0, padx=10, pady=10)
    current_progress_bar = ttk.Progressbar(window, orient="horizontal", length=260, mode="determinate")
    current_progress_bar.grid(row=4, column=1, padx=10, pady=10)

    # 添加状态标签
    status_label = tk.Label(window, text="等待转换...", font=("Arial", 12))
    status_label.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    # 添加按钮
    def start_conversion():
        start_button.config(state=tk.DISABLED)  # 禁用按钮
        try:
            target_folder = select_folder()
            if not target_folder:
                return
            converter = VideoConverter(progress_bar, current_progress_bar, status_label, window)
            converter.batch_convert(target_folder, codec_var.get(), preset_var.get(), crf_var.get())
        finally:
            start_button.config(state=tk.NORMAL)  # 恢复按钮

    start_button = tk.Button(window, text="开始转换", command=start_conversion)
    start_button.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

    # 运行主循环
    window.mainloop()

if __name__ == "__main__":
    main()