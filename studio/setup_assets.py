#!/usr/bin/env python3
"""Stüdyo varlıklarını uygulamanın kaynağından hazırlar; bu dosyalar herkese açık bot deposuna konmaz.

  goof/<poz>.png        Goof 2.0 pozları, karakter avatarları (char_*) ve sahne çizimleri (scene_*), @3x
  fonts/*.ttf           Bricolage Grotesque (uygulamanın başlık yazı tipi)

Kaynak, içinde LINGOOF/Assets.xcassets bulunan klasördür: en güncel build'in "Kaynak" klasörü
(ör. LINGOOF-1_2_2-140-Optimize-Teslim.zip içindeki Kaynak/) ya da güncel iOS deposu.

Kullanım: python3 setup_assets.py /yol/Kaynak
"""
import shutil
import sys
from pathlib import Path

from PIL import Image

STUDIO = Path(__file__).resolve().parent
POSES = ['goof_alert', 'goof_avatar', 'goof_calm', 'goof_celebrate', 'goof_focus', 'goof_hype', 'goof_oops', 'goof_proud', 'goof_sleepy',
         'goof_laugh', 'goof_love', 'goof_sad', 'goof_shy', 'goof_think', 'goof_thumbs_up', 'goof_wave', 'goof_wink', 'goof_penpal',
         'goof_pose_card', 'goof_pose_card_blank', 'goof_pose_celebrate', 'goof_pose_facepalm', 'goof_pose_jump', 'goof_pose_lean_in',
         'goof_pose_look_down', 'goof_pose_look_up', 'goof_pose_neutral', 'goof_pose_peek', 'goof_pose_point_left', 'goof_pose_point_right',
         'goof_pose_sleep', 'goof_base_3q', 'goof_base_front',
         'char_alex', 'char_emma', 'char_leo', 'char_maya', 'char_nina', 'char_sofia', 'char_role_a', 'char_role_b', 'char_role_c', 'char_role_d',
         'scene_career', 'scene_daily', 'scene_dating', 'scene_internet', 'scene_social', 'scene_travel', 'scene_university']


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
        im.save(STUDIO / 'goof' / f'{p}.png')
    (STUDIO / 'fonts').mkdir(exist_ok=True)
    for f in ('BricolageGrotesque-Bold.ttf', 'BricolageGrotesque-ExtraBold.ttf'):
        shutil.copy2(ios / 'LINGOOF' / 'Resources' / 'Fonts' / f, STUDIO / 'fonts' / f)
    print('hazır' + (f' (eksik pozlar: {missing})' if missing else ''))


if __name__ == '__main__':
    main()
