import os
import subprocess
import time
from datetime import datetime
import logging
import argparse
import re
ADB_SERIAL = "CUYDU19528013322"


def adb_command(command: str) -> subprocess.CompletedProcess:
    """Run an ADB command and return the CompletedProcess."""
    cmd = command
    if re.match(r'^\s*adb\b', cmd) and not re.match(r'^\s*adb\s+devices\b', cmd):
        cmd = re.sub(r'^\s*adb\b', f'adb -s {ADB_SERIAL}', cmd, count=1)
    return subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def check_adb_connection() -> bool:
    """Check if there is at least one device connected via ADB."""
    result = adb_command("adb devices")
    if result.returncode != 0:
        logging.error(f"ADB devices 命令失败: {result.stderr}")
        return False

    # Look for a line that ends with '\tdevice' (a connected device)
    lines = result.stdout.strip().splitlines()
    for line in lines[1:]:  # skip the header line
        if line.strip().endswith("\tdevice"):
            return True
    logging.error("未检测到已连接设备，请检查USB连接或ADB权限。")
    return False


def ensure_dirs():
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def go_home():
    """Press the HOME key to ensure we are on the launcher screen."""
    result = adb_command("adb shell input keyevent 3")
    if result.returncode != 0:
        logging.warning(f"发送HOME键失败: {result.stderr}")
    time.sleep(1.0)


def capture_screenshot(filename: str | None = None) -> str:
    """Capture a screenshot from the device and save under screenshots/.

    Returns the full local path to the saved image.
    """
    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not filename:
        filename = f"home_{timestamp}.png"

    local_path = os.path.join("screenshots", filename)
    device_path = f"/sdcard/{filename}"

    logging.info(f"开始截屏: {filename}")
    # Capture to device
    cap = adb_command(f"adb shell screencap -p {device_path}")
    if cap.returncode != 0:
        logging.error(f"设备截屏失败: {cap.stderr}")
        raise RuntimeError(f"设备截屏失败: {cap.stderr}")

    # Pull to local
    pull = adb_command(f"adb pull {device_path} {local_path}")
    if pull.returncode != 0:
        logging.error(f"拉取截图失败: {pull.stderr}")
        raise RuntimeError(f"拉取截图失败: {pull.stderr}")

    # Clean up device file
    adb_command(f"adb shell rm {device_path}")

    logging.info(f"截图已保存: {local_path}")
    return local_path


def setup_logging():
    ensure_dirs()
    log_file = os.path.join("logs", f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_capture_home.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="截取当前手机桌面到 screenshots 目录")
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="保存的文件名（默认: home_时间戳.png）",
    )
    parser.add_argument(
        "--home",
        action="store_true",
        help="发送HOME键返回桌面后再截屏",
    )
    args = parser.parse_args()

    setup_logging()

    if not check_adb_connection():
        raise SystemExit(1)

    if args.home:
        logging.info("发送HOME键，返回桌面...")
        go_home()
    else:
        logging.info("直接截取当前界面...")

    saved_path = capture_screenshot(args.filename)
    print(f"截图保存路径: {saved_path}")


if __name__ == "__main__":
    main()
