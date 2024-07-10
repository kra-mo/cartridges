# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ["../../_build/cartridges/cartridges"],
    pathex=[],
    binaries=[],
    datas=[("../../_build/data/cartridges.gresource", "Resources")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={
        "gi": {
            "module-versions": {
                "Gtk": "4.0",
            },
        },
    },
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Cartridges",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Cartridges",
)
app = BUNDLE(
    coll,
    name="Cartridges.app",
    icon="./icon.icns",
    bundle_identifier="page.kramo.Cartridges",
    info_plist={
        "LSApplicationCategoryType": "public.app-category.games",
    },
)
