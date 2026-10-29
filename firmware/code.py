"""Matrix Portal S3 entry point: Wi-Fi, clock, the LED panel, the remote's socket, the main loop.

All the display logic is in app.py so it can run in the simulator too; this file
is only what needs the real hardware.

Needs in /lib: adafruit_requests, adafruit_connection_manager, adafruit_ntp, adafruit_httpserver.
settings.toml: CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD, MBTA_API_KEY, and optionally
REMOTE_TOKEN for the phone remote and AIO_USERNAME / AIO_KEY (Adafruit IO) for ride messages.
Don't print any of them.
"""
import gc
import json
import os
import time

import board
import displayio
import framebufferio
import microcontroller
import rgbmatrix
import rtc
import socketpool
import ssl
import supervisor
import wifi
from watchdog import WatchDogMode

import adafruit_ntp
import adafruit_requests
from adafruit_httpserver import GET, POST, FileResponse, Response, Server

import app
import remote
import sign as signlib

try:
    import bitmaptools
except ImportError:
    bitmaptools = None

FRAME_MS = 50              # ~20 frames a second while something animates
NTP_MS = 6 * 3600 * 1000   # set the clock again this often
WLED_TIMEOUT = 1.5         # seconds to wait for WLED before giving up on one setting (it is tried again later)
WATCHDOG_S = (30, 20, 10)  # reboot if the loop stalls; not sure every CircuitPython build takes 30, so try smaller

wdt = None                 # the watchdog, once start_watchdog() has run
STATUS_TEXT = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found"}


def feed():
    # call this anywhere the board waits on purpose (Wi-Fi, a slow send) so the watchdog doesn't fire
    if wdt:
        wdt.feed()


def start_watchdog():
    global wdt
    for seconds in WATCHDOG_S:
        try:
            microcontroller.watchdog.timeout = seconds
            microcontroller.watchdog.mode = WatchDogMode.RESET
            wdt = microcontroller.watchdog
            wdt.feed()
            print("watchdog:", seconds, "s")
            return
        except Exception as e:
            print("watchdog:", type(e).__name__)

data = app.load_data()

# --- sign panel
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=signlib.W, height=signlib.H, bit_depth=data["sign"].get("bit_depth", 5),
    rgb_pins=[board.MTX_R1, board.MTX_G1, board.MTX_B1, board.MTX_R2, board.MTX_G2, board.MTX_B2],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK, latch_pin=board.MTX_LAT, output_enable_pin=board.MTX_OE)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True, rotation=data["sign"].get("rotation", 0))
bitmap = displayio.Bitmap(signlib.W, signlib.H, 16)
palette = displayio.Palette(16)
group = displayio.Group()
group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = group
shown = [None] * signlib.H      # the rows currently on the panel


def set_palette(colors):
    for i in range(len(colors)):
        palette[i] = (colors[i][0] << 16) | (colors[i][1] << 8) | colors[i][2]


def show(bm):
    # only copy the rows that changed
    for y in range(signlib.H):
        row = bm[y]
        if row == shown[y]:
            continue
        if bitmaptools:
            bitmaptools.arrayblit(bitmap, row, 0, y, signlib.W, y + 1)
        else:
            for x in range(signlib.W):
                bitmap[x, y] = row[x]
        shown[y] = row


def message(line1, line2=""):
    bm = signlib.blank()
    signlib.draw_text(bm, 2, 8, line1, signlib.NOTE)
    signlib.draw_text(bm, 2, 17, line2, signlib.DIM)
    show(bm)
    print(line1, line2)


st = app.setup(data)
set_palette(app.sign_palette(st, data))

# --- network
SSID = os.getenv("CIRCUITPY_WIFI_SSID")
PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")
KEY = os.getenv("MBTA_API_KEY")
st["remote_token"] = os.getenv("REMOTE_TOKEN") or ""      # "" = no code needed, only the X-Remote header
AIO_USER = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")
if AIO_USER and AIO_KEY:
    app.setup_mailbox(st, AIO_USER, (data.get("ride") or {}).get("feed", "mbta-ride"))


def connect():
    while wifi.radio.ipv4_address is None:
        feed()                  # waiting for the network is not a hang
        message("WIFI...", (SSID or "NO SSID SET")[:15])
        if not SSID:
            time.sleep(5)       # settings.toml isn't filled in yet
            continue
        try:
            wifi.radio.connect(SSID, PASSWORD)
        except Exception as e:  # wrong password, out of range, router restarting
            message("NO WIFI", "RETRYING")
            print(type(e).__name__)
            time.sleep(5)


def set_clock():
    try:
        rtc.RTC().datetime = ntp.datetime
        return True
    except Exception as e:
        print("clock:", type(e).__name__)
        return False


def fetch(url):
    began = now_ms()
    with requests.get(url, headers=app.request_headers(url, KEY, AIO_KEY), timeout=8) as r:
        if r.status_code != 200:
            raise RuntimeError("HTTP %d" % r.status_code)
        text = r.text
    d = json.loads(text)
    return d, len(text), now_ms() - began


def now_ms():
    return time.monotonic_ns() // 1000000


connect()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600)
message("CLOCK...")
while not set_clock():
    time.sleep(2)
clock_set = now_ms()
if not KEY:
    message("NO API KEY", "SEE SETTINGS")
    time.sleep(5)

wled = None
udp = None
if data.get("wled_ip") and data["wled_ip"] != "TODO":
    wled = (data["wled_ip"], app.DDP_PORT)
    udp = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    ddp = app.ddp_buffer(st)
resend_ms = int(data.get("ddp_resend_seconds", 1) * 1000)


night = False

# --- the phone remote

# No root directory on purpose: with one, any GET that matches no route is answered with the file of that
# name from the drive, so http://<board>/settings.toml would hand out the Wi-Fi password and the API keys.
# The page is sent by answer() below with an explicit root for that one file.
server = Server(pool)


def answer(request):
    st["ui"]["free"] = gc.mem_free()
    body = str(request.body or b"", "utf-8")
    status, ctype, out = remote.handle(st, request.method, request.path, body, request.headers,
                                       now_ms(), time.time())
    if ctype == "file":
        return FileResponse(request, out, "/")
    return Response(request, out, content_type=ctype, status=(status, STATUS_TEXT.get(status, "Error")))


for path in remote.PATHS:
    server.route(path, [GET, POST])(answer)


def post_wled(body):
    # Blocks for up to WLED_TIMEOUT, which is why app.wled_result() backs off when WLED is off.
    try:
        with requests.post("http://%s/json/state" % data["wled_ip"], json=body, timeout=WLED_TIMEOUT) as r:
            return r.status_code == 200
    except Exception as e:
        print("wled:", type(e).__name__)
        return False


def send_map(ms, t):
    global last_map
    app.update_map(st, ms)
    try:
        udp.sendto(app.ddp_packet(st, t, ddp, night, ms), wled)
    except OSError:
        pass                        # WLED off or unreachable; next frame will try again
    last_map = ms


message("LOADING...", str(wifi.radio.ipv4_address))
server.start(str(wifi.radio.ipv4_address), 80)

# Load everything once before the ticker starts.
while app.fetch_one(st, now_ms(), time.time(), fetch):
    gc.collect()
for line in app.report(st):
    print(line)
start_watchdog()                # from here on the main loop must keep feeding it

# --- main loop
last_map = last_report = -100000
slowest = frames = 0
shown_bm = None
while True:
    feed()
    start = now_ms()
    t = (start % 3600000) / 1000    # animation clock; wraps hourly to stay precise

    if wled and app.map_live(st) and start - last_map >= 250:
        send_map(start, t)          # a fresh frame just before any network pause
    try:
        server.poll()               # the phone remote, if it's asking
    except OSError:
        pass                        # a dropped connection; never let it stop the display
    if wled:
        setting = app.wled_due(st, start)
        if setting:
            app.wled_result(st, now_ms(), post_wled(setting))
            feed()
    app.tick(st, start, time.time(), fetch)     # may make one request, only while the ticker holds
    drawing = now_ms()
    is_night = app.is_night(st, time.time())
    if is_night != night or st["ui"]["dirty"]:     # night starts or ends, or the remote changed the mode or brightness
        night = is_night
        st["ui"]["dirty"] = False
        set_palette(app.sign_palette(st, data, night))
    if st["failures"] >= 5:         # the network has gone; start it again
        print("reconnecting:", st["last_error"])
        st["failures"] = 3          # keeps "NO DATA" up until a fetch works
        if wifi.radio.ipv4_address is None:
            connect()
    if drawing - clock_set > NTP_MS and st["tk"]["phase"] == "hold" and set_clock():
        clock_set = drawing

    if wled and app.map_live(st) and (app.is_animated(st, drawing) or drawing - last_map >= resend_ms):
        send_map(drawing, t)

    bm = app.sign_frame(st, drawing, time.time())
    if bm is not shown_bm:
        show(bm)
        shown_bm = bm

    if drawing - last_report >= 60000 and st["tk"]["phase"] == "hold":
        last_report = drawing       # status for anyone watching the serial port
        print("trains lit %d, ticker %s, failures %d %s, free %d, %d frames, slowest draw %d ms" % (
            sum(1 for s in st["states"] if s), st["tk"]["item"] and st["tk"]["item"]["key"],
            st["failures"], st["last_error"], gc.mem_free(), frames, slowest))
        for line in app.report(st):
            print(" ", line)
        slowest = frames = 0
    frames += 1
    slowest = max(slowest, now_ms() - drawing)

    spare = FRAME_MS - (now_ms() - start)
    if spare > 0:
        time.sleep(spare / 1000)
