GROUPS = {
    "U3": "U3 U4 C21 C16 C15 C19 C18 C17 R3 R4 C22 C14 C13 C8 R7 R6 R13 D3 C10 C11 R43 R44 TP10 TP11 "
          "C20 C12 R10 Y1 C23 C24 R12 TP5 TP7 C25 R11".split(),
    "SW": ["SW1", "SW2"],
    "U9": "U9 RN4 RN5 RN6 RN7 TP13 C71 R50".split(),
    "U8": "U8 RN1 RN2 RN3 C70".split(),
    "U6": "U6 TP12 C60 C61 R40 R42".split(),
    "U7": "U7 C62 C63 R41".split(),
    "J2": ["J2"],
    "J3": ["J3"],
}

def rot(dx, dy, d):
    """Rotate a board vector by d degrees CCW as seen on screen (y down)."""
    d %= 360
    if d == 0:
        return dx, dy
    if d == 90:
        return dy, -dx
    if d == 180:
        return -dx, -dy
    return -dy, dx


