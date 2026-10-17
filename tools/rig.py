# -*- coding: utf-8 -*-
"""姜林角色姿态装配：白衬衫/黑西裤/皮鞋，拼成“狗爬”和“磕头”。
零件全部取自 chars/jianglin/_work/cutout.png（工作图 880x1184）。
"""
import math
import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "build")
SRC = Image.open(os.path.join(WORK, "cutout.png")).convert("RGBA")   # 由 tools/cutout.py 生成
# 清掉右下角水印残留
_w, _h = SRC.size
_a = np.array(SRC)
_a[max(0, _h - 80):, max(0, _w - 220):, 3] = 0
SRC = Image.fromarray(_a, "RGBA")


def fill_holes(img):
    a = np.array(img)
    alpha = a[:, :, 3]
    m = (alpha > 40).astype(np.uint8)
    h, w = m.shape
    ff = m.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    holes = (~ff.astype(bool)) & (m == 0)
    if holes.any():
        bgr = cv2.inpaint(cv2.cvtColor(a[:, :, :3], cv2.COLOR_RGB2BGR), holes.astype(np.uint8) * 255, 3, cv2.INPAINT_TELEA)
        a[:, :, :3] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        alpha[holes] = 255
    return Image.fromarray(a)


def dark(im, f):
    a = np.array(im).astype(np.float32)
    a[..., :3] *= f
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def fade_top(im, px):
    w, h = im.size
    g = Image.new("L", (1, h), 255)
    for y in range(min(px, h)):
        g.putpixel((0, y), int(255 * (y / max(1, px)) ** 0.7))
    g = g.resize((w, h)).filter(ImageFilter.GaussianBlur(3))
    a = np.array(im)
    a[:, :, 3] = (a[:, :, 3].astype(np.float32) * np.array(g).astype(np.float32) / 255).astype(np.uint8)
    return Image.fromarray(a)


def head_piece():
    im = fill_holes(SRC.crop((348, 52, 508, 242)))        # 160x190 头 + 下巴一点脖子
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse((2, -10, im.size[0] - 2, im.size[1] + 2), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(4))
    base = im.getchannel("A").point(lambda v: 255 if v > 60 else 0)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0),
                                Image.composite(m, Image.new("L", im.size, 0), base)))
    return im


# 衬衫要“向右转 90°”再铺到躯干上（领口朝前/朝头），否则会竖着贴在狗身体里
SHIRT_TEX = fill_holes(SRC.crop((345, 300, 520, 475))).rotate(-90, expand=True, resample=Image.BICUBIC)
# 屁股只用纯裤料（大腿中段），避开皮带/裤裆——否则看着像“下半身装反了”
PANTS_TEX = fill_holes(SRC.crop((322, 660, 500, 906))).rotate(-90, expand=True, resample=Image.BICUBIC)
HEAD = head_piece().transpose(Image.FLIP_LEFT_RIGHT)            # 头水平翻转
ARM = fill_holes(SRC.crop((268, 300, 352, 644)))                # 84x344 短袖+前臂+手
LEG = fill_holes(SRC.crop((298, 620, 452, 1144))).transpose(Image.FLIP_LEFT_RIGHT)   # 154x524 腿（翻转）

W, H = 820, 500
GROUND = 432
BH = 150
BW = 320
HIP_X = 196
BODY_TOP = GROUND - 110 - BH
BODY_BOT = BODY_TOP + BH
SHO_X = HIP_X + BW

LEG_TOP = BODY_BOT - 56
LEG_H = GROUND - LEG_TOP
leg = fade_top(LEG.resize((64, LEG_H), Image.LANCZOS), int(LEG_H * 0.24))
ARM_TOP = BODY_BOT - 66
ARM_H = GROUND - ARM_TOP
arm = fade_top(ARM.resize((62, ARM_H), Image.LANCZOS), int(ARM_H * 0.26))
AW, AH = arm.size
LW, LH = leg.size

HEAD_H = int(BH * 1.34)
head = HEAD.resize((int(BH * 1.16), HEAD_H), Image.LANCZOS)
HW, HH = head.size
HX = SHO_X - int(HW * 0.56)
HY = BODY_TOP - int(BH * 0.20)


def body_layer():
    front_w = int(BW * 0.52)                 # 右段 = 前身（衬衫，靠近头）
    back_w = BW - front_w                    # 左段 = 屁股（黑西裤）
    strip = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    strip.alpha_composite(PANTS_TEX.resize((back_w, BH), Image.LANCZOS), (0, 0))
    strip.alpha_composite(dark(SHIRT_TEX, 0.97).resize((front_w, BH), Image.LANCZOS), (back_w, 0))
    m = Image.new("L", (BW * 2, BH * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, BW * 2 - 1, BH * 2 - 1), BH, fill=255)
    m = m.resize((BW, BH), Image.LANCZOS)
    strip.putalpha(m)
    return strip


BODY = body_layer()
print("body", (BW, BH), "arm", (AW, AH), "leg", (LW, LH), "head", (HW, HH))


def put(canvas, im, angle, top_left):
    r = im.rotate(angle, expand=True, resample=Image.BICUBIC) if angle else im
    canvas.alpha_composite(r, (int(top_left[0] - (r.size[0] - im.size[0]) / 2),
                               int(top_left[1] - (r.size[1] - im.size[1]) / 2)))
    return r


def scene(pose="crawl", t=0.0, dbg=False):
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((HIP_X - 60, GROUND - 10, SHO_X + 90, GROUND + 26), fill=(15, 15, 20, 110))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(12)))

    if pose == "crawl":
        sw = math.cos(2 * math.pi * t)
        arm_n = (SHO_X - int(AW * 1.34), ARM_TOP + 2 + 8 * sw)
        arm_f = (SHO_X - int(AW * 1.72), ARM_TOP - 2 - 8 * sw)
        leg_n = (HIP_X + int(BW * 0.16), LEG_TOP + 2 - 8 * sw)
        leg_f = (HIP_X - int(BW * 0.02), LEG_TOP - 2 + 8 * sw)
        a_arm_n, a_arm_f = 6 + 12 * sw, 6 - 12 * sw
        a_leg_n, a_leg_f = 6 - 10 * sw, 6 + 10 * sw
        hx, hy, hang = HX, HY, 4
        body_top = BODY_TOP
    else:
        # 磕头：躯干整体倾斜（前低后高、屁股翘起），头砸到地面上
        tilt = -13
        arm_n = (SHO_X - int(AW * 0.50), BODY_BOT - 6)
        arm_f = (SHO_X - int(AW * 0.86), BODY_BOT - 10)
        leg_n = (HIP_X + int(BW * 0.10), BODY_BOT - 62)
        leg_f = (HIP_X - int(BW * 0.06), BODY_BOT - 60)
        a_arm_n, a_arm_f = -86, -78
        a_leg_n, a_leg_f = 78, 90
        hx, hy = HX + 6, GROUND - int(HH * 0.98) + int(10 * t)
        hang = -76 + 12 * t
        body_top = BODY_TOP + 34

    put(canvas, dark(leg, 0.70), a_leg_f, leg_f)
    put(canvas, dark(arm, 0.74), a_arm_f, arm_f)
    put(canvas, leg, a_leg_n, leg_n)
    put(canvas, arm, a_arm_n, arm_n)
    if pose == "crawl":
        canvas.alpha_composite(BODY, (HIP_X, body_top))
    else:
        tr = BODY.rotate(tilt, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(tr, (HIP_X + (BW - tr.size[0]) // 2, body_top + (BH - tr.size[1]) // 2))
    put(canvas, head, hang, (hx, hy))

    if dbg:
        c = canvas.copy()
        d = ImageDraw.Draw(c)
        d.line([(0, GROUND), (W, GROUND)], fill=(255, 0, 0, 255), width=2)
        d.rectangle((HIP_X, body_top, SHO_X, body_top + BH), outline=(0, 0, 255, 255), width=2)
        canvas = c
    return canvas


def sheet(path):
    tiles = [("crawl", 0.0), ("crawl", 0.5), ("kowtow", 0.0), ("kowtow", 1.0)]
    out = Image.new("RGB", (W * 2, H * 2), (240, 240, 242))
    for i, (p, t) in enumerate(tiles):
        im = scene(p, t)
        bg = Image.new("RGBA", (W, H), (240, 240, 242, 255))
        bg.alpha_composite(im)
        out.paste(bg.convert("RGB"), ((i % 2) * W, (i // 2) * H))
        im.save(os.path.join(WORK, "pose_%s_%d.png" % (p, int(t * 100))))
    out.save(path)
    print("saved", path)


if __name__ == "__main__":
    sheet(os.path.join(WORK, "poses.png"))
