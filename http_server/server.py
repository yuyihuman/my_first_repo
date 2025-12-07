import http.server
import socketserver
import socket
import os
import sys
import io
import urllib.parse
import html
import shutil
import time

# 配置端口
PORT = 8000

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 添加一些允许跨域的头，方便调试或被其他前端调用
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        entries.sort(key=lambda a: a.casefold())
        f = io.BytesIO()
        displaypath = urllib.parse.unquote(self.path)
        f.write(b"<!DOCTYPE html>")
        f.write(f"<html><head><meta charset='utf-8'><title>Index of {html.escape(displaypath)}</title><style>html{{font-size:32px}} body{{margin:16px}} li{{line-height:1.6}} a,button,input{{font-size:1em}}</style></head>".encode('utf-8'))
        f.write(b"<body>")
        f.write(f"<h2>Index of {html.escape(displaypath)}</h2>".encode('utf-8'))
        f.write(b"<div>")
        f.write(b"<form method='POST' enctype='multipart/form-data'>")
        f.write(b"<input id='fileInput' type='file' name='file' multiple required> ")
        f.write("<button id='uploadBtn' type='submit' disabled>上传文件</button>".encode('utf-8'))
        f.write(b"</form>")
        f.write(b"<script>")
        f.write(b"const input=document.getElementById('fileInput');const btn=document.getElementById('uploadBtn');function sync(){btn.disabled=!(input.files&&input.files.length>0);}input.addEventListener('change',sync);sync();document.querySelector('form').addEventListener('submit',e=>{if(btn.disabled){e.preventDefault();}});")
        f.write(b"</script>")
        f.write(b"</div>")
        f.write(b"<hr><ul>")
        if displaypath != '/':
            f.write(b"<li><a href='../'>../</a></li>")
        for name in entries:
            fullname = os.path.join(path, name)
            isdir = os.path.isdir(fullname)
            display_name = name + ('/' if isdir else '')
            linkname = name + ('/' if isdir else '')
            href = urllib.parse.quote(linkname)
            f.write(f"<li><a href='{href}'>{html.escape(display_name)}</a></li>".encode('utf-8'))
        f.write(b"</ul><hr>")
        f.write(b"</body></html>")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def do_POST(self):
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type or 'boundary=' not in content_type:
            self.send_error(400, "Unsupported Content-Type")
            return
        boundary = content_type.split('boundary=', 1)[1].strip().strip('"')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = 0
        data = self.rfile.read(length)
        boundary_bytes = ("--" + boundary).encode('utf-8')
        parts = data.split(boundary_bytes)
        save_dir = self.translate_path(self.path)
        if not os.path.isdir(save_dir):
            save_dir = os.path.dirname(save_dir)

        def unique_target(dirpath, filename):
            base = os.path.basename(filename)
            return os.path.join(dirpath, base)

        files_to_save = []
        conflicts = []

        for part in parts:
            if not part or part.startswith(b"--"):
                continue
            part = part.lstrip(b"\r\n")
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            head = part[:header_end].decode('utf-8', errors='ignore')
            body = part[header_end + 4:]
            body = body.rstrip(b"\r\n")
            headers = head.split("\r\n")
            cd_val = ''
            ct_val = ''
            for line in headers:
                l = line.lower()
                if l.startswith('content-disposition:'):
                    cd_val = line.split(':', 1)[1].strip()
                elif l.startswith('content-type:'):
                    ct_val = line.split(':', 1)[1].strip()
            if cd_val:
                params = {}
                for seg in cd_val.split(';'):
                    seg = seg.strip()
                    if '=' in seg:
                        k, v = seg.split('=', 1)
                        params[k.strip().lower()] = v.strip().strip('"')
                    else:
                        params[seg.strip().lower()] = ''
                if params.get('name') != 'file':
                    continue
                filename = None
                if 'filename*' in params:
                    v = params['filename*']
                    if "''" in v:
                        filename = urllib.parse.unquote(v.split("''", 1)[1])
                    else:
                        filename = urllib.parse.unquote(v)
                elif 'filename' in params:
                    filename = params['filename']
                if filename:
                    filename = os.path.basename(filename.replace('\\', '/')).strip()
                    if not filename:
                        filename = None
                if not filename:
                    filename = f"upload_{int(time.time()*1000)}"
                target = unique_target(save_dir, filename)
                if os.path.exists(target):
                    conflicts.append(filename)
                else:
                    files_to_save.append((target, body))

        if conflicts:
            msg = "文件已存在: " + ", ".join([html.escape(x) for x in conflicts])
            page = f"""
<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>Conflict</title></head>
<body>
<h3>{msg}</h3>
<p><a href='{html.escape(self.path)}'>返回目录</a></p>
</body></html>
""".encode('utf-8')
            self.send_response(409)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        saved = []
        for target, body in files_to_save:
            with open(target, 'wb') as out:
                out.write(body)
            saved.append(os.path.basename(target))

        host = self.headers.get('Host', '')
        base = self.path
        if not base.endswith('/'):
            base = base + '/'
        urls = []
        for name in saved:
            urls.append(f"http://{host}{base}{urllib.parse.quote(name)}")
        page = ("<!DOCTYPE html><html><head><meta charset='utf-8'><title>Uploaded</title></head><body>" +
                ("<h3>Uploaded:</h3><ul>" + "".join([f"<li><a href='" + u + "'>" + html.escape(u) + "</a></li>" for u in urls]) + "</ul>") +
                f"<p><a href='{html.escape(self.path)}'>返回目录</a></p>" +
                "</body></html>").encode('utf-8')

        self.send_response(201)
        if urls:
            self.send_header('Location', urls[0])
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

def get_ip_address():
    try:
        # 获取本机局域网IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def run_server():
    # 切换到当前脚本所在目录，确保提供的文件是相对于脚本的
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    Handler = CustomHandler
    
    # 使用 ThreadingTCPServer 支持并发请求
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
        ip = get_ip_address()
        print(f"Serving HTTP on 0.0.0.0 port {PORT} (http://0.0.0.0:{PORT}/) ...")
        print(f"Local Network URL: http://{ip}:{PORT}/")
        print(f"Access 'images' directory: http://{ip}:{PORT}/images/")
        print(f"Access 'audio' directory: http://{ip}:{PORT}/audio/")
        print("Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()
