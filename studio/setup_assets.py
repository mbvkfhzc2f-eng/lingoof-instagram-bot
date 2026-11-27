#!/usr/bin/env python3
"""Stüdyo varlıklarını uygulamanın (özel) iOS deposundan hazırlar; bu dosyalar herkese açık bot deposuna konmaz.

  goof/<poz>.png        Goof pozları (Assets.xcassets, @3x)
  fonts/*.ttf           Bricolage Grotesque (uygulamanın yazı tipi)
  shots/screen_*.png    App Store ekran görüntülerinden kırpılmış uygulama ekranları (ürün Reels'i için)

Kullanım: python3 setup_assets.py /yol/lingoof-ios
"""
import shutil
import sys
from pathlib import Path

from PIL import Image

STUDIO = Path(__file__).resolve().parent
POSES = ['goof_alert', 'goof_avatar', 'goof_calm', 'goof_celebrate', 'goof_focus', 'goof_hype', 'goof_oops', 'goof_proud', 'goof_sleepy',
         'goof_pose_card', 'goof_pose_celebrate', 'goof_pose_facepalm', 'goof_pose_jump', 'goof_pose_lean_in', 'goof_pose_look_down',
         'goof_pose_look_up', 'goof_pose_neutral', 'goof_pose_peek', 'goof_pose_point_left', 'goof_pose_point_right', 'goof_pose_sleep',
         'goof_base_3q', 'goof_base_front']
SCREENS = {'screen_hata.png': '01_hata_yap_goof_aciklasin.png', 'screen_home.png': '02_gunde_5_dakika.png',
           'screen_progress.png': '04_gercek_ilerleme.png'}


def main():
    ios = Path(sys.argv[1])
    (STUDIO / 'goof').mkdir(exist_ok=True)
    missing = []
    for p in POSES:
        src = None
        for scale in ('@3x', '@2x', ''):
            c = ios / 'LINGOOF' / 'Assets.xcassets' / f'{p}.imageset' / f'{p}{scale}.png'
            if c.exists():
                src = c
                break
        if not src:
            missing.append(p)
            continue
        im = Image.open(src).convert('RGBA')
        if p != 'goof_avatar' and im.width != 768:
            im = im.resize((768, 768), Image.LANCZOS)
        im.save(STUDIO / 'goof' / f'{p}.png')
    (STUDIO / 'fonts').mkdir(exist_ok=True)
    for f in ('BricolageGrotesque-Bold.ttf', 'BricolageGrotesque-ExtraBold.ttf'):
        shutil.copy2(ios / 'LINGOOF' / 'Resources' / 'Fonts' / f, STUDIO / 'fonts' / f)
    (STUDIO / 'shots').mkdir(exist_ok=True)
    for dst, src in SCREENS.items():
        im = Image.open(ios / 'AppStore' / 'Screenshots_6.9in' / src).convert('RGB')
        im.crop((197, 812, 1123, 812 + 1890)).save(STUDIO / 'shots' / dst)   # telefon çerçevesinin içindeki ekran
    print('hazır' + (f' (eksik pozlar: {missing})' if missing else ''))


if __name__ == '__main__':
    main()
