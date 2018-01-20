import os
import sys
from PIL import Image,ImageFilter,ImageDraw
import numpy as np
import time
import random
import math
import json
import re



def _get_screen_size():
    size_str = os.popen('adb shell wm size').read()
    m = re.search('(\d+)x(\d+)', size_str)
    if m:
        width = m.group(1)
        height = m.group(2)
        return "{height}x{width}".format(height=height, width=width)

def open_accordant_config():
    screen_size = _get_screen_size()
    config_file = "{path}/config/{screen_size}/config.json".format(
        path=sys.path[0],
        screen_size=screen_size
    )
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            # print("Load config file from {}".format(config_file))
            return json.load(f)
    else:
        with open('{}/config/default.json'.format(sys.path[0]), 'r') as f:
            # print("Load default config")
            return json.load(f)

config = open_accordant_config()

# Magic Number，不设置可能无法正常执行，请根据具体截图从上到下按需设置
under_game_score_y = config['under_game_score_y']
press_coefficient = config['press_coefficient']       # 长按的时间系数，请自己根据实际情况调节
piece_base_height_1_2 = config['piece_base_height_1_2']   # 二分之一的棋子底座高度，可能要调节
piece_body_width = config['piece_body_width']             # 棋子的宽度，比截图中量到的稍微大一点比较安全，可能要调节

def get_screenshot():
    os.system('adb shell screencap -p /sdcard/autojump.png')
    os.system('adb pull /sdcard/autojump.png .')

def game_over(im):
    pixels = im.load()
    point = pixels[0,0]
    print(point)
    if (30<point[0]<55) and (30<point[1]<55) and (30<point[2]<55):
        return True
    return False

def find_piece_x(im):
    w, h = im.size

    piece_x_sum = 0
    piece_x_c = 0
    piece_y_max = 0
    scan_x_border = int(w / 8)  # 扫描棋子时的左右边界
    scan_start_y = 0  # 扫描的起始y坐标
    im_pixel=im.load()
    # 以50px步长，尝试探测scan_start_y
    for i in range(int(h / 3), int( h*2 /3 ), 50):
        last_pixel = im_pixel[0,i]
        for j in range(1, w):
            pixel=im_pixel[j,i]
            # 不是纯色的线，则记录scan_start_y的值，准备跳出循环
            if pixel[0] != last_pixel[0] or pixel[1] != last_pixel[1] or pixel[2] != last_pixel[2]:
                scan_start_y = i - 50
                break
        if scan_start_y:
            break
    # print('scan_start_y: ', scan_start_y)

    # 从scan_start_y开始往下扫描，棋子应位于屏幕上半部分，这里暂定不超过2/3
    for i in range(scan_start_y, int(h * 2 / 3)):
        for j in range(scan_x_border, w - scan_x_border):  # 横坐标方面也减少了一部分扫描开销
            pixel = im_pixel[j,i]
            # 根据棋子的最低行的颜色判断，找最后一行那些点的平均值，这个颜色这样应该 OK，暂时不提出来
            if (50 < pixel[0] < 60) and (53 < pixel[1] < 63) and (95 < pixel[2] < 110):
                piece_x_sum += j
                piece_x_c += 1
                piece_y_max = max(i, piece_y_max)

    if not all((piece_x_sum, piece_x_c)):
        return 0
    piece_x = piece_x_sum / piece_x_c
    return int(piece_x)

def find_board_x(im):
    w, h = im.size
    conF = im.filter(ImageFilter.CONTOUR)
    L = conF.convert('L')
    # L.show()

    for j in range(int(h / 3),int(h * 2 / 3)):
        for i in range(w):
            r = L.getpixel((i,j))
            if r<200:
                # print(i,j)
                return i
    return 0
def find_piece_and_board(im):
    w, h = im.size

    piece_x_sum = 0
    piece_x_c = 0
    piece_y_max = 0
    board_x = 0
    board_y = 0
    scan_x_border = int(w / 8)  # 扫描棋子时的左右边界
    scan_start_y = 0  # 扫描的起始y坐标
    im_pixel=im.load()
    # 以50px步长，尝试探测scan_start_y
    for i in range(int(h / 3), int( h*2 /3 ), 50):
        last_pixel = im_pixel[0,i]
        for j in range(1, w):
            pixel=im_pixel[j,i]
            # 不是纯色的线，则记录scan_start_y的值，准备跳出循环
            if pixel[0] != last_pixel[0] or pixel[1] != last_pixel[1] or pixel[2] != last_pixel[2]:
                scan_start_y = i - 50
                break
        if scan_start_y:
            break
    # print('scan_start_y: ', scan_start_y)

    # 从scan_start_y开始往下扫描，棋子应位于屏幕上半部分，这里暂定不超过2/3
    for i in range(scan_start_y, int(h * 2 / 3)):
        for j in range(scan_x_border, w - scan_x_border):  # 横坐标方面也减少了一部分扫描开销
            pixel = im_pixel[j,i]
            # 根据棋子的最低行的颜色判断，找最后一行那些点的平均值，这个颜色这样应该 OK，暂时不提出来
            if (50 < pixel[0] < 60) and (53 < pixel[1] < 63) and (95 < pixel[2] < 110):
                piece_x_sum += j
                piece_x_c += 1
                piece_y_max = max(i, piece_y_max)

    if not all((piece_x_sum, piece_x_c)):
        return 0, 0, 0, 0
    piece_x = piece_x_sum / piece_x_c
    piece_y = piece_y_max - piece_base_height_1_2  # 上移棋子底盘高度的一半

    for i in range(int(h / 3), int(h * 2 / 3)):
        last_pixel = im_pixel[0, i]
        if board_x or board_y:
            break
        board_x_sum = 0
        board_x_c = 0

        for j in range(w):
            pixel = im_pixel[j,i]
            # 修掉脑袋比下一个小格子还高的情况的 bug
            if abs(j - piece_x) < piece_body_width:
                continue

            # 修掉圆顶的时候一条线导致的小 bug，这个颜色判断应该 OK，暂时不提出来
            if abs(pixel[0] - last_pixel[0]) + abs(pixel[1] - last_pixel[1]) + abs(pixel[2] - last_pixel[2]) > 10:
                board_x_sum += j
                board_x_c += 1
        if board_x_sum:
            board_x = board_x_sum / board_x_c
    # 按实际的角度来算，找到接近下一个 board 中心的坐标 这里的角度应该是30°,值应该是tan 30°, math.sqrt(3) / 3
    board_y = piece_y - abs(board_x - piece_x) * math.sqrt(3) / 3

    if not all((board_x, board_y)):
        return 0, 0, 0, 0

    return piece_x, piece_y, board_x, board_y
def getMaxQ(state,Q):
    return max(Q[state,:])

def getMaxQ_index(Q):
    index = np.argwhere(Q == max(Q[:]))
    # print(index[0][0])
    return index[0][0]

def q_learning(Q,GAMMA,init_action):
    # for i in range(episode):
    while True:

        get_screenshot()
        im = Image.open('./autojump.png')
        piece_x, piece_y, board_x, board_y = find_piece_and_board(im)
        dist = int(math.sqrt((board_x - piece_x) ** 2 + (board_y - piece_y) ** 2))
        press_time = 0
        # if dist%10 > 4:
        #     distance = int(dist/10) + 1
        # else:
        distance = int(dist/10)
        vaild_action = []
        for i in range(6, 41):
            if Q[distance][i] != -50:
                vaild_action.append(i)
        # print(vaild_action)
        if getMaxQ(distance,Q) == 0:
            if vaild_action != []:
                press_time = random.choice(vaild_action) * 25
            else:
                press_time = random.choice(init_action) * 25
        else:
            # print(np.argwhere(Q == getMaxQ(distance,Q)))
            # press_time = np.argwhere(Q == getMaxQ(distance,Q))[0][1] * 50
            press_time = getMaxQ_index(Q[distance]) * 25
            #print(press_time)
        # print('press_time:', press_time/50)
        # print('distance:',distance)
        os.system('adb shell input swipe 20 20 21 21 {time}'.format(time=press_time))
        time.sleep(4)
        #
        get_screenshot()
        im = Image.open('./autojump.png')
        if game_over(im):
            Q[distance][int(press_time / 25)] = -50 + GAMMA * getMaxQ(distance,Q)
            # print('score:',Q[distance][int(press_time / 50)])
            break
        else:
            Q[distance][int(press_time/25)] = 10 + GAMMA * getMaxQ(distance,Q)
            # print('score:',Q[distance][int(press_time / 50)])

def retry_button(w,h):
    left = w / 2
    top = 1003 * (h / 1280.0) + 10
    cmd = 'adb shell input swipe {x1} {y1} {x2} {y2} {duration}'.format(
        x1=left,
        y1=top,
        x2=left,
        y2=top,
        duration=100
    )
    os.system(cmd)



def train(episode,w,h):
    init_action = [i for i in range(1,41)]
    if os.path.exists("Qarray.txt"):
        Q = np.loadtxt("Qarray.txt")
        print("load Qarray.txt")
    else:
        # print(e)
        Q = np.zeros((int(w/10)+1,41))

    print(Q)
    for i in range(episode):
        print(i,'episode')
        q_learning(Q, 0.8,init_action)
        retry_button(w,h)
        time.sleep(1)
        np.savetxt("Qarray.txt",Q)

train(500,720,1280)
    # return 0
# get_screenshot()
# im = Image.open('./autojump.png')
# x = find_piece_x(im)
# i,j = find_boaOKzrd_x(im)
# draw = ImageDraw.Draw(im)
# draw.line((piece_x, piece_y) + (board_x, board_y), fill=2, width=3)
# draw.line((i, 0, i, im.size[1]), fill=(255, 0, 0))
# draw.line((0, j, im.size[0], j), fill=(255, 0, 0))
# draw.line((x, 0, x, im.size[1]), fill=(0, 0, 255))
# # draw.line((0, board_y, im.size[0], board_y), fill=(0, 0, 255))
# draw.ellipse((i - 10, j - 10, i + 10, j + 10), fill=(0, 0, 255))
# draw.ellipse((x - 10, j - 10, x + 10, j + 10), fill=(0, 0, 255))
# im.show()

# # print(int(w/10),h)

#
# print(Q)
# print(game_over(im))
# dist = abs(find_piece_x(im)-find_board_x(im))
# print(int(dist/10),dist%10)

# os.system('adb shell input swipe 20 20 21 21 500')