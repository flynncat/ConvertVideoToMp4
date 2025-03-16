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
    def __init__(self, progress_bar, status_label, window):
        self.progress_bar = progress_bar
        self.status_label = status_label
        self.window = window
        self.original_files = []  # 用于存储所有原始文件路径

    def convert_video(self, input_path, output_path):
        # 调用 FFmpeg 转换
        command = [
            FFMPEG_PATH,
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            output_path
        ]
        
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("错误", f"转换失败: {str(e)}")
        except FileNotFoundError:
            messagebox.showerror("错误", f"未找到 FFmpeg，请检查路径配置: {FFMPEG_PATH}")

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
            return float(output)
        except subprocess.CalledProcessError:
            return None

    def batch_convert(self, target_folder):
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
                self.convert_video(input_path, output_path)
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
    window.geometry("400x200")
    

    # 添加进度条
    progress_bar = ttk.Progressbar(window, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(pady=20)

    # 添加状态标签
    status_label = tk.Label(window, text="等待转换...", font=("Arial", 12))
    status_label.pack(pady=10)

    # 添加按钮
    def start_conversion():
        start_button.config(state=tk.DISABLED)  # 禁用按钮
        try:
            target_folder = select_folder()
            if not target_folder:
                return
            converter = VideoConverter(progress_bar, status_label, window)
            converter.batch_convert(target_folder)
        finally:
            start_button.config(state=tk.NORMAL)  # 恢复按钮

    start_button = tk.Button(window, text="开始转换", command=start_conversion)
    start_button.pack(pady=10)

    # 运行主循环
    window.mainloop()

if __name__ == "__main__":
    main()