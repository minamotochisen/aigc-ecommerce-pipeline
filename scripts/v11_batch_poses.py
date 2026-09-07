# -*- coding: utf-8 -*-
"""V11 批次: 姿态宫格重拍 (影棚无缝背景解耦) handonhip/walking/side/back/stand34 x2 seeds"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_api
import v10_qwen2511 as v10

POSES = {
    "handonhip": [92310, 92311],
    "walking":   [92320, 92321],
    "side":      [92330, 92331, 92332],
    "front":     [92340, 92341],
    "stand34":   [92350, 92351],
}


def main():
    comfy_api.wait_server()
    for key, seeds in POSES.items():
        for s in seeds:
            v10.run_seeds("pose", [(key, s)])


if __name__ == "__main__":
    main()
