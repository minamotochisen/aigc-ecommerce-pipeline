# -*- coding: utf-8 -*-
"""ComfyUI API 工具：提交工作流 / 轮询 / 下载输出 / 上传输入图"""
import json
import time
import urllib.parse
import urllib.request

COMFY = "http://127.0.0.1:8188"


def _req(url, data=None, timeout=30):
    if data is not None:
        req = urllib.request.Request(url, data=data)
    else:
        req = url
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:2000]
        raise RuntimeError(f"HTTP {e.code}: {body}") from None


def wait_server(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            _req(COMFY + "/system_stats", timeout=3)
            return True
        except Exception:
            time.sleep(2)
    return False


def upload_image(path, name=None):
    """上传输入图到 ComfyUI input 目录，返回 (filename, subfolder, type)"""
    import mimetypes
    import os
    import uuid
    name = name or os.path.basename(path)
    boundary = uuid.uuid4().hex
    with open(path, "rb") as f:
        payload = f.read()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        COMFY + "/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def queue(workflow, timeout=600, poll=2):
    """提交工作流 API JSON，阻塞直到完成，返回 {node_id: outputs}"""
    wid = _req(
        COMFY + "/prompt",
        json.dumps({"prompt": workflow}).encode(),
    )
    prompt_id = json.loads(wid)["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = json.loads(_req(f"{COMFY}/history/{prompt_id}"))
        if prompt_id in hist:
            outputs = hist[prompt_id]["outputs"]
            status = hist[prompt_id].get("status", {})
            if status.get("status_str") == "error":
                msgs = [m for m in status.get("messages", []) if m[0] == "execution_error"]
                raise RuntimeError(json.dumps(msgs, ensure_ascii=False)[:3000])
            if outputs:
                return outputs
        time.sleep(poll)
    raise TimeoutError(f"workflow timeout after {timeout}s")


def fetch_outputs(outputs, outdir):
    """下载 outputs 里所有图片，返回本地路径列表"""
    import os
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for node_out in outputs.values():
        for img in node_out.get("images", []):
            if img.get("type") not in (None, "output"):
                continue
            q = urllib.parse.urlencode(
                {
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                }
            )
            data = _req(f"{COMFY}/view?{q}", timeout=120)
            p = os.path.join(outdir, img["filename"])
            with open(p, "wb") as f:
                f.write(data)
            paths.append(p)
    return paths


def run(workflow, outdir, timeout=600):
    outputs = queue(workflow, timeout=timeout)
    paths = fetch_outputs(outputs, outdir)
    # 防止多张连续生成时模型缓存累积把 RAM 吃满导致页交换(实测 29GB 触发 240s/it)
    try:
        _req(COMFY + "/free", json.dumps({"unload_models": True, "free_memory": True}).encode(), timeout=30)
    except Exception:
        pass
    return paths


COMFY_DIR = (r"D:\ComfyUI_windows_portable\ComfyUI_windows_portable_nvidia"
             r"\ComfyUI_windows_portable")


def restart_server(timeout=300):
    """杀掉 ComfyUI(按命令行匹配, 不误杀其他 python)并重新拉起"""
    import os
    import subprocess
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object {$_.CommandLine -like '*ComfyUI*main.py*'} | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=90)
    time.sleep(4)
    exe = os.path.join(COMFY_DIR, "python_embeded", "python.exe")
    logf = open(os.path.join(COMFY_DIR, "comfyui_watchdog.log"), "ab")
    DETACHED = 0x00000008 | 0x00000200
    subprocess.Popen(
        [exe, "-s", "ComfyUI/main.py", "--windows-standalone-build",
         "--disable-auto-launch", "--disable-dynamic-vram"],
        cwd=COMFY_DIR, stdout=logf, stderr=subprocess.STDOUT,
        creationflags=DETACHED)
    if not wait_server(timeout):
        raise RuntimeError("comfyui restart failed")
    return True


def run_watchdog(workflow, outdir, per_run=390, attempts=4, fresh_each=True):
    """单图超过 per_run 秒未完成(服务端冻结)则重启 ComfyUI 并重排队;
    fresh_each=True 时每张图前主动重启, 规避 RAM 累积导致的页交换(实测 76s/it 恶化)"""
    last = None
    for i in range(attempts):
        try:
            if fresh_each and i == 0:
                restart_server()
            outputs = queue(workflow, timeout=per_run)
            paths = fetch_outputs(outputs, outdir)
            try:
                _req(COMFY + "/free", json.dumps(
                    {"unload_models": True, "free_memory": True}).encode(), timeout=30)
            except Exception:
                pass
            return paths
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last = e
            print(f"[watchdog] run frozen/crashed ({type(e).__name__}), restart attempt {i + 1}/{attempts}", flush=True)
            restart_server()
    raise RuntimeError(f"watchdog exhausted: {last}")


if __name__ == "__main__":
    import sys
    if wait_server():
        print("ComfyUI OK")
    else:
        print("ComfyUI NOT reachable")
        sys.exit(1)
