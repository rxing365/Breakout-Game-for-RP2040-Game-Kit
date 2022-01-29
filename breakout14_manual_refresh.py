import time
import board
import busio
import bitmaptools
import breakout_audio
import terminalio
import displayio
import math
from analogio import AnalogIn
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.circle import Circle
from adafruit_st7789 import ST7789
from digitalio import DigitalInOut, Direction, Pull

displayio.release_displays()

stick_y = AnalogIn(board.A2)
stick_x = AnalogIn(board.A3)

btn_a = DigitalInOut(board.GP6)
btn_a.direction = Direction.INPUT
btn_a.pull = Pull.UP

btn_b = DigitalInOut(board.GP5)
btn_b.direction = Direction.INPUT
btn_b.pull = Pull.UP



game_mode = "start"
game_tick = 0

ball_color = 0xFF00FF
pad_color = 0x00FF00
stat_bar_color = 0x1F3809
title_color = 0xFFFF00
game_over_bg_c = 0x141452

font = terminalio.FONT

screen_width = 240
screen_height = 240

pad_x = 100
pad_y = 225
pad_w = 70  # 50 Default
pad_h = 8
pad_dx = 0.0
pad_dy = 0.0
next_x = 0
next_y = 0

ball_radius = 5
ball_x = pad_x + math.floor(pad_w / 2)
ball_y = pad_y - ball_radius
ball_dx = 4
ball_dy = -4
ball_ang = 1
sticky = True

lives = 3
points = 0

stick_px = 0
stick_py = 0
stick_s = 0.7  # joystick灵敏度，数值越小越灵敏，0 < stick_s < 1.64

# 初始化屏幕
spi = busio.SPI(clock=board.GP2, MOSI=board.GP3)
tft_cs = board.GP18
tft_dc = board.GP1

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP0)

display = ST7789(display_bus, width=240, height=240, rowstart=80, rotation=180)
display.auto_refresh = False


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


# 初始化摇杆
stick_y_origin = get_voltage(stick_y)
stick_x_origin = get_voltage(stick_x)


def up():
    if -(get_voltage(stick_y) - stick_y_origin) > stick_s:
        return True
    else:
        return False


def down():
    if -(get_voltage(stick_y) - stick_y_origin) < -stick_s:
        return True
    else:
        return False


def left():
    if -(get_voltage(stick_x) - stick_x_origin) < -stick_s:
        return True
    else:
        return False


def right():
    if -(get_voltage(stick_x) - stick_x_origin) > stick_s:
        return True
    else:
        return False


# 初始化音频
game_audio = breakout_audio.GameAudio()

# 开始屏幕
title = label.Label(font, text="BREAKOUT", color=title_color)
title.x = 35
title.y = 40
comment = label.Label(font, text="PRESS A TO START", color=title_color)
comment.x = 35
comment.y = 100
display_start_text = displayio.Group(scale=1)
display_start_text.append(title)
display_start_text.append(comment)

# 游戏相关界面显示
display_all = displayio.Group()

def init_bricks():
    for i in range(0, 20):
        brick_x.append(10+((i % 5) * (brick_w + 3)))
        brick_y.append(35 + math.floor(i / 5) * (brick_h + 4))
        brick_v.append(True)


# 初始化砖块
brick_x = []
brick_y = []
brick_w = 42
brick_h = 12
brick_v = []

palette = displayio.Palette(2)
palette[0] = 0x000000
palette[1] = 0xffffff
bricks = displayio.Bitmap(240, 240, 1)
bricks_grid = displayio.TileGrid(bricks, pixel_shader=palette)
display_all.append(bricks_grid)
init_bricks()

# 初始化小球
ball = Circle(ball_x, ball_y, ball_radius, fill=ball_color, outline=ball_color)
display_all.append(ball)

# 初始化球拍
pad = Rect(pad_x, pad_y, pad_w, pad_h, fill=pad_color)
display_all.append(pad)

# 初始化统计条
stat_bar = Rect(0, 0, screen_width, 14, fill=stat_bar_color)
display_all.append(stat_bar)
live_count = label.Label(font, text=("LIVES: " + str(lives) + " "), color=title_color)
live_count.x = 0
live_count.y = 6
display_all.append(live_count)
point_count = label.Label(font, text=("SCORES: " + str(points) + " "), color=title_color)
point_count.x = 120
point_count.y = 6
display_all.append(point_count)

# 初始化游戏结束画面
game_over_bg = Rect(0, 500, screen_width, 50, fill=game_over_bg_c)
display_all.append(game_over_bg)
game_over_text = label.Label(font, text="Game Over", color=title_color)
game_over_text.x = 0
game_over_text.y = 500
display_all.append(game_over_text)


def ball_hitbox(bx, by, box_x, box_y, box_w, box_h):
    if by - ball_radius > box_y + box_h:
        return False
    if by + ball_radius < box_y:
        return False
    if bx - ball_radius > box_x + box_w:
        return False
    if bx + ball_radius < box_x:
        return False
    return True


def median(data):
    data.sort()
    half = len(data) // 2
    return data[half]


def deflx_ball(bx, by, bdx, bdy, tx, ty, tw, th):
    if bdx == 0:
        return False
    elif bdy == 0:
        return True
    else:
        slp = bdy / bdx
        cx = 0
        cy = 0
        if slp > 0 and bdx > 0:
            cx = tx - bx
            cy = ty - by
            if cx <= 0:
                return False
            if cy == 0:
                return False
            elif (cx / cy) < slp:
                return True
            else:
                return False
        elif slp < 0 and bdx > 0:
            cx = tx - bx
            cy = ty + th - by
            if cx <= 0:
                return False
            elif cy / cx < slp:
                return False
            else:
                return True
        elif slp > 0 and bdx < 0:
            cx = tx + tw - bx
            cy = ty + th - by
            if cx >= 0:
                return False
            elif cy / cx > slp:
                return False
            else:
                return True
        else:
            cx = tx + tw - bx
            cy = ty - by
            if cx >= 0:
                return False
            elif cy / cx < slp:
                return False
            else:
                return True
    return False


def build_bricks():
    global brick_x, brick_y, brick_v
    
    for i in range(0, len(brick_x)):
        bitmaptools.fill_region(bricks, brick_x[i], brick_y[i], brick_x[i] + brick_w, brick_y[i] + brick_h, 1)
        brick_v[i] = True
        

def sign(num):
    if num > 0:
        return 1
    elif num < 0:
        return -1
    else:
        return 0


def set_ang(ang):
    global ball_ang, ball_dx, ball_dy
    
    ball_ang = ang
    if ang == 2:
        ball_dx = 0.5 * 4 * sign(ball_dx)
        ball_dy = 1.3 * 4 * sign(ball_dy)
    elif ang == 0:
        ball_dx = 1.3 * 4 * sign(ball_dx)
        ball_dy = 0.5 * 4 * sign(ball_dy)
    else:
        ball_dx = 4 * sign(ball_dx)
        ball_dy = 4 * sign(ball_dy)


def start_game():
    global ball_x, ball_y, ball_dx, ball_dy, pad_x, pad_y, pad_dx, pad_dy, game_mode, lives, points, brick_v
    
    game_mode = "game"
    lives = 3
    points = 0

    pad_x = 100
    pad_y = 225
    pad_dx = 0.0
    pad_dy = 0.0
    
    build_bricks()
    serve_ball()
    
    live_count.text = "LIVES: " + str(lives) + " "
    point_count.text = "SCORES: " + str(points) + " "


def serve_ball():
    global ball_x, ball_y, ball_dx, ball_dy, sticky
    
    ball_x = pad_x + round(pad_w / 2) - ball_radius
    ball_y = pad_y - (2 * ball_radius) - 1
    ball_dx = 4
    ball_dy = -4
    sticky = True

  
def game_over():
    global game_mode
    game_mode = "game_over"


def draw_game():
    global ball_x, ball_y, ball_dx, ball_dy, pad_x, pad_y, pad_dx, pad_dy, pad_w, pad_h, screen_width, screen_height,\
        lives, points, game_tick, brick_v, sticky
    
    now = time.monotonic()
    if (now - game_tick) > 0.02:
#        print([now, game_tick, now - game_tick])
        game_tick = now
        
        # 移动球拍
        if right():
            pad_dx = -8
            if sticky:
                ball_dx = -4
        if left():
            pad_dx = 8
            if sticky:
                ball_dx = 4
        if not (left() or right()):
            pad_dx = pad_dx / 1.3
        pad_x += round(pad_dx)
        pad_x  = median([0, pad_x, screen_width - pad_w])
        pad.x = pad_x
        
        if sticky:
            if not btn_b.value:
                sticky = False
                bitmaptools.fill_region(bricks, ball_x - 15, ball_y - 15, ball_x + 26, ball_y + 21, 0)
            ball_x = pad_x + round(pad_w / 2) - ball_radius
            ball_y = pad_y - (2 * ball_radius) - 1
        else:
            next_x = ball_x + ball_dx
            next_y = ball_y + ball_dy
        
            # 球体球拍碰撞检测
            if ball_hitbox(next_x, next_y, pad_x, pad_y, pad_w, pad_h):
                if deflx_ball(ball_x, ball_y, ball_dx, ball_dy, pad_x, pad_y, pad_w, pad_h):
                    ball_dx = -ball_dx
                    if ball_x < pad_x + pad_w / 2:
                        next_x = pad_x - ball_radius
                    else:
                        next_x = pad_x + pad_w + ball_radius
                else:
                    ball_dy = -ball_dy
                    if ball_y > pad_y:
                        #与球拍底面碰撞
                        next_y = pad_y + pad_h + ball_radius
                    else:
                        #与球拍顶面碰撞
                        next_y = pad_y - ball_radius
                        if math.fabs(ball_dx) > 3:
                            #改变小球角度
                            if sign(pad_dx) == sign(ball_dx):
                                #低角度
                                set_ang(median([0, ball_ang - 1, 2]))
                            else:
                                #高角度
                                if ball_ang == 2:
                                    ball_dx = -ball_dx
                                else:
                                    set_ang(median([0, ball_ang + 1, 2]))
                                
                points += 1
                #game_audio.sfx(0)
                point_count.text = "SCORES: " + str(points) + " "
            
            # 砖块碰撞检测
            brick_hit = False
            for i in range(0, len(brick_x)):
                if brick_v[i] and ball_hitbox(next_x, next_y, brick_x[i], brick_y[i], brick_w, brick_h):
                    if not brick_hit:
                        if deflx_ball(ball_x, ball_y, ball_dx, ball_dy, brick_x[i], brick_y[i], brick_w, brick_h):
                            ball_dx = -ball_dx
                        else:
                            ball_dy = -ball_dy
                    brick_v[i] = False
                    bitmaptools.fill_region(bricks, brick_x[i], brick_y[i], brick_x[i] + brick_w, brick_y[i] + brick_h, 0)
                    brick_hit = True
                    #game_audio.sfx(0)
                    points += 10
                    point_count.text = "SCORES: " + str(points) + " "

            # 小球与边界碰撞检测
            if (next_x > (screen_width - 2 * ball_radius)) or (next_x < 0):
                next_x = median([0, next_x, (screen_width - 2 * ball_radius)])
                ball_dx = -ball_dx
            if next_y < 14:
                next_y = median([0, next_y, (screen_height - 2 * ball_radius)])
                ball_dy = -ball_dy
            '''
            if next_y > (screen_height - 2 * ball_radius):
                lives -= 1
                ball_dy = -ball_dy
            '''

            ball_x = next_x
            ball_y = next_y
            if ball_y > (screen_height + 10):
                lives -= 1
                if lives == 0:
                    game_over()
                else:
                    serve_ball()
                live_count.text = "LIVES: " + str(lives) + " "
        
        if sticky:
            # 预览小球发射角度
            bitmaptools.fill_region(bricks, ball_x - 15, ball_y - 15, ball_x + 26, ball_y + 21, 0)
            bitmaptools.draw_line(bricks, ball_x + ball_radius + 2 * ball_dx, ball_y + ball_radius + 2 * ball_dy, ball_x + 3 * ball_dx + ball_radius, ball_y + 3 * ball_dy + ball_radius, 1)
        ball.x = round(ball_x)
        ball.y = round(ball_y)

        #    time.sleep(0.005)
    display.show(display_all)


def draw_dev():
    print(-(get_voltage(stick_x) - stick_x_origin))  # 测试joystick电压


def draw_start():
    if not btn_a.value:
        start_game()
    display.show(display_start_text)


def draw_game_over():
    game_over_bg.y = 100
    game_over_text.y = 125
    if not btn_a.value:
        start_game()
        game_over_bg.y = 500
        game_over_text.y = 500
    display.show(display_all)


while True:
    if game_mode == "game":
        draw_game()
    elif game_mode == "start":
        draw_start()
    elif game_mode == "game_over":
        draw_game_over()
    elif game_mode == "dev":
        draw_dev()
    display.refresh()
