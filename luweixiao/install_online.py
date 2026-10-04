"""HTTPS bootstrap for Stata installations whose native download returns r(603).

Execute this public script once in Stata's configured Python. It verifies all
runtime files, then delegates installation to Stata's normal PLUS mechanism.
"""


def install():
    import hashlib
    from pathlib import Path
    import re
    import tempfile
    import urllib.request
    from sfi import SFIToolkit

    base = 'https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luwx/'
    runtime = ('luwx.ado', 'luwx.sthlp', 'luwx_bridge.py', 'luwx_api.py',
               'luwx_settings.py', 'luwx_evidence.py',
               'luweixiao.ado', 'luweixiao.sthlp')
    required = ('luwx.pkg', 'stata.toc') + runtime
    limit = 2 * 1024 * 1024

    def fetch(name):
        url = base + name
        with urllib.request.urlopen(url, timeout=30) as response:
            if response.geturl() != url:
                raise ValueError('安装下载地址发生跳转，已停止安装。')
            value = response.read(limit + 1)
        if len(value) > limit:
            raise ValueError('安装文件超过允许大小，已停止安装。')
        return value

    hashes = {}
    try:
        manifest = fetch('MANIFEST_SHA256.txt').decode('utf-8-sig')
        for line in manifest.splitlines():
            if not line.strip():
                continue
            match = re.fullmatch(r'([0-9a-fA-F]{64})  ([A-Za-z0-9_.-]+)', line.strip())
            if not match or match.group(2) in hashes:
                raise ValueError('SHA256清单格式无效，已停止安装。')
            hashes[match.group(2)] = match.group(1).lower()
        if any(name not in hashes for name in required):
            raise ValueError('SHA256清单缺少运行文件，已停止安装。')
        files = {}
        for name in required:
            value = fetch(name)
            if hashlib.sha256(value).hexdigest() != hashes[name]:
                raise ValueError('SHA256校验失败：' + name + '；未安装。')
            files[name] = value

        package_files = []
        version_count = 0
        for line in files['luwx.pkg'].decode('utf-8-sig').splitlines():
            if not line.strip():
                continue
            record = line.strip().split(None, 1)
            if record == ['v', '3']:
                version_count += 1
            elif len(record) == 2 and record[0] == 'd':
                continue
            elif len(record) == 2 and record[0] == 'f' and record[1] in runtime:
                package_files.append(record[1])
            else:
                raise ValueError('luwx.pkg含非预期安装记录，已停止安装。')
        if version_count != 1 or len(package_files) != len(runtime) or set(package_files) != set(runtime):
            raise ValueError('luwx.pkg运行文件清单不匹配，已停止安装。')
    except UnicodeError:
        raise ValueError('安装清单不是有效UTF-8文本，已停止安装。') from None

    with tempfile.TemporaryDirectory(prefix='luwx-online-') as folder:
        source = Path(folder)
        path = source.as_posix()
        if any(char in path for char in ('"', '`', '$', '\r', '\n')):
            raise ValueError('临时目录包含Stata特殊字符；请改用ZIP安装。')
        for name, value in files.items():
            (source / name).write_bytes(value)
        # All 10 public files are verified before this first installation call.
        SFIToolkit.stata('net install luwx, from("' + path + '") replace', echo=False)
    SFIToolkit.display('luwx安装完成。请重启Stata；每位同学配置自己的API。\n', asis=True)


# Stata's one-line exec may run outside __main__; install exactly once here.
install()
del install
