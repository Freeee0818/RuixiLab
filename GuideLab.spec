# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: 将 GuideLab 后端 + 前端 dist 打成单 exe
# 使用前请先执行: npm run build（生成 dist/）
# 构建命令（在项目根目录）: pyinstaller GuideLab.spec

import os

# 项目根目录：SPECPATH 可能是 spec 文件路径或包含 spec 的目录，统一为绝对目录
_spec_abs = os.path.abspath(SPECPATH)
PROJECT_ROOT = os.path.dirname(_spec_abs) if os.path.isfile(_spec_abs) else _spec_abs

# 绝对路径，避免因工作目录或 SPECPATH 语义导致找错目录
SCRIPT_PATH = os.path.join(PROJECT_ROOT, 'pysr_module', 'main.py')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DIST_DIR_ABS = os.path.join(PROJECT_ROOT, 'dist')
DIST_INDEX_ABS = os.path.join(DIST_DIR_ABS, 'index.html')

# 要打进 exe 的数据：config 必选；dist 为前端构建产物，存在则一并打入
datas = [(CONFIG_DIR, 'config')]
if os.path.isdir(DIST_DIR_ABS) and os.path.isfile(DIST_INDEX_ABS):
    datas.append((DIST_DIR_ABS, 'dist'))
else:
    print('警告: 未找到 dist/ 或 dist/index.html，将只打包 API（无前端页面）。请先执行 npm run build。')

block_cipher = None

a = Analysis(
    [SCRIPT_PATH],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'pydantic',
        'pydantic_settings',
        'multipart',
        'httpx',
        'anyio',
        'anyio._backends._asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GuideLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # 保留控制台，便于看到服务地址和日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
