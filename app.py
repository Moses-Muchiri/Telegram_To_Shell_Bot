import telebot
import os
import subprocess
from dotenv import load_dotenv
from colorama import init, Fore
import psutil

load_dotenv()
init(autoreset=True)

TOKEN = os.getenv("TOKEN")
AUTHORIZED_CHAT_ID = os.getenv("AUTHORIZED_CHAT_ID")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads/")

ALLOWED_COMMANDS = os.getenv("ALLOWED_COMMANDS", "").split(",")
ALLOWED_DOCUMENT_TYPES = os.getenv("ALLOWED_DOCUMENT_TYPES", "").split(",")
ALLOWED_AUDIO_TYPES = os.getenv("ALLOWED_AUDIO_TYPES", "").split(",")
ALLOWED_VIDEO_TYPES = os.getenv("ALLOWED_VIDEO_TYPES", "").split(",")

bot = telebot.TeleBot(TOKEN)

def is_safe_path(basedir, path, follow_symlinks=True):
    if follow_symlinks:
        return os.path.realpath(path).startswith(os.path.realpath(basedir) + os.sep)
    return os.path.abspath(path).startswith(os.path.abspath(basedir) + os.sep)

def is_valid_file_extension(filename, allowed_extensions):
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)

def shell(cmd):
    if cmd.split()[0] not in ALLOWED_COMMANDS:
        error_message = "ERROR: Command not allowed."
        print(Fore.BLUE + error_message)
        return error_message
    
    try:
        print(Fore.WHITE + f"Executing command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(Fore.BLUE + "Command ran successfully.")
            return "Command ran successfully."
        else:
            error_message = f"ERROR: {result.stderr.strip()}"
            print(Fore.BLUE + error_message)
            return error_message
    except subprocess.TimeoutExpired:
        timeout_message = "ERROR: Command timed out"
        print(Fore.BLUE + timeout_message)
        return timeout_message
    except Exception as e:
        error_message = f"ERROR: {e}"
        print(Fore.BLUE + error_message)
        return error_message

def forward_message(message):
    bot.forward_message(AUTHORIZED_CHAT_ID, message.chat.id, message.message_id)

@bot.message_handler(commands=['upload'])
def upload_file(message):
    if message.reply_to_message:
        file_info = bot.get_file(message.reply_to_message.document.file_id if message.reply_to_message.document else 
                                  message.reply_to_message.audio.file_id if message.reply_to_message.audio else 
                                  message.reply_to_message.video.file_id if message.reply_to_message.video else 
                                  message.reply_to_message.photo[-1].file_id if message.reply_to_message.photo else None)
        
        if not file_info:
            bot.send_message(message.chat.id, "Please reply to a valid document, image, audio, or video file with /upload.")
            return

        downloaded_file = bot.download_file(file_info.file_path)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        if message.reply_to_message.document:
            file_path = os.path.join(UPLOAD_DIR, message.reply_to_message.document.file_name)
            if is_valid_file_extension(file_path, ALLOWED_DOCUMENT_TYPES):
                if is_safe_path(UPLOAD_DIR, file_path):
                    with open(file_path, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    bot.send_message(message.chat.id, "Document uploaded successfully.")
                else:
                    bot.send_message(message.chat.id, "Invalid file path.")
            else:
                bot.send_message(message.chat.id, "Unsupported document format.")
        
        elif message.reply_to_message.photo:
            file_path = os.path.join(UPLOAD_DIR, f"{message.reply_to_message.photo[-1].file_id}.jpg")
            if is_safe_path(UPLOAD_DIR, file_path):
                with open(file_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                bot.send_message(message.chat.id, "Image uploaded successfully.")
            else:
                bot.send_message(message.chat.id, "Invalid file path.")

        elif message.reply_to_message.audio:
            file_path = os.path.join(UPLOAD_DIR, f"{message.reply_to_message.audio.file_name}")
            if is_valid_file_extension(file_path, ALLOWED_AUDIO_TYPES):
                if is_safe_path(UPLOAD_DIR, file_path):
                    with open(file_path, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    bot.send_message(message.chat.id, "Audio uploaded successfully.")
                else:
                    bot.send_message(message.chat.id, "Invalid file path.")
            else:
                bot.send_message(message.chat.id, "Unsupported audio format.")

        elif message.reply_to_message.video:
            file_path = os.path.join(UPLOAD_DIR, f"{message.reply_to_message.video.file_name}")
            if is_valid_file_extension(file_path, ALLOWED_VIDEO_TYPES):
                if is_safe_path(UPLOAD_DIR, file_path):
                    with open(file_path, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    bot.send_message(message.chat.id, "Video uploaded successfully.")
                else:
                    bot.send_message(message.chat.id, "Invalid file path.")
            else:
                bot.send_message(message.chat.id, "Unsupported video format.")

    else:
        bot.send_message(message.chat.id, "Please reply to a document, image, audio, or video with /upload to upload.")

@bot.message_handler(commands=['getfile'])
def send_file(message):
    try:
        filename = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        if not filename:
            bot.send_message(message.chat.id, "Please specify a filename.")
            return

        file_path = os.path.join(UPLOAD_DIR, filename)
        if is_safe_path(UPLOAD_DIR, file_path) and os.path.isfile(file_path):
            with open(file_path, 'rb') as file:
                bot.send_document(message.chat.id, file)
        else:
            bot.send_message(message.chat.id, "File not found or invalid path.")
    except IndexError:
        bot.send_message(message.chat.id, "Please specify a filename.")
    except Exception as e:
        bot.send_message(message.chat.id, f"An error occurred: {str(e)}")

@bot.message_handler(commands=['history'])
def command_history(message):
    if hasattr(command_history, 'history'):
        history_text = "\n".join(command_history.history)
        bot.send_message(message.chat.id, history_text if history_text else "No command history.")
    else:
        bot.send_message(message.chat.id, "No command history.")

@bot.message_handler(commands=['sysinfo'])
def sys_info(message):
    cpu_usage = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')
    info = f"CPU Usage: {cpu_usage}%\nMemory Usage: {memory_info.percent}%\nDisk Usage: {disk_info.percent}%"
    bot.send_message(message.chat.id, info)

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    print(Fore.WHITE + f"Received message: {message.text}")
    
    if message.chat.id != int(AUTHORIZED_CHAT_ID):
        print(Fore.BLUE + "Forwarding message to authorized chat.")
        forward_message(message)
    else:
        print(Fore.BLUE + "Authorized user detected, executing command.")
        if not hasattr(command_history, 'history'):
            command_history.history = []
        command_history.history.append(message.text)
        ret_text = shell(message.text)
        if ret_text:
            bot.send_message(message.chat.id, ret_text)

def send_connection_message():
    bot.send_message(AUTHORIZED_CHAT_ID, "Connected to PC")

if __name__ == "__main__":
    print(Fore.GREEN + "Connected to my bot")
    send_connection_message()
    bot.polling(none_stop=True)
