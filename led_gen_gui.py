#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# led_gen_gui.py — редактор LED-паттернов и генератор установщика
# для Yandex Station Mini 2. Фото-предпросмотр требует Pillow
# (pip install pillow) и файла station_top.png рядом со скриптом.
# Для установки без скрипта с паролем полезен paramiko (pip install paramiko);
# без него используется системный ssh (пароль он спросит в консоли).

import base64
import hashlib
import json
import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog

try:
    from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

STATES = ('listening', 'speaking', 'thinking')
STATE_TITLES = {'listening': 'Слушает', 'speaking': 'Говорит', 'thinking': 'Думает'}
ZONES = 6
CANVAS_W, CANVAS_H = 560, 300
PHOTO_CANDIDATES = ('station_top.png', 'station_top.jpg')

ORIGINAL_PAYLOADS = {
    'listening': 'bG9vcApGRjE3NDQgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMApGRTE3NDQgRkU4OTAwIEZFRTUwMCAyMERGNjAgMDBEOEZFIDc0NERGRSAyMApGQzE3NDMgRkM4ODAwIEZDRTMwMCAyMERENUYgMDBENkZDIDczNENGQyAyMApGOTE2NDIgRjk4NzAwIEY5RTEwMCAxRkRCNUUgMDBENEY5IDcxNEJGOSAyMApGNTE2NDEgRjU4NTAwIEY1REQwMCAxRkQ3NUMgMDBEMEY1IDZGNEFGNSAyMApGMDE2NDAgRjA4MjAwIEYwRDgwMCAxRUQzNUEgMDBDQ0YwIDZENDhGMCAyMApFQTE1M0UgRUE3RjAwIEVBRDMwMCAxRENFNTggMDBDN0VBIDZBNDdFQSAyMApFMzE0M0QgRTM3QjAwIEUzQ0QwMCAxQ0M3NTUgMDBDMUUzIDY3NDVFMyAyMApEQzE0M0IgREM3NzAwIERDQzYwMCAxQ0MxNTMgMDBCQkRDIDY0NDJEQyAyMApENTEzMzkgRDU3MzAwIEQ1QzAwMCAxQkJCNTAgMDBCNUQ1IDYxNDBENSAyMApDRDEyMzcgQ0Q2RjAwIENEQjkwMCAxQUI0NEQgMDBBRUNEIDVEM0VDRCAyMApDNTEyMzUgQzU2QjAwIEM1QjIwMCAxOUFENEEgMDBBOEM1IDVBM0JDNSAyMApCRDExMzIgQkQ2NjAwIEJEQUEwMCAxOEE2NDcgMDBBMUJEIDU2MzlCRCAyMApCNTEwMzAgQjU2MjAwIEI1QTMwMCAxNzlGNDQgMDA5QUI1IDUyMzdCNSAyMApBRDEwMkUgQUQ1RTAwIEFEOUMwMCAxNjk4NDEgMDA5M0FEIDRGMzRBRCAyMApBNTBGMkMgQTU1OTAwIEE1OTUwMCAxNTkxM0UgMDA4Q0E1IDRCMzJBNSAyMAo5RTBFMkEgOUU1NjAwIDlFOEYwMCAxNDhCM0IgMDA4NjlFIDQ4MzA5RSAyMAo5NzBFMjggOTc1MjAwIDk3ODgwMCAxMzg1MzkgMDA4MDk3IDQ1MkU5NyAyMAo5MDBEMjYgOTA0RTAwIDkwODIwMCAxMjdFMzYgMDA3QjkwIDQyMkI5MCAyMAo4QTBDMjUgOEE0QjAwIDhBN0MwMCAxMTc5MzQgMDA3NThBIDNGMkE4QSAyMAo4NDBDMjMgODQ0NzAwIDg0NzcwMCAxMTc0MzIgMDA3MDg0IDNDMjg4NCAyMAo3RjBCMjIgN0Y0NTAwIDdGNzMwMCAxMDcwMzAgMDA2QzdGIDNBMjY3RiAyMAo3QTBCMjEgN0E0MjAwIDdBNkUwMCAwRjZCMkUgMDA2ODdBIDM3MjU3QSAyMAo3NjBCMUYgNzY0MDAwIDc2NkEwMCAwRjY4MkMgMDA2NDc2IDM2MjQ3NiAyMAo3MjBBMUUgNzIzRTAwIDcyNjcwMCAwRTY0MkIgMDA2MTcyIDM0MjI3MiAyMAo2RjBBMUUgNkYzQzAwIDZGNjQwMCAwRTYyMkEgMDA1RTZGIDMyMjI2RiAyMAo2QzBBMUQgNkMzQTAwIDZDNjEwMCAwRTVGMjkgMDA1QzZDIDMxMjE2QyAyMAo2QTBBMUMgNkEzOTAwIDZBNjAwMCAwRDVEMjggMDA1QTZBIDMwMjA2QSAyMAo2ODA5MUMgNjgzODAwIDY4NUUwMCAwRDVCMjcgMDA1OTY4IDJGMUY2OCAyMAo2NzA5MUIgNjczODAwIDY3NUQwMCAwRDVBMjcgMDA1ODY3IDJGMUY2NyAyMAo2NjA5MUIgNjYzNzAwIDY2NUMwMCAwRDVBMjYgMDA1NzY2IDJFMUY2NiA0MAo2NzA5MUIgNjczODAwIDY3NUQwMCAwRDVBMjcgMDA1ODY3IDJGMUY2NyAyMAo2ODA5MUMgNjgzODAwIDY4NUUwMCAwRDVCMjcgMDA1OTY4IDJGMUY2OCAyMAo2QjBBMUQgNkIzQTAwIDZCNjEwMCAwRDVFMjggMDA1QjZCIDMxMjA2QiAyMAo2RDBBMUQgNkQzQjAwIDZENjIwMCAwRTYwMjkgMDA1RDZEIDMyMjE2RCAyMAo3MDBBMUUgNzAzRDAwIDcwNjUwMCAwRTYyMkEgMDA1RjcwIDMzMjI3MCAyMAo3MzBBMUYgNzMzRTAwIDczNjgwMCAwRTY1MkIgMDA2MjczIDM0MjM3MyAyMAo3NjBCMUYgNzY0MDAwIDc2NkEwMCAwRjY4MkMgMDA2NDc2IDM2MjQ3NiAyMAo3QTBCMjEgN0E0MjAwIDdBNkUwMCAwRjZCMkUgMDA2ODdBIDM3MjU3QSAyMAo3RDBCMjEgN0Q0NDAwIDdENzEwMCAxMDZFMkYgMDA2QTdEIDM5MjY3RCAyMAo4MTBDMjIgODE0NjAwIDgxNzQwMCAxMDcxMzEgMDA2RTgxIDNCMjc4MSAyMAo4NTBDMjMgODU0ODAwIDg1NzgwMCAxMTc1MzIgMDA3MTg1IDNEMjg4NSAyMAo4OTBDMjUgODk0QTAwIDg5N0MwMCAxMTc4MzQgMDA3NTg5IDNFMjk4OSAyMAo4QzBEMjUgOEM0QzAwIDhDN0UwMCAxMjdCMzUgMDA3NzhDIDQwMkE4QyAyMAo5MDBEMjYgOTA0RTAwIDkwODIwMCAxMjdFMzYgMDA3QjkwIDQyMkI5MCAyMAo5NDBEMjcgOTQ1MDAwIDk0ODUwMCAxMzgyMzggMDA3RTk0IDQzMkQ5NCAyMAo5ODBFMjkgOTg1MjAwIDk4ODkwMCAxMzg2MzkgMDA4MTk4IDQ1MkU5OCAyMAo5QzBFMkEgOUM1NDAwIDlDOEQwMCAxNDg5M0IgMDA4NTlDIDQ3MkY5QyAyMApBMDBFMkIgQTA1NzAwIEEwOTAwMCAxNDhEM0MgMDA4OEEwIDQ5MzBBMCAyMApBNDBGMkMgQTQ1OTAwIEE0OTQwMCAxNTkwM0UgMDA4Q0E0IDRCMzJBNCAyMApBODBGMkQgQTg1QjAwIEE4OTgwMCAxNTk0M0YgMDA4RkE4IDRDMzNBOCAyMApBQzEwMkUgQUM1RDAwIEFDOUIwMCAxNjk3NDEgMDA5MkFDIDRFMzRBQyAyMApCMDEwMkYgQjA1RjAwIEIwOUYwMCAxNjlCNDIgMDA5NkIwIDUwMzVCMCAyMApCNTEwMzAgQjU2MjAwIEI1QTMwMCAxNzlGNDQgMDA5QUI1IDUyMzdCNSAyMApCOTExMzEgQjk2NDAwIEI5QTcwMCAxN0EzNDYgMDA5REI5IDU0MzhCOSAyMApCRDExMzIgQkQ2NjAwIEJEQUEwMCAxOEE2NDcgMDBBMUJEIDU2MzlCRCAyMApDMTExMzMgQzE2ODAwIEMxQUUwMCAxOEFBNDkgMDBBNEMxIDU4M0FDMSAyMApDNTEyMzUgQzU2QjAwIEM1QjIwMCAxOUFENEEgMDBBOEM1IDVBM0JDNSAyMApDOTEyMzYgQzk2RDAwIEM5QjUwMCAxOUIxNEMgMDBBQkM5IDVCM0RDOSAyMApDRDEyMzcgQ0Q2RjAwIENEQjkwMCAxQUI0NEQgMDBBRUNEIDVEM0VDRCAyMApEMTEzMzggRDE3MTAwIEQxQkQwMCAxQUI4NEYgMDBCMkQxIDVGM0ZEMSAyMApENTEzMzkgRDU3MzAwIEQ1QzAwMCAxQkJCNTAgMDBCNUQ1IDYxNDBENSAyMApEOTE0M0EgRDk3NTAwIEQ5QzQwMCAxQkJGNTIgMDBCOUQ5IDYzNDJEOSAyMApEQzE0M0IgREM3NzAwIERDQzYwMCAxQ0MxNTMgMDBCQkRDIDY0NDJEQyAyMApFMDE0M0MgRTA3OTAwIEUwQ0EwMCAxQ0M1NTQgMDBCRkUwIDY2NDRFMCAyMApFNDE1M0QgRTQ3QjAwIEU0Q0UwMCAxREM4NTYgMDBDMkU0IDY4NDVFNCAyMApFODE1M0UgRTg3RTAwIEU4RDEwMCAxRENDNTcgMDBDNUU4IDZBNDZFOCAyMApFQjE1M0YgRUI3RjAwIEVCRDQwMCAxRENFNTggMDBDOEVCIDZCNDdFQiAyMApFRjE2NDAgRUY4MTAwIEVGRDgwMCAxRUQyNUEgMDBDQkVGIDZENDhFRiAyMApGMjE2NDEgRjI4MzAwIEYyREEwMCAxRUQ1NUIgMDBDRUYyIDZFNDlGMiAyMApGNTE2NDEgRjU4NTAwIEY1REQwMCAxRkQ3NUMgMDBEMEY1IDZGNEFGNSAyMApGODE2NDIgRjg4NjAwIEY4RTAwMCAxRkRBNUQgMDBEM0Y4IDcxNEJGOCAyMApGQTE3NDMgRkE4NzAwIEZBRTEwMCAxRkRDNUUgMDBENUZBIDcyNEJGQSAyMApGRDE3NDMgRkQ4OTAwIEZERTQwMCAyMERFNUYgMDBEN0ZEIDczNENGRCAyMApGRTE3NDQgRkU4OTAwIEZFRTUwMCAyMERGNjAgMDBEOEZFIDc0NERGRSAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAo=',
    'speaking': 'bG9vcApGRkU2MDAgRkZFNjAwIEZGRTYwMCBGRkU2MDAgRkZFNjAwIEZGRTYwMCA0MApGRUU1MDAgRkVFNTAwIEZFRTUwMCBGRUU1MDAgRkVFNTAwIEZFRTUwMCAyMApGQ0UzMDAgRkNFMzAwIEZDRTMwMCBGQ0UzMDAgRkNFMzAwIEZDRTMwMCAyMApGQUUxMDAgRkFFMTAwIEZBRTEwMCBGQUUxMDAgRkFFMTAwIEZBRTEwMCAyMApGOEUwMDAgRjhFMDAwIEY4RTAwMCBGOEUwMDAgRjhFMDAwIEY4RTAwMCAyMApGNkRFMDAgRjZERTAwIEY2REUwMCBGNkRFMDAgRjZERTAwIEY2REUwMCAyMApGM0RCMDAgRjNEQjAwIEYzREIwMCBGM0RCMDAgRjNEQjAwIEYzREIwMCAyMApFRkQ4MDAgRUZEODAwIEVGRDgwMCBFRkQ4MDAgRUZEODAwIEVGRDgwMCAyMApFQkQ0MDAgRUJENDAwIEVCRDQwMCBFQkQ0MDAgRUJENDAwIEVCRDQwMCAyMApFOEQxMDAgRThEMTAwIEU4RDEwMCBFOEQxMDAgRThEMTAwIEU4RDEwMCAyMApFNENFMDAgRTRDRTAwIEU0Q0UwMCBFNENFMDAgRTRDRTAwIEU0Q0UwMCAyMApFMENBMDAgRTBDQTAwIEUwQ0EwMCBFMENBMDAgRTBDQTAwIEUwQ0EwMCAyMApEQ0M2MDAgRENDNjAwIERDQzYwMCBEQ0M2MDAgRENDNjAwIERDQzYwMCAyMApEN0MyMDAgRDdDMjAwIEQ3QzIwMCBEN0MyMDAgRDdDMjAwIEQ3QzIwMCAyMApEMkJEMDAgRDJCRDAwIEQyQkQwMCBEMkJEMDAgRDJCRDAwIEQyQkQwMCAyMApDRUJBMDAgQ0VCQTAwIENFQkEwMCBDRUJBMDAgQ0VCQTAwIENFQkEwMCAyMApDOEI0MDAgQzhCNDAwIEM4QjQwMCBDOEI0MDAgQzhCNDAwIEM4QjQwMCAyMApDNEIxMDAgQzRCMTAwIEM0QjEwMCBDNEIxMDAgQzRCMTAwIEM0QjEwMCAyMApCRkFDMDAgQkZBQzAwIEJGQUMwMCBCRkFDMDAgQkZBQzAwIEJGQUMwMCAyMApCOUE3MDAgQjlBNzAwIEI5QTcwMCBCOUE3MDAgQjlBNzAwIEI5QTcwMCAyMApCNEEyMDAgQjRBMjAwIEI0QTIwMCBCNEEyMDAgQjRBMjAwIEI0QTIwMCAyMApBRjlFMDAgQUY5RTAwIEFGOUUwMCBBRjlFMDAgQUY5RTAwIEFGOUUwMCAyMApBOTk4MDAgQTk5ODAwIEE5OTgwMCBBOTk4MDAgQTk5ODAwIEE5OTgwMCAyMApBNDk0MDAgQTQ5NDAwIEE0OTQwMCBBNDk0MDAgQTQ5NDAwIEE0OTQwMCAyMAo5RThGMDAgOUU4RjAwIDlFOEYwMCA5RThGMDAgOUU4RjAwIDlFOEYwMCAyMAo5OThBMDAgOTk4QTAwIDk5OEEwMCA5OThBMDAgOTk4QTAwIDk5OEEwMCAyMAo5NDg1MDAgOTQ4NTAwIDk0ODUwMCA5NDg1MDAgOTQ4NTAwIDk0ODUwMCAyMAo4RDdGMDAgOEQ3RjAwIDhEN0YwMCA4RDdGMDAgOEQ3RjAwIDhEN0YwMCAyMAo4NTc4MDAgODU3ODAwIDg1NzgwMCA4NTc4MDAgODU3ODAwIDg1NzgwMCAyMAo3OTZEMDAgNzk2RDAwIDc5NkQwMCA3OTZEMDAgNzk2RDAwIDc5NkQwMCAyMAo2QTYwMDAgNkE2MDAwIDZBNjAwMCA2QTYwMDAgNkE2MDAwIDZBNjAwMCAyMAo1OTUwMDAgNTk1MDAwIDU5NTAwMCA1OTUwMDAgNTk1MDAwIDU5NTAwMCAyMAo0NzQwMDAgNDc0MDAwIDQ3NDAwMCA0NzQwMDAgNDc0MDAwIDQ3NDAwMCAyMAozQTM0MDAgM0EzNDAwIDNBMzQwMCAzQTM0MDAgM0EzNDAwIDNBMzQwMCAyMAozMjJEMDAgMzIyRDAwIDMyMkQwMCAzMjJEMDAgMzIyRDAwIDMyMkQwMCAyMAoyRjJBMDAgMkYyQTAwIDJGMkEwMCAyRjJBMDAgMkYyQTAwIDJGMkEwMCAyMAozMzJFMDAgMzMyRTAwIDMzMkUwMCAzMzJFMDAgMzMyRTAwIDMzMkUwMCAyMAozQjM1MDAgM0IzNTAwIDNCMzUwMCAzQjM1MDAgM0IzNTAwIDNCMzUwMCAyMAo0NTNFMDAgNDUzRTAwIDQ1M0UwMCA0NTNFMDAgNDUzRTAwIDQ1M0UwMCAyMAo1MzRCMDAgNTM0QjAwIDUzNEIwMCA1MzRCMDAgNTM0QjAwIDUzNEIwMCAyMAo2MTU3MDAgNjE1NzAwIDYxNTcwMCA2MTU3MDAgNjE1NzAwIDYxNTcwMCAyMAo2RjY0MDAgNkY2NDAwIDZGNjQwMCA2RjY0MDAgNkY2NDAwIDZGNjQwMCAyMAo3QjZGMDAgN0I2RjAwIDdCNkYwMCA3QjZGMDAgN0I2RjAwIDdCNkYwMCAyMAo4Njc5MDAgODY3OTAwIDg2NzkwMCA4Njc5MDAgODY3OTAwIDg2NzkwMCAyMAo5MDgyMDAgOTA4MjAwIDkwODIwMCA5MDgyMDAgOTA4MjAwIDkwODIwMCAyMAo5Nzg4MDAgOTc4ODAwIDk3ODgwMCA5Nzg4MDAgOTc4ODAwIDk3ODgwMCAyMAo5RThGMDAgOUU4RjAwIDlFOEYwMCA5RThGMDAgOUU4RjAwIDlFOEYwMCAyMApBNTk1MDAgQTU5NTAwIEE1OTUwMCBBNTk1MDAgQTU5NTAwIEE1OTUwMCAyMApBQzlCMDAgQUM5QjAwIEFDOUIwMCBBQzlCMDAgQUM5QjAwIEFDOUIwMCAyMApCNEEyMDAgQjRBMjAwIEI0QTIwMCBCNEEyMDAgQjRBMjAwIEI0QTIwMCAyMApCQUE4MDAgQkFBODAwIEJBQTgwMCBCQUE4MDAgQkFBODAwIEJBQTgwMCAyMApDMkFGMDAgQzJBRjAwIEMyQUYwMCBDMkFGMDAgQzJBRjAwIEMyQUYwMCAyMApDOUI1MDAgQzlCNTAwIEM5QjUwMCBDOUI1MDAgQzlCNTAwIEM5QjUwMCAyMApEMUJEMDAgRDFCRDAwIEQxQkQwMCBEMUJEMDAgRDFCRDAwIEQxQkQwMCAyMApEOEMzMDAgRDhDMzAwIEQ4QzMwMCBEOEMzMDAgRDhDMzAwIEQ4QzMwMCAyMApERkM5MDAgREZDOTAwIERGQzkwMCBERkM5MDAgREZDOTAwIERGQzkwMCAyMApFN0QwMDAgRTdEMDAwIEU3RDAwMCBFN0QwMDAgRTdEMDAwIEU3RDAwMCAyMApFREQ2MDAgRURENjAwIEVERDYwMCBFREQ2MDAgRURENjAwIEVERDYwMCAyMApGNERDMDAgRjREQzAwIEY0REMwMCBGNERDMDAgRjREQzAwIEY0REMwMCAyMApGOEUwMDAgRjhFMDAwIEY4RTAwMCBGOEUwMDAgRjhFMDAwIEY4RTAwMCAyMApGREU0MDAgRkRFNDAwIEZERTQwMCBGREU0MDAgRkRFNDAwIEZERTQwMCAyMAo=',
    'thinking': 'bG9vcApFODE1M0UgMDAwMDAwIDA5MDgwMCAxQ0MyNTMgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMDEwMTAwIDA2MDUwMCAxQUIzNEQgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMDMwMjAwIDAzMDMwMCAxN0ExNDUgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMDYwMzAwIDAyMDIwMCAxNDhEM0QgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMEIwNjAwIDAxMDEwMCAxMTc5MzQgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMTMwQTAwIDAwMDAwMCAwRTY0MkIgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMUYxMTAwIDAwMDAwMCAwQjUwMjIgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgMkUxOTAwIDAwMDAwMCAwOTNFMUIgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgNDMyNDAwIDAwMDAwMCAwNzJFMTQgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgNUYzMzAwIDAwMDAwMCAwNTIxMEUgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgODE0NjAwIDAwMDAwMCAwMzE2MDkgMDBEOUZGIDc0NERGRiAyMApGRjE3NDQgQTY1QTAwIDAwMDAwMCAwMjBGMDYgMDBEMEY1IDc0NERGRiAyMApGRjE3NDQgQ0I2RTAwIDAwMDAwMCAwMTA5MDQgMDBDM0U1IDc0NERGRiAyMApGRjE3NDQgRUY4MTAwIDAwMDAwMCAwMTA0MDIgMDBCNEQ0IDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDAxMDEwMCAwMDAyMDEgMDBBNEMxIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDA0MDQwMCAwMDAwMDAgMDA5MkFDIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDA4MDcwMCAwMDAwMDAgMDA3Rjk1IDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDBGMEUwMCAwMDAwMDAgMDA2QjdFIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDE5MTcwMCAwMDAwMDAgMDA1ODY3IDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDI3MjMwMCAwMDAwMDAgMDA0NTUxIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDNCMzUwMCAwMDAwMDAgMDAzNDNEIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDU0NEMwMCAwMDAwMDAgMDAyNjJEIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDczNjgwMCAwMDAwMDAgMDAxQjIwIDc0NERGRiAyMApGRjE3NDQgRkY4QTAwIDk4ODkwMCAwMDAwMDAgMDAxMzE2IDcwNEJGNyAyMApGRjE3NDQgRkY4QTAwIEJFQUIwMCAwMDAwMDAgMDAwQzBFIDY5NDZFNyAyMApGRjE3NDQgRkY4QTAwIEUyQ0MwMCAwMDAwMDAgMDAwODA5IDYxNDFENiAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwMDAxMDAgMDAwNDA1IDU5M0JDMyAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwMDAzMDEgMDAwMzAzIDRGMzVBRSAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwMTA1MDIgMDAwMTAxIDQ1MkU5OCAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwMjBCMDUgMDAwMDAwIDNCMjc4MSAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwMjExMDcgMDAwMDAwIDMwMjA2OSAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwNDFBMEIgMDAwMDAwIDI2MTk1MyAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwNjI4MTEgMDAwMDAwIDFEMTM0MCAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwOTNDMUEgMDAwMDAwIDE1MEUyRiAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAwQzU0MjQgMDAwMDAwIDBGMEEyMiAyMApGRjE3NDQgRkY4QTAwIEZGRTYwMCAxMDcxMzEgMDAwMDAwIDBBMDcxNyAyMApGNTE2NDEgRkY4QTAwIEZGRTYwMCAxNTkzM0YgMDAwMDAwIDA3MDUxMCAyMApFNTE1M0QgRkY4QTAwIEZGRTYwMCAxQUIzNEQgMDAwMDAwIDA1MDMwQSAyMApENDEzMzkgRkY4QTAwIEZGRTYwMCAxRUQ0NUIgMDAwMDAwIDAzMDIwNyAyMApDMDExMzMgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAwMTAxIDAyMDEwNCAyMApBQTBGMkQgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAwMzA0IDAxMDEwMiAyMAo5MzBEMjcgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAwNzA4IDAwMDAwMSAyMAo3QjBCMjEgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAwQzBFIDAwMDAwMCAyMAo2NDA5MUIgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAxNDE3IDAwMDAwMCAyMAo0RTA3MTUgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAxRjI0IDAwMDAwMCAyMAozQjA1MTAgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDAyRTM2IDAwMDAwMCAyMAoyQjA0MEIgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDA0MzRGIDAwMDAwMCAyMAoxRTAzMDggRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDA1RDZEIDAwMDAwMCAyMAoxNDAyMDUgRkY4QTAwIEZGRTYwMCAyMEUwNjAgMDA3QzkyIDAwMDAwMCAyMAowQzAxMDMgRjI4MzAwIEZGRTYwMCAyMEUwNjAgMDA5REI4IDAwMDAwMCAyMAowNzAxMDIgRTE3QTAwIEZGRTYwMCAyMEUwNjAgMDBCQkRDIDAwMDAwMCAyMAowMzAwMDEgQ0Y3MDAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDAwMDAwMSAyMAowMTAwMDAgQkI2NTAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDAxMDEwMyAyMAowMDAwMDAgQTU1OTAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDAzMDIwNyAyMAowMDAwMDAgOEU0RDAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDA2MDQwRCAyMAowMDAwMDAgNzY0MDAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDBBMDcxNiAyMAowMDAwMDAgNUYzMzAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDEwMEIyMyAyMAowMDAwMDAgNEEyODAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDE4MTAzNSAyMAowMDAwMDAgMzkxRjAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDIzMTc0QyAyMAowMDAwMDAgMjgxNjAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDMwMjA2QSAyMAowMDAwMDAgMUMwRjAwIEZGRTYwMCAyMEUwNjAgMDBEOUZGIDQwMkI4RCAyMAowMDAwMDAgMTMwQTAwIEY0REMwMCAyMEUwNjAgMDBEOUZGIDUxMzZCMyAyMAowMDAwMDAgMEMwNjAwIEUzQ0QwMCAyMEUwNjAgMDBEOUZGIDYyNDFEOCAyMAowMTAwMDAgMDcwNDAwIEQyQkQwMCAyMEUwNjAgMDBEOUZGIDczNENGQyAyMAowMzAwMDEgMDQwMjAwIEJGQUMwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAowNjAxMDIgMDIwMTAwIEE5OTgwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAowQTAxMDMgMDEwMTAwIDkzODUwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAoxMTAyMDUgMDAwMDAwIDdDNzAwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAoxQzAzMDcgMDAwMDAwIDY1NUIwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAoyQjA0MEIgMDAwMDAwIDRGNDcwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAozRjA2MTEgMDAwMDAwIDNEMzcwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAo1OTA4MTggMDAwMDAwIDJDMjgwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAo3OTBCMjAgMDAwMDAwIDFGMUMwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMAo5RTBFMkEgMDAwMDAwIDE2MTQwMCAyMEUwNjAgMDBEOUZGIDc0NERGRiAyMApDNDEyMzQgMDAwMDAwIDBGMEUwMCAxRUQyNUEgMDBEOUZGIDc0NERGRiAyMAo=',
}


# ---------------- работа с паттернами ----------------

def parse_payload_text(text):
    lines = text.strip().split('\n')
    if not lines or lines[0].strip() != 'loop':
        raise ValueError('паттерн должен начинаться со строки "loop"')
    frames = []
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) != 7:
            raise ValueError('некорректная строка кадра: %r' % ln)
        colors = [tuple(int(p[j:j + 2], 16) for j in (0, 2, 4))
                  for p in parts[:6]]
        frames.append((colors, int(parts[6], 16)))
    return frames


def parse_payload(b64):
    return parse_payload_text(base64.b64decode(b64.encode('ascii')).decode('ascii'))


def hex_to_rgb(s):
    s = s.strip().lstrip('#').upper()
    if not re.fullmatch(r'[0-9A-F]{6}', s):
        raise ValueError('нужен HEX вида RRGGBB, например FFE600')
    v = int(s, 16)
    return (v >> 16 & 255, v >> 8 & 255, v & 255)


def rgb_to_hex(c):
    return '%02X%02X%02X' % tuple(c)


def recolor_frames(frames, main_rgb, keep_structure, overrides=None):
    if overrides is None:
        overrides = [None] * ZONES
    out = []
    for colors, dur in frames:
        row = []
        for i, src in enumerate(colors):
            base = overrides[i] if (i < len(overrides) and overrides[i]) else main_rgb
            if keep_structure:
                f = max(src) / 255.0
                row.append(tuple(min(255, round(base[j] * f)) for j in range(3)))
            else:
                row.append(tuple(base))
        out.append((row, dur))
    return out


def scale_frames(frames, brightness_pct, speed):
    k = brightness_pct / 100.0
    out = []
    for colors, dur in frames:
        row = [tuple(min(255, round(ch * k)) for ch in c) for c in colors]
        out.append((row, max(1, round(dur * speed))))
    return out


def build_payload(frames):
    lines = ['loop']
    for colors, dur in frames:
        lines.append('%s %02X' % (' '.join(rgb_to_hex(c) for c in colors), dur))
    data = ('\n'.join(lines) + '\n').encode('ascii')
    return base64.b64encode(data).decode('ascii'), hashlib.sha256(data).hexdigest()


def build_patterns(patterns, brightness, speed):
    payloads, hashes, counts = {}, {}, {}
    for name in STATES:
        frames = scale_frames(patterns[name], brightness, speed)
        payloads[name], hashes[name] = build_payload(frames)
        counts[name] = len(frames)
    return payloads, hashes, counts


def render_photo_frame(base, params, colors):
    W, H = base.size
    cx, cy = params['cx'] * W, params['cy'] * H
    rx, ry = params['rx'] * W, params['ry'] * H
    thick = max(2, int(params['thick'] / 100.0 * min(rx, ry)))
    bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
    overlay = Image.new('RGB', base.size, (0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i, c in enumerate(colors):
        start = -90 + i * 60
        draw.arc(bbox, start, start + 60, fill=c, width=thick)
    glow = overlay.filter(ImageFilter.GaussianBlur(max(2.0, thick * 0.5)))
    return ImageChops.add(base, glow)


# ---------------- шаблон установщика ----------------

SHELL_TEMPLATE = r'''#!/bin/sh
set -eu

TARGET_DEVICE=mini2
if [ "$#" -gt 0 ] && [ "$1" = "--help" ]; then
  echo "Usage: $0 [ssh-host]"
  echo "Default host: mini2"
  exit 0
fi
if [ "$#" -gt 0 ]; then
  TARGET_DEVICE=$1
fi

command -v ssh >/dev/null 2>&1 || {
  echo "ssh is required" >&2
  exit 1
}
command -v base64 >/dev/null 2>&1 || {
  echo "base64 is required on the computer running this script" >&2
  exit 1
}

payload() {
  case "$1" in
    listening)
      cat <<'PAYLOAD_LISTENING'
@@P_LISTENING@@
PAYLOAD_LISTENING
      ;;
    speaking)
      cat <<'PAYLOAD_SPEAKING'
@@P_SPEAKING@@
PAYLOAD_SPEAKING
      ;;
    thinking)
      cat <<'PAYLOAD_THINKING'
@@P_THINKING@@
PAYLOAD_THINKING
      ;;
    *)
      echo "Unknown payload: $1" >&2
      exit 2
      ;;
  esac
}

echo "Checking $TARGET_DEVICE..."
ssh "$TARGET_DEVICE" 'sh -s' <<'REMOTE_PREFLIGHT'
@@PREFLIGHT_BODY@@
REMOTE_PREFLIGHT

backup_dir=$(ssh "$TARGET_DEVICE" 'sh -s' <<'REMOTE_BACKUP'
@@BACKUP_BODY@@
REMOTE_BACKUP
)
echo "Originals backed up to: $backup_dir"

for name in listening speaking thinking
do
  echo "Uploading custom $name pattern..."
  payload "$name" |
    ssh "$TARGET_DEVICE" "base64 -d > /data/quasar/.rgb-alice-$name.led.new"
done

ssh "$TARGET_DEVICE" 'sh -s' <<'REMOTE_INSTALL'
@@INSTALL_BODY@@
REMOTE_INSTALL

echo "Done. Reconnect to $TARGET_DEVICE if it had an active SSH session."
'''

RESTORE_TEMPLATE = r'''#!/bin/sh
# Возвращает стоковые паттерны из каталога бэкапа на устройстве.
# Запуск: sh restore_led.sh [ssh-host]
set -eu

TARGET_DEVICE=mini2
BACKUP_DIR=@@BACKUP_DIR@@

if [ "$#" -gt 0 ]; then
  TARGET_DEVICE=$1
fi

ssh "$TARGET_DEVICE" 'sh -s' "$BACKUP_DIR" <<'REMOTE_RESTORE'
@@RESTORE_BODY@@
REMOTE_RESTORE
echo "Done."
'''

PREFLIGHT_BODY = r'''
set -eu

[ "$(id -u)" = 0 ] || {
  echo "Root SSH access is required" >&2
  exit 1
}
[ "$(uname -m)" = "aarch64" ] || {
  echo "This installer requires aarch64" >&2
  exit 1
}
model=$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)
case "$model" in
  *"Yandex Station Mini 2"*) ;;
  *)
    echo "Not a Yandex Station Mini 2: $model" >&2
    exit 1
    ;;
esac
echo "MODEL=$model"
[ -d /data/quasar ] || mkdir -p /data/quasar
command -v base64 >/dev/null 2>&1 || {
  echo "base64 is missing on the target" >&2
  exit 1
}
command -v sha256sum >/dev/null 2>&1 || {
  echo "sha256sum is missing on the target" >&2
  exit 1
}
[ -x /system/vendor/quasar/led_util ] || {
  echo "Quasar LED utility is missing" >&2
  exit 1
}
for file in \
  /system/vendor/quasar/ledpatterns/oknix/alice_listening.led \
  /system/vendor/quasar/ledpatterns/oknix/alice_speaking.led \
  /system/vendor/quasar/ledpatterns/oknix/alice_thinking.led
do
  [ -f "$file" ] || {
    echo "Missing stock pattern: $file" >&2
    exit 1
  }
done
echo "PREFLIGHT_OK"
'''

BACKUP_BODY = r'''
set -eu
backup=/data/quasar/rgb-alice-backup-$(date +%Y%m%d-%H%M%S)-$$
mkdir "$backup"
cp -p /system/vendor/quasar/ledpatterns/oknix/alice_listening.led "$backup/"
cp -p /system/vendor/quasar/ledpatterns/oknix/alice_speaking.led "$backup/"
cp -p /system/vendor/quasar/ledpatterns/oknix/alice_thinking.led "$backup/"
(
  cd "$backup"
  sha256sum alice_listening.led alice_speaking.led alice_thinking.led > SHA256SUMS
)
echo "BACKUP_DIR=$backup"
'''

RESTORE_BODY = r'''
set -eu
backup=$1
[ -f "$backup/alice_listening.led" ] && [ -f "$backup/alice_speaking.led" ] && [ -f "$backup/alice_thinking.led" ] || {
  echo "Backup files not found in $backup" >&2
  exit 1
}
rootfs_rw=0
restore_rootfs_ro() {
  if [ "$rootfs_rw" = 1 ]; then
    mount -o remount,ro / || true
  fi
}
trap restore_rootfs_ro 0 1 2 3 15
mount -o remount,rw /
rootfs_rw=1
cat "$backup/alice_listening.led" > /system/vendor/quasar/ledpatterns/oknix/alice_listening.led
cat "$backup/alice_speaking.led" > /system/vendor/quasar/ledpatterns/oknix/alice_speaking.led
cat "$backup/alice_thinking.led" > /system/vendor/quasar/ledpatterns/oknix/alice_thinking.led
mount -o remount,ro /
rootfs_rw=0
if /system/vendor/quasar/q restart; then
  echo "Stock patterns restored, Quasar restarted"
else
  echo "Warning: files restored, but Quasar restart failed" >&2
fi
echo "RESTORE_DONE"
'''

INSTALL_BODY = r'''
set -eu

work=/data/quasar
expected_listening=@@H_LISTENING@@
expected_speaking=@@H_SPEAKING@@
expected_thinking=@@H_THINKING@@

check_hash() {
  file=$1
  expected=$2
  actual=$(sha256sum "$file" | awk '{print $1}')
  [ "$actual" = "$expected" ] || {
    echo "Hash mismatch: $file" >&2
    exit 1
  }
}

check_hash "$work/.rgb-alice-listening.led.new" "$expected_listening"
check_hash "$work/.rgb-alice-speaking.led.new" "$expected_speaking"
check_hash "$work/.rgb-alice-thinking.led.new" "$expected_thinking"

mv "$work/.rgb-alice-listening.led.new" "$work/alice_custom_listening.led"
mv "$work/.rgb-alice-speaking.led.new" "$work/alice_custom_speaking.led"
mv "$work/.rgb-alice-thinking.led.new" "$work/alice_custom_thinking.led"

rootfs_rw=0
restore_rootfs_ro() {
  if [ "$rootfs_rw" = 1 ]; then
    mount -o remount,ro / || true
  fi
}
trap restore_rootfs_ro 0 1 2 3 15

mount -o remount,rw /
rootfs_rw=1

cp -p "$work/alice_custom_listening.led"  /system/vendor/quasar/ledpatterns/oknix/alice_listening.led
cp -p "$work/alice_custom_speaking.led"   /system/vendor/quasar/ledpatterns/oknix/alice_speaking.led
cp -p "$work/alice_custom_thinking.led"   /system/vendor/quasar/ledpatterns/oknix/alice_thinking.led

check_hash /system/vendor/quasar/ledpatterns/oknix/alice_listening.led "$expected_listening"
check_hash /system/vendor/quasar/ledpatterns/oknix/alice_speaking.led "$expected_speaking"
check_hash /system/vendor/quasar/ledpatterns/oknix/alice_thinking.led "$expected_thinking"

mount -o remount,ro /
rootfs_rw=0

if /system/vendor/quasar/q restart; then
  echo "Quasar restarted"
else
  echo "Warning: files installed, but Quasar restart failed" >&2
fi

echo "Installed custom RGB Alice patterns"
echo "listening: @@N_LISTENING@@ frames"
echo "speaking: @@N_SPEAKING@@ frames"
echo "thinking: @@N_THINKING@@ frames"
echo "INSTALL_DONE"
'''


# ---------------- генерация ----------------

def generate_script(patterns, brightness, speed):
    payloads, hashes, counts = build_patterns(patterns, brightness, speed)
    script = SHELL_TEMPLATE
    for name in STATES:
        up = name.upper()
        script = script.replace('@@P_%s@@' % up, payloads[name])
    script = script.replace('@@PREFLIGHT_BODY@@', PREFLIGHT_BODY)
    script = script.replace('@@BACKUP_BODY@@', BACKUP_BODY)
    script = script.replace('@@INSTALL_BODY@@', INSTALL_BODY)
    for name in STATES:
        up = name.upper()
        script = script.replace('@@H_%s@@' % up, hashes[name])
        script = script.replace('@@N_%s@@' % up, str(counts[name]))
    return script, hashes, counts


def generate_restore(backup_dir):
    return RESTORE_TEMPLATE.replace('@@BACKUP_DIR@@', backup_dir.strip()) \
                           .replace('@@RESTORE_BODY@@', RESTORE_BODY)


def build_remote_install(payloads, hashes, counts):
    """Собирает единый удалённый скрипт: preflight + бэкап + заливка + установка."""
    parts = [REMOTE_FULL_HEADER, PREFLIGHT_BODY, BACKUP_BODY]
    for name in STATES:
        up = name.upper()
        parts.append("echo 'Uploading %s pattern...'\n" % name)
        parts.append("base64 -d > /data/quasar/.rgb-alice-%s.led.new <<'PAYLOAD_%s'\n"
                     % (name, up))
        parts.append(payloads[name] + '\n')
        parts.append('PAYLOAD_%s\n' % up)
    body = INSTALL_BODY
    for name in STATES:
        up = name.upper()
        body = body.replace('@@H_%s@@' % up, hashes[name])
        body = body.replace('@@N_%s@@' % up, str(counts[name]))
    parts.append(body)
    return '\n'.join(parts)


REMOTE_FULL_HEADER = 'set -eu\n'

REMOTE_RESTART = r'''
set -eu
if /system/vendor/quasar/q restart; then
  echo "Quasar restarted"
else
  echo "Quasar restart failed" >&2
  exit 1
fi
echo "RESTART_DONE"
'''


# ---------------- SSH ----------------

def ssh_run_subprocess(host, port, user, stdin_text, cmd='sh -s', timeout=300):
    argv = ['ssh', '-p', str(port), '-o', 'StrictHostKeyChecking=accept-new',
            '%s@%s' % (user, host), cmd]
    try:
        proc = subprocess.run(argv, input=stdin_text.encode('ascii'),
                              capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(
            'ssh не найден. Установите OpenSSH Client '
            '(Параметры Windows -> Приложения -> Дополнительные компоненты) '
            'или поставьте paramiko: pip install paramiko')
    return (proc.returncode,
            proc.stdout.decode('utf-8', errors='replace'),
            proc.stderr.decode('utf-8', errors='replace'))


def ssh_run_paramiko(host, port, user, password, stdin_text, cmd='sh -s'):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(host, port=port, username=user, password=password,
                    timeout=15)
        stdin, stdout, stderr = cli.exec_command(cmd, timeout=300)
        stdin.write(stdin_text)
        stdin.channel.shutdown_write()
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        code = stdout.channel.recv_exit_status()
    finally:
        cli.close()
    return code, out, err


# ---------------- интерфейс ----------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('LED-паттерны — Yandex Station Mini 2')
        self.minsize(920, 980)
        self.patterns = {}
        for name in STATES:
            self.patterns[name] = parse_payload(ORIGINAL_PAYLOADS[name])
        self.edit_idx = 0
        self.playing = False
        self.preview_job = None
        self.preview_frames = None
        self.preview_idx = 0
        self.photo_img = None
        self._preview_tk = None
        self._build_ui()
        self._load_default_photo()
        self.rebuild_preview()

    # ---------- построение интерфейса ----------

    def _build_ui(self):
        f1 = ttk.LabelFrame(self, text='Создатель кадров')
        f1.pack(fill='x', padx=8, pady=(8, 2))
        ttk.Label(f1, text='Цвета действий').grid(
            row=0, column=0, columnspan=6, sticky='w', padx=6, pady=(2, 0))
        self.main_entry = {}
        self.swatches = {}
        self.creator_keep = {}
        for i, name in enumerate(STATES):
            row = i + 1
            ttk.Label(f1, text=STATE_TITLES[name]).grid(
                row=row, column=0, sticky='w', padx=6, pady=3)
            entry = ttk.Entry(f1, width=10)
            entry.insert(0, 'FFFFFF')
            entry.grid(row=row, column=1, padx=4)
            entry.bind('<KeyRelease>', lambda e, n=name: self.draw_swatch(n))
            self.main_entry[name] = entry
            swatch = tk.Canvas(f1, width=26, height=22, highlightthickness=1,
                               highlightbackground='#999999')
            swatch.grid(row=row, column=2, padx=4)
            self.swatches[name] = swatch
            self.draw_swatch(name)
            ttk.Button(f1, text='Выбрать…', width=10,
                       command=lambda n=name: self.pick_color(n)).grid(
                row=row, column=3, padx=4)
            var = tk.BooleanVar(value=True)
            self.creator_keep[name] = var
            ttk.Checkbutton(f1, text='сохранить структуру анимации',
                            variable=var).grid(row=row, column=4, columnspan=2,
                                               sticky='w', padx=8)
        ttk.Label(f1, text='Свой цвет для отдельных зон '
                           '(необязательно, HEX RRGGBB)').grid(
            row=4, column=0, columnspan=6, sticky='w', padx=6, pady=(8, 0))
        for z in range(ZONES):
            ttk.Label(f1, text='Зона %d' % (z + 1)).grid(
                row=5, column=z + 1, padx=4)
        self.zone_entries = {}
        for i, name in enumerate(STATES):
            row = i + 6
            ttk.Label(f1, text=STATE_TITLES[name]).grid(
                row=row, column=0, sticky='w', padx=6)
            self.zone_entries[name] = []
            for z in range(ZONES):
                e = ttk.Entry(f1, width=9)
                e.grid(row=row, column=z + 1, padx=2, pady=2)
                self.zone_entries[name].append(e)
        row_btn = 9
        ttk.Button(f1, text='Создать кадры', command=self.apply_creator).grid(
            row=row_btn, column=0, columnspan=2, padx=6, pady=(6, 4), sticky='w')
        ttk.Label(f1, text='пересобирает все три анимации из стоковых '
                           'паттернов по заданным цветам').grid(
            row=row_btn, column=2, columnspan=4, sticky='w', pady=(6, 4))
        f1.columnconfigure(6, weight=1)

        f2 = ttk.LabelFrame(
            self, text='Общие настройки (применяются при генерации и в предпросмотре)')
        f2.pack(fill='x', padx=8, pady=2)
        ttk.Label(f2, text='Яркость, %:').grid(row=0, column=0, padx=6)
        self.brightness = ttk.Spinbox(f2, from_=1, to=100, width=6)
        self.brightness.set(100)
        self.brightness.grid(row=0, column=1)
        ttk.Label(f2, text='Скорость (множитель длительности кадра):').grid(
            row=0, column=2, padx=(16, 4))
        self.speed = ttk.Spinbox(f2, from_=0.1, to=10, increment=0.1, width=6)
        self.speed.set(1.0)
        self.speed.grid(row=0, column=3)
        ttk.Button(f2, text='Обновить предпросмотр',
                   command=self.rebuild_preview).grid(row=0, column=4, padx=12)

        f3 = ttk.LabelFrame(
            self, text='Редактор кадров — изменения сразу попадают в установщик')
        f3.pack(fill='x', padx=8, pady=2)
        ttk.Label(f3, text='Действие:').grid(row=0, column=0, padx=6, pady=4)
        self.state_var = tk.StringVar(value='listening')
        cb = ttk.Combobox(f3, textvariable=self.state_var, width=10,
                          values=list(STATES), state='readonly')
        cb.grid(row=0, column=1, sticky='w')
        cb.bind('<<ComboboxSelected>>', lambda e: self.on_state_changed())
        left = ttk.Frame(f3)
        left.grid(row=1, column=0, columnspan=2, sticky='ns', padx=6, pady=4)
        self.frame_list = tk.Listbox(left, width=46, height=9, exportselection=False)
        self.frame_list.pack(side='left', fill='y')
        sb = ttk.Scrollbar(left, command=self.frame_list.yview)
        sb.pack(side='left', fill='y')
        self.frame_list.configure(yscrollcommand=sb.set)
        self.frame_list.bind('<<ListboxSelect>>', lambda e: self.on_frame_selected())
        btns = ttk.Frame(left)
        btns.pack(side='left', fill='y', padx=4)
        for text, cmd in (('Добавить копию', self.add_frame),
                          ('Удалить', self.del_frame),
                          ('Выше', self.move_up),
                          ('Ниже', self.move_down)):
            ttk.Button(btns, text=text, width=14, command=cmd).pack(pady=2)
        right = ttk.Frame(f3)
        right.grid(row=1, column=2, sticky='n', padx=6, pady=4)
        self.frame_title = ttk.Label(right, text='Кадр —')
        self.frame_title.grid(row=0, column=0, columnspan=3, sticky='w')
        self.zone_btns = []
        for z in range(ZONES):
            b = tk.Button(right, width=10, relief='flat', highlightthickness=1,
                          highlightbackground='#777777',
                          command=lambda z=z: self.pick_zone(z))
            b.grid(row=1 + z // 3, column=z % 3, padx=3, pady=3, sticky='we')
            self.zone_btns.append(b)
        ttk.Label(right, text='Длительность кадра, мс:').grid(
            row=3, column=0, sticky='w', pady=(4, 0))
        self.dur_entry = ttk.Entry(right, width=8)
        self.dur_entry.grid(row=4, column=0, sticky='w')
        self.dur_entry.bind('<Return>', lambda e: self.apply_duration())
        ttk.Button(right, text='Применить', width=10,
                   command=self.apply_duration).grid(row=4, column=1,
                                                     sticky='w', padx=4)

        f4 = ttk.LabelFrame(self, text='Предпросмотр (кольцо = 6 зон подсветки)')
        f4.pack(fill='x', padx=8, pady=2)
        self.canvas = tk.Canvas(f4, width=CANVAS_W, height=CANVAS_H,
                                bg='#101014', highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=7, padx=6, pady=6)
        self.btn_play = ttk.Button(f4, text='Старт', command=self.toggle_preview)
        self.btn_play.grid(row=0, column=1, padx=6, pady=6, sticky='w')
        ttk.Button(f4, text='Загрузить фото…', command=self.load_photo).grid(
            row=1, column=1, padx=6, sticky='w')
        params = (('центр X, %', 'cx', 48), ('центр Y, %', 'cy', 47),
                  ('радиус X, %', 'rx', 14.5), ('радиус Y, %', 'ry', 24),
                  ('толщина, %', 'thick', 35))
        self.ring_vars = {}
        for i, (label, key, default) in enumerate(params):
            ttk.Label(f4, text=label).grid(row=i, column=2, sticky='e',
                                           padx=(16, 2))
            v = tk.StringVar(value=str(default))
            self.ring_vars[key] = v
            sp = ttk.Spinbox(f4, from_=1, to=200, increment=0.5, width=7,
                             textvariable=v)
            sp.grid(row=i, column=3, sticky='w')
            sp.bind('<Return>', lambda e: self.rebuild_preview())
        self.photo_status = ttk.Label(
            f4, text='Фото не загружено — рисуется схематично')
        self.photo_status.grid(row=5, column=2, columnspan=2, sticky='w', padx=16)

        f8 = ttk.LabelFrame(
            self, text='Без скрипта — прямое подключение к колонке по SSH')
        f8.pack(fill='x', padx=8, pady=2)
        ttk.Label(f8, text='IP / хост:').grid(row=0, column=0, padx=6, sticky='w')
        self.ip_entry = ttk.Entry(f8, width=16)
        self.ip_entry.grid(row=0, column=1, padx=2)
        ttk.Label(f8, text='Порт:').grid(row=0, column=2, padx=(10, 2), sticky='w')
        self.port_spin = ttk.Spinbox(f8, from_=1, to=65535, width=7)
        self.port_spin.set(22)
        self.port_spin.grid(row=0, column=3)
        ttk.Label(f8, text='Пользователь:').grid(
            row=0, column=4, padx=(10, 2), sticky='w')
        self.user_entry = ttk.Entry(f8, width=10)
        self.user_entry.insert(0, 'root')
        self.user_entry.grid(row=0, column=5)
        ttk.Label(f8, text='Пароль:').grid(row=0, column=6, padx=(10, 2),
                                           sticky='w')
        self.pass_entry = ttk.Entry(f8, width=14, show='*')
        self.pass_entry.grid(row=0, column=7, padx=2)
        if HAS_PARAMIKO:
            hint = 'пароль используется (paramiko установлен)'
        else:
            hint = 'для пароля нужен paramiko: pip install paramiko'
        ttk.Label(f8, text=hint).grid(row=0, column=8, columnspan=3,
                                      sticky='w', padx=4)
        f8r = ttk.Frame(f8)
        f8r.grid(row=1, column=0, columnspan=11, sticky='w', padx=6, pady=4)
        ttk.Button(f8r, text='Проверить подключение',
                   command=lambda: self._bg(self._do_check)).pack(side='left',
                                                                  padx=3)
        ttk.Button(f8r, text='Установить паттерны',
                   command=lambda: self._bg(self._do_install)).pack(side='left',
                                                                    padx=3)
        ttk.Button(f8r, text='Перезапустить Quasar',
                   command=lambda: self._bg(self._do_restart)).pack(side='left',
                                                                    padx=3)
        ttk.Button(f8r, text='Восстановить из бэкапа…',
                   command=lambda: self._bg(self._do_restore)).pack(side='left',
                                                                    padx=3)
        f8.columnconfigure(9, weight=1)

        f5 = ttk.Frame(self)
        f5.pack(fill='x', padx=8, pady=2)
        ttk.Button(f5, text='Импорт паттерна…', command=self.import_pattern).pack(
            side='left', padx=4)
        ttk.Button(f5, text='Экспорт base64…', command=self.export_pattern).pack(
            side='left', padx=4)
        ttk.Button(f5, text='Сохранить проект…', command=self.save_project).pack(
            side='left', padx=4)
        ttk.Button(f5, text='Открыть проект…', command=self.load_project).pack(
            side='left', padx=4)

        f6 = ttk.Frame(self)
        f6.pack(fill='x', padx=8, pady=4)
        ttk.Button(f6, text='Сгенерировать установщик (.sh)…',
                   command=self.generate).pack(side='left', padx=4)
        ttk.Button(f6, text='Скрипт восстановления…',
                   command=self.restore).pack(side='left', padx=4)

        f7 = ttk.LabelFrame(self, text='Журнал')
        f7.pack(fill='both', expand=True, padx=8, pady=(2, 8))
        self.log = tk.Text(f7, height=8, state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True, padx=4, pady=4)

    # ---------- журнал и фоновые задачи ----------

    def log_print(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def log_bg(self, text):
        self.after(0, self.log_print, text)

    def _bg(self, fn, *args):
        def worker():
            try:
                fn(*args)
            except Exception as e:
                self.log_bg('Ошибка: %s' % e)
        threading.Thread(target=worker, daemon=True).start()

    def _ssh_call(self, stdin_text, cmd='sh -s'):
        host = self.ip_entry.get().strip()
        if not host:
            raise ValueError('Укажите IP или имя хоста колонки')
        try:
            port = int(self.port_spin.get())
        except ValueError:
            raise ValueError('Порт: целое число от 1 до 65535')
        if not 1 <= port <= 65535:
            raise ValueError('Порт: целое число от 1 до 65535')
        user = self.user_entry.get().strip() or 'root'
        password = self.pass_entry.get()
        if password and HAS_PARAMIKO:
            return ssh_run_paramiko(host, port, user, password, stdin_text, cmd)
        return ssh_run_subprocess(host, port, user, stdin_text, cmd)

    def _report(self, code, out, err, done_marker):
        for line in out.strip().splitlines():
            self.log_bg('  ' + line)
        if err.strip():
            for line in err.strip().splitlines():
                self.log_bg('  stderr: ' + line)
        if code != 0:
            raise RuntimeError('команда завершилась с кодом %d' % code)
        if done_marker and done_marker not in out:
            raise RuntimeError('удалённая сторона не подтвердила выполнение')

    def _do_check(self):
        self.log_bg('Проверка подключения %s@%s:%s...'
                    % (self.user_entry.get().strip() or 'root',
                       self.ip_entry.get().strip(), self.port_spin.get()))
        code, out, err = self._ssh_call(PREFLIGHT_BODY)
        self._report(code, out, err, 'PREFLIGHT_OK')
        self.log_bg('Подключение и проверки пройдены.')

    def _do_install(self):
        try:
            payloads, hashes, counts = build_patterns(
                self.patterns, self.brightness_value(), self.speed_value())
        except ValueError as e:
            self.log_bg('Ошибка: %s' % e)
            return
        self.log_bg('Установка паттернов на %s...' % self.ip_entry.get().strip())
        script = build_remote_install(payloads, hashes, counts)
        code, out, err = self._ssh_call(script)
        self._report(code, out, err, 'INSTALL_DONE')
        for line in out.splitlines():
            if line.startswith('BACKUP_DIR='):
                self.log_bg('Бэкап стоковых паттернов: %s' % line.split('=', 1)[1])
        self.log_bg('Готово. Если SSH-сессия была активна — переподключитесь.')

    def _do_restart(self):
        self.log_bg('Перезапуск Quasar...')
        code, out, err = self._ssh_call(REMOTE_RESTART)
        self._report(code, out, err, 'RESTART_DONE')

    def _do_restore(self):
        backup = simpledialog.askstring(
            'Восстановление',
            'Путь к каталогу бэкапа на устройстве\n(например '
            '/data/quasar/rgb-alice-backup-20260101-120000-123):',
            parent=self)
        if not backup:
            return
        self.log_bg('Восстановление из %s...' % backup)
        code, out, err = self._ssh_call(
            RESTORE_BODY, cmd="sh -s '%s'" % backup.strip().replace("'", ""))
        self._report(code, out, err, 'RESTORE_DONE')

    # ---------- создатель кадров ----------

    def draw_swatch(self, name):
        try:
            color = '#' + rgb_to_hex(hex_to_rgb(self.main_entry[name].get()))
        except ValueError:
            color = '#000000'
        self.swatches[name].configure(bg=color)

    def pick_color(self, name):
        rgb_, hexstr = colorchooser.askcolor(parent=self)
        if hexstr:
            self.main_entry[name].delete(0, 'end')
            self.main_entry[name].insert(0, hexstr.lstrip('#').upper())
            self.draw_swatch(name)

    def creator_values(self, name):
        main = hex_to_rgb(self.main_entry[name].get())
        overrides = [hex_to_rgb(z) if z else None
                     for z in (e.get().strip() for e in self.zone_entries[name])]
        return main, overrides, self.creator_keep[name].get()

    def apply_creator(self):
        try:
            built = {}
            for name in STATES:
                main, overrides, keep = self.creator_values(name)
                frames = parse_payload(ORIGINAL_PAYLOADS[name])
                built[name] = recolor_frames(frames, main, keep, overrides)
        except ValueError as e:
            messagebox.showerror('Ошибка', str(e), parent=self)
            return
        self.patterns.update(built)
        self.edit_idx = 0
        self.refresh_editor()
        self.rebuild_preview()
        self.log_print('Кадры созданы по цветам из «Создателя кадров»:')
        for name in STATES:
            self.log_print('  %9s: %d кадров' % (name, len(self.patterns[name])))

    # ---------- редактор ----------

    def cur_state(self):
        return self.state_var.get()

    def cur_frames(self):
        return self.patterns[self.cur_state()]

    def on_state_changed(self):
        self.edit_idx = 0
        self.refresh_editor()
        self.rebuild_preview()

    def refresh_editor(self):
        frames = self.cur_frames()
        self.edit_idx = max(0, min(self.edit_idx, len(frames) - 1))
        lb = self.frame_list
        lb.delete(0, 'end')
        for i, (colors, dur) in enumerate(frames):
            summary = ' '.join(rgb_to_hex(c) for c in colors[:3])
            lb.insert('end', 'кадр %2d: %3d ms  %s …' % (i + 1, dur, summary))
        lb.selection_clear(0, 'end')
        lb.selection_set(self.edit_idx)
        self.show_frame_detail()

    def on_frame_selected(self):
        sel = self.frame_list.curselection()
        if sel:
            self.edit_idx = sel[0]
            self.show_frame_detail()
            if self.preview_frames:
                self.draw_preview_frame()

    def show_frame_detail(self):
        frames = self.cur_frames()
        self.edit_idx = max(0, min(self.edit_idx, len(frames) - 1))
        colors, dur = frames[self.edit_idx]
        self.frame_title.configure(
            text='Кадр %d из %d' % (self.edit_idx + 1, len(frames)))
        for z in range(ZONES):
            self.zone_btns[z].configure(bg='#' + rgb_to_hex(colors[z]),
                                        text=rgb_to_hex(colors[z]))
        self.dur_entry.delete(0, 'end')
        self.dur_entry.insert(0, str(dur))

    def pick_zone(self, z):
        rgb_, hexstr = colorchooser.askcolor(parent=self)
        if not hexstr:
            return
        frames = self.cur_frames()
        colors, dur = frames[self.edit_idx]
        colors = list(colors)
        colors[z] = hex_to_rgb(hexstr)
        frames[self.edit_idx] = (tuple(colors), dur)
        self.refresh_editor()
        self.rebuild_preview()

    def apply_duration(self):
        try:
            v = int(self.dur_entry.get())
        except ValueError:
            messagebox.showerror('Ошибка', 'Длительность: целое число 1–255',
                                 parent=self)
            return
        v = max(1, min(255, v))
        frames = self.cur_frames()
        colors, _ = frames[self.edit_idx]
        frames[self.edit_idx] = (colors, v)
        self.refresh_editor()
        self.rebuild_preview()

    def add_frame(self):
        frames = self.cur_frames()
        colors, dur = frames[self.edit_idx]
        frames.insert(self.edit_idx + 1, (tuple(colors), dur))
        self.edit_idx += 1
        self.refresh_editor()
        self.rebuild_preview()

    def del_frame(self):
        frames = self.cur_frames()
        if len(frames) <= 1:
            messagebox.showinfo('Удаление', 'Последний кадр удалить нельзя',
                                parent=self)
            return
        del frames[self.edit_idx]
        self.edit_idx = max(0, self.edit_idx - 1)
        self.refresh_editor()
        self.rebuild_preview()

    def _move(self, delta):
        frames = self.cur_frames()
        i, j = self.edit_idx, self.edit_idx + delta
        if 0 <= j < len(frames):
            frames[i], frames[j] = frames[j], frames[i]
            self.edit_idx = j
            self.refresh_editor()
            self.rebuild_preview()

    def move_up(self):
        self._move(-1)

    def move_down(self):
        self._move(1)

    # ---------- фото и предпросмотр ----------

    def get_ring_params(self):
        params = {}
        for key in ('cx', 'cy', 'rx', 'ry', 'thick'):
            params[key] = float(self.ring_vars[key].get()) / 100.0
        for key, v in params.items():
            if not 0 < v <= 2:
                raise ValueError('Параметры кольца: проценты от 1 до 200')
        return params

    def load_photo(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[('Изображения', '*.png;*.jpg;*.jpeg'),
                       ('Все файлы', '*.*')])
        if path:
            self._set_photo(path)
            self.rebuild_preview()

    def _set_photo(self, path):
        if not HAS_PIL:
            self.photo_status.configure(
                text='Pillow не установлена — предпросмотр на фото недоступен')
            return
        try:
            img = Image.open(path).convert('RGB')
        except Exception as e:
            messagebox.showerror('Ошибка',
                                 'Не удалось открыть фото: %s' % e, parent=self)
            return
        scale = min(CANVAS_W / img.width, CANVAS_H / img.height, 1.0)
        if scale < 1.0:
            resample = getattr(Image, 'LANCZOS', None)
            if resample is None:
                resample = Image.Resampling.LANCZOS
            img = img.resize((max(1, round(img.width * scale)),
                              max(1, round(img.height * scale))), resample)
        self.photo_img = img
        self.photo_status.configure(
            text='Фото: %s (%dx%d)' % (os.path.basename(path),
                                       img.width, img.height))

    def _load_default_photo(self):
        base = os.path.dirname(os.path.abspath(__file__))
        for name in PHOTO_CANDIDATES:
            p = os.path.join(base, name)
            if os.path.exists(p):
                self._set_photo(p)
                return

    def brightness_value(self):
        try:
            v = int(float(self.brightness.get()))
        except ValueError:
            raise ValueError('Яркость: число от 1 до 100')
        if not 1 <= v <= 100:
            raise ValueError('Яркость: число от 1 до 100')
        return v

    def speed_value(self):
        try:
            v = float(self.speed.get())
        except ValueError:
            raise ValueError('Скорость: число от 0.1 до 10')
        if not 0.1 <= v <= 10:
            raise ValueError('Скорость: число от 0.1 до 10')
        return v

    def rebuild_preview(self):
        if self.preview_job:
            self.after_cancel(self.preview_job)
            self.preview_job = None
        try:
            self.preview_frames = scale_frames(
                self.cur_frames(), self.brightness_value(), self.speed_value())
        except ValueError as e:
            self.preview_frames = None
            self.canvas.delete('all')
            self.canvas.create_text(CANVAS_W // 2, CANVAS_H // 2, text=str(e),
                                    fill='#ff8888')
            return
        self.preview_idx = 0
        self.draw_preview_frame()
        if self.playing:
            self.preview_job = self.after(1, self._tick)

    def draw_preview_frame(self):
        if not self.preview_frames:
            return
        colors, _ = self.preview_frames[self.preview_idx]
        if HAS_PIL and self.photo_img:
            try:
                params = self.get_ring_params()
            except ValueError as e:
                self.photo_status.configure(text=str(e))
                return
            frame_img = render_photo_frame(self.photo_img, params, colors)
            self._preview_tk = ImageTk.PhotoImage(frame_img)
            self.canvas.delete('all')
            self.canvas.create_image(CANVAS_W // 2, CANVAS_H // 2,
                                     image=self._preview_tk)
        else:
            self._draw_fallback(colors)

    def _draw_fallback(self, colors):
        c = self.canvas
        c.delete('all')
        c.create_oval(CANVAS_W / 2 - 190, CANVAS_H / 2 - 105,
                      CANVAS_W / 2 + 190, CANVAS_H / 2 + 105,
                      fill='#2b2b30', outline='#18181c')
        try:
            p = self.get_ring_params()
        except ValueError:
            p = {'cx': 0.48, 'cy': 0.47, 'rx': 0.145, 'ry': 0.24, 'thick': 0.35}
        cx, cy = p['cx'] * CANVAS_W, p['cy'] * CANVAS_H
        rx, ry = p['rx'] * CANVAS_W, p['ry'] * CANVAS_H
        thick = max(2, int(p['thick'] * min(rx, ry)))
        bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
        for i, col in enumerate(colors):
            c.create_arc(bbox, start=-90 + i * 60, extent=60, style='arc',
                         width=thick, outline='#' + rgb_to_hex(col))
        c.create_oval(cx - rx * 0.55, cy - ry * 0.55,
                      cx + rx * 0.55, cy + ry * 0.55,
                      fill='#26262a', outline='')

    def toggle_preview(self):
        if self.playing:
            self.playing = False
            if self.preview_job:
                self.after_cancel(self.preview_job)
                self.preview_job = None
            self.btn_play.configure(text='Старт')
        else:
            self.playing = True
            self.btn_play.configure(text='Стоп')
            self._tick()

    def _tick(self):
        if not (self.playing and self.preview_frames):
            return
        dur = self.preview_frames[self.preview_idx][1]
        self.preview_idx = (self.preview_idx + 1) % len(self.preview_frames)
        self.draw_preview_frame()
        self.preview_job = self.after(max(16, dur), self._tick)

    # ---------- импорт/экспорт/проект ----------

    def import_pattern(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[('Паттерн / base64', '*.led;*.txt;*.b64'),
                       ('Все файлы', '*.*')])
        if not path:
            return
        try:
            with open(path, 'r', encoding='ascii') as f:
                raw = f.read().strip()
            if raw.startswith('loop'):
                frames = parse_payload_text(raw)
            else:
                frames = parse_payload(raw)
        except Exception as e:
            messagebox.showerror('Ошибка',
                                 'Не удалось разобрать паттерн: %s' % e,
                                 parent=self)
            return
        self.patterns[self.cur_state()] = frames
        self.edit_idx = 0
        self.refresh_editor()
        self.rebuild_preview()
        self.log_print('Импортирован паттерн %s: %d кадров'
                       % (self.cur_state(), len(frames)))

    def export_pattern(self):
        payload, _ = build_payload(self.cur_frames())
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension='.b64',
            initialfile=self.cur_state() + '.b64',
            filetypes=[('base64', '*.b64'), ('Все файлы', '*.*')])
        if not path:
            return
        with open(path, 'w', encoding='ascii', newline='\n') as f:
            f.write(payload)
        self.log_print('Экспортирован %s: %s' % (self.cur_state(), path))

    def save_project(self):
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension='.json',
            initialfile='led_project.json',
            filetypes=[('JSON', '*.json')])
        if not path:
            return
        data = {}
        for name in STATES:
            data[name] = [[['%02X%02X%02X' % tuple(c) for c in colors], dur]
                          for colors, dur in self.patterns[name]]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        self.log_print('Проект сохранён: %s' % path)

    def load_project(self):
        path = filedialog.askopenfilename(
            parent=self, filetypes=[('JSON', '*.json'), ('Все файлы', '*.*')])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for name in STATES:
                frames = []
                for colors, dur in data[name]:
                    if len(colors) != ZONES:
                        raise ValueError('у кадра должно быть 6 зон')
                    frames.append((tuple(hex_to_rgb(c) for c in colors), int(dur)))
                self.patterns[name] = frames
        except Exception as e:
            messagebox.showerror('Ошибка', 'Не удалось открыть проект: %s' % e,
                                 parent=self)
            return
        self.edit_idx = 0
        self.refresh_editor()
        self.rebuild_preview()
        self.log_print('Проект загружен: %s' % path)

    # ---------- генерация ----------

    def generate(self):
        try:
            script, hashes, counts = generate_script(
                self.patterns, self.brightness_value(), self.speed_value())
        except Exception as e:
            messagebox.showerror('Ошибка', str(e), parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension='.sh', initialfile='install_led.sh',
            filetypes=[('Shell script', '*.sh'), ('Все файлы', '*.*')])
        if not path:
            return
        with open(path, 'w', encoding='ascii', newline='\n') as f:
            f.write(script)
        self.log_print('Установщик записан: %s' % path)
        for name in STATES:
            self.log_print('  %9s: %d кадров, sha256=%s'
                           % (name, counts[name], hashes[name]))
        self.log_print('Запуск: sh %s [ssh-host]' % path)

    def restore(self):
        backup = simpledialog.askstring(
            'Скрипт восстановления',
            'Путь к каталогу бэкапа на устройстве\n(например '
            '/data/quasar/rgb-alice-backup-20260101-120000-123):',
            parent=self)
        if not backup:
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension='.sh', initialfile='restore_led.sh',
            filetypes=[('Shell script', '*.sh'), ('Все файлы', '*.*')])
        if not path:
            return
        with open(path, 'w', encoding='ascii', newline='\n') as f:
            f.write(generate_restore(backup))
        self.log_print('Скрипт восстановления записан: %s' % path)


if __name__ == '__main__':
    App().mainloop()
