import flet as ft
import httpx
import threading
import time
import subprocess
import sys
import os
import atexit

_api_proc = None

def _start_api():
    global _api_proc
    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable
    _api_proc = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "api:app", "--port", "8000", "--log-level", "warning"],
        cwd=script_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)

def _stop_api():
    global _api_proc
    if _api_proc and _api_proc.poll() is None:
        _api_proc.terminate()
        try:
            _api_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _api_proc.kill()

atexit.register(_stop_api)
_start_api()

# ── Variant 20 colours
PRIMARY   = "#1B5E20"   # AppBar background
PAGE_BG   = "#DDE9DA"   # Page background
HEADER_BG = "#2D2D3F"   # Table header
POST_BTN  = "#1B5E20"   # POST Add button
DEL_BTN   = "#B92626"   # DELETE button  (fixed for all variants)
SNACK_BG  = "#242436"   # Snackbar/banner (fixed for all variants)
TEXTBOX   = "#EAEACD"   # Text-box container background
ROW_ODD   = "#E8F5E9"   # Odd data rows
ROW_EVEN  = "#FFFFFF"   # Even data rows
TEXT_DK   = "#212121"
TEXT_SEC  = "#757575"
API_LABEL = "#1B5E20"

BASE_URL  = "http://127.0.0.1:8000"

COL_STYLE = ft.TextStyle(color="white", weight=ft.FontWeight.BOLD, size=13)


def make_tf(label):
    return ft.TextField(
        label=label,
        expand=True,
        border_color="#81C784",
        focused_border_color=PRIMARY,
        bgcolor=TEXTBOX,
        text_size=13,
        color=TEXT_DK,
        cursor_color=PRIMARY,
        label_style=ft.TextStyle(color="#4CAF50"),
    )


def api_get():
    try:
        r = httpx.get(f"{BASE_URL}/volunteers", timeout=5)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Server baghlantisi yoxdur. api.py-ni ishlet."
    except Exception as ex:
        return None, str(ex)


def api_post(payload: dict):
    try:
        r = httpx.post(f"{BASE_URL}/volunteers", json=payload, timeout=5)
        if r.status_code == 400:
            return None, r.json().get("detail", "Xeta")
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Server baghlantisi yoxdur."
    except Exception as ex:
        return None, str(ex)


def api_delete(volunteer_id: int):
    try:
        r = httpx.delete(f"{BASE_URL}/volunteers/{volunteer_id}", timeout=5)
        if r.status_code == 404:
            return None, r.json().get("detail", "Tapilmadi")
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, "Server baghlantisi yoxdur."
    except Exception as ex:
        return None, str(ex)


# WINDOW 2 — Add / Delete  (POST & DELETE via FastAPI)
def window2(page: ft.Page, go_back):

    tf_id    = make_tf("VolunteerID")
    tf_name  = make_tf("FullName")
    tf_skill = make_tf("Skills")
    tf_phone = make_tf("Phone")

    banner = ft.Container(
        visible=False,
        bgcolor=SNACK_BG,
        border_radius=8,
        padding=ft.padding.symmetric(vertical=12, horizontal=16),
        content=ft.Row(spacing=8, controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE, color="white", size=18),
            ft.Text("", color="white", weight=ft.FontWeight.BOLD, size=13),
        ]),
    )

    table_col = ft.Ref[ft.Column]()

    def build_table(rows):
        return ft.DataTable(
            expand=True,
            width=float("inf"),
            bgcolor=ft.Colors.TRANSPARENT,
            border=ft.border.all(0, "transparent"),
            heading_row_color=HEADER_BG,
            heading_row_height=40,
            data_row_min_height=36,
            data_row_max_height=48,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("VolunteerID", style=COL_STYLE)),
                ft.DataColumn(ft.Text("FullName",    style=COL_STYLE)),
                ft.DataColumn(ft.Text("Skills",      style=COL_STYLE)),
                ft.DataColumn(ft.Text("Phone",       style=COL_STYLE)),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(r.get("VolunteerID", "")), color=TEXT_DK, size=13)),
                        ft.DataCell(ft.Text(str(r.get("FullName",    "")), color=TEXT_DK, size=13)),
                        ft.DataCell(ft.Text(str(r.get("Skills",      "")), color=TEXT_DK, size=13)),
                        ft.DataCell(ft.Text(str(r.get("Phone",       "")), color=TEXT_DK, size=13)),
                    ],
                    color=ROW_ODD if i % 2 == 0 else ROW_EVEN,
                )
                for i, r in enumerate(rows)
            ],
        )

    def refresh_table():
        data, err = api_get()
        if err:
            show_banner(err, is_error=True)
            return
        table_col.current.controls = [build_table(data)]
        page.update()

    def clear_form():
        for f in [tf_id, tf_name, tf_skill, tf_phone]:
            f.value = ""
            f.error_text = None

    def show_banner(msg: str, is_error=False):
        banner.bgcolor = "#C62828" if is_error else SNACK_BG
        banner.content.controls[0].name = ft.Icons.ERROR if is_error else ft.Icons.CHECK_CIRCLE
        banner.content.controls[1].value = msg
        banner.visible = True
        page.update()
        def hide():
            time.sleep(3)
            banner.visible = False
            page.update()
        threading.Thread(target=hide, daemon=True).start()

    def post_add(e):
        for f in [tf_id, tf_name, tf_skill, tf_phone]:
            f.error_text = None
        if not tf_id.value or not tf_name.value:
            tf_id.error_text   = "Teleb olunur" if not tf_id.value   else None
            tf_name.error_text = "Teleb olunur" if not tf_name.value else None
            page.update()
            return
        try:
            new_id = int(tf_id.value)
        except ValueError:
            tf_id.error_text = "Reqem olmalidir"
            page.update()
            return

        payload = {
            "VolunteerID": new_id,
            "FullName":    tf_name.value,
            "Skills":      tf_skill.value,
            "Phone":       tf_phone.value,
        }
        result, err = api_post(payload)
        if err:
            show_banner(err, is_error=True)
            return
        clear_form()
        refresh_table()
        show_banner("Record added / deleted successfully!")

    def do_delete(e):
        tf_id.error_text = None
        if not tf_id.value:
            tf_id.error_text = "ID daxil et"
            page.update()
            return
        try:
            del_id = int(tf_id.value)
        except ValueError:
            tf_id.error_text = "Reqem olmalidir"
            page.update()
            return
        result, err = api_delete(del_id)
        if err:
            show_banner(err, is_error=True)
            return
        clear_form()
        refresh_table()
        show_banner("Record added / deleted successfully!")

    init_data, _ = api_get()
    init_rows = init_data if init_data else []

    content = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            # ── AppBar
            ft.Container(
                bgcolor=PRIMARY,
                padding=ft.padding.symmetric(horizontal=8, vertical=10),
                content=ft.Row([
                    ft.ElevatedButton(
                        "← Back",
                        bgcolor="#2E7D32", color="white",
                        height=36,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                        on_click=lambda _: go_back(),
                    ),
                    ft.Text("Add Volunteer", color="white", size=18,
                            weight=ft.FontWeight.BOLD, expand=True,
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(width=80),
                ]),
            ),

            ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
                controls=[
                    ft.Container(
                        padding=ft.padding.all(14),
                        content=ft.Column(spacing=10, controls=[

                            ft.Text("Table: Volunteers — GET /volunteers",
                                    color=API_LABEL, weight=ft.FontWeight.BOLD, size=13),
                            ft.ProgressBar(value=1, color=PRIMARY, bgcolor="#A5D6A7"),

                            ft.Container(
                                border=ft.border.all(1, "#A5D6A7"),
                                border_radius=8,
                                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                                content=ft.Row(expand=True, controls=[
                                    ft.Column(
                                        ref=table_col,
                                        expand=True,
                                        controls=[build_table(init_rows)],
                                    ),
                                ]),
                            ),

                            ft.Divider(height=6, color=ft.Colors.TRANSPARENT),

                            ft.Text("Add New Record — POST /volunteers",
                                    color=API_LABEL, weight=ft.FontWeight.BOLD, size=13),

                            ft.Row([tf_id,    tf_name],  spacing=10),
                            ft.Row([tf_skill, tf_phone], spacing=10),

                            ft.Divider(height=4, color=ft.Colors.TRANSPARENT),

                            ft.Row(spacing=10, controls=[
                                ft.ElevatedButton(
                                    "POST Add", expand=True,
                                    bgcolor=POST_BTN, color="white", height=46,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                    on_click=post_add,
                                ),
                                ft.ElevatedButton(
                                    "DELETE", expand=True,
                                    bgcolor=DEL_BTN, color="white", height=46,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                    on_click=do_delete,
                                ),
                            ]),

                            banner,
                        ]),
                    ),
                ],
            ),
        ],
    )

    return content


# WINDOW 1 — Main  (GET data from FastAPI)
def window1(page: ft.Page, go_to_add):

    bs_title    = ft.Text("", color=PRIMARY, weight=ft.FontWeight.BOLD, size=14)
    bs_subtitle = ft.Text("", color=TEXT_DK, size=13)
    bs_hint     = ft.Text("Tap drag handle to expand full details",
                          color=TEXT_SEC, italic=True, size=11)

    bottom_sheet = ft.BottomSheet(
        open=False,
        dismissible=True,
        bgcolor="white",
        content=ft.Container(
            padding=ft.padding.only(left=20, top=8, right=20, bottom=24),
            content=ft.Column(tight=True, controls=[
                ft.Container(height=4),
                bs_title,
                ft.Container(height=4),
                bs_subtitle,
                ft.Container(height=6),
                bs_hint,
            ]),
        ),
        on_dismiss=lambda e: None,
    )
    page.overlay.append(bottom_sheet)

    def open_bs(row_data: dict):
        name  = row_data.get("FullName", "")
        skill = row_data.get("Skills", "")
        phone = row_data.get("Phone", "")
        bs_title.value    = "▼ BOTTOM SHEET"
        bs_subtitle.value = f"{name} - {skill} - Available"
        bottom_sheet.open = True
        page.update()

    def build_clickable_table(rows):
        data_rows = []
        for i, r in enumerate(rows):
            rd = r
            data_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(rd.get("VolunteerID", "")), color=TEXT_DK, size=13)),
                        ft.DataCell(ft.Text(str(rd.get("FullName",    "")), color=TEXT_DK, size=13)),
                        ft.DataCell(ft.Text(str(rd.get("Skills",      "")), color=TEXT_DK, size=13)),
                        ft.DataCell(ft.Text(str(rd.get("Phone",       "")), color=TEXT_DK, size=13)),
                    ],
                    color=ROW_ODD if i % 2 == 0 else ROW_EVEN,
                    on_select_changed=lambda e, d=rd: open_bs(d),
                )
            )
        return ft.DataTable(
            expand=True,
            width=float("inf"),
            bgcolor=ft.Colors.TRANSPARENT,
            border=ft.border.all(0, "transparent"),
            heading_row_color=HEADER_BG,
            heading_row_height=40,
            data_row_min_height=36,
            data_row_max_height=48,
            column_spacing=16,
            columns=[
                ft.DataColumn(ft.Text("Volunteer", style=COL_STYLE)),
                ft.DataColumn(ft.Text("FullName",  style=COL_STYLE)),
                ft.DataColumn(ft.Text("Skills",    style=COL_STYLE)),
                ft.DataColumn(ft.Text("Phone",     style=COL_STYLE)),
            ],
            rows=data_rows,
        )

    table_col  = ft.Ref[ft.Column]()
    body       = ft.Ref[ft.Container]()
    err_text   = ft.Ref[ft.Text]()
    total_text = ft.Ref[ft.Text]()

    def refresh_main_table():
        data, err = api_get()
        if err:
            if err_text.current:
                err_text.current.value = err
                err_text.current.visible = True
        else:
            if err_text.current:
                err_text.current.visible = False
            if table_col.current:
                table_col.current.controls = [build_clickable_table(data)]
            if total_text.current and data is not None:
                total_text.current.value = f"Total Volunteers: {len(data)}"
        page.update()

    def volunteers_view():
        init_data, init_err = api_get()
        init_rows = init_data if init_data else []
        total_count = len(init_rows) if init_rows else 0

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
            controls=[
                ft.Container(
                    bgcolor="#C8E6C9", border_radius=6,
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    content=ft.Text("GET /volunteers  ->  loads data from FastAPI",
                                    color=PRIMARY, size=11),
                ),
                ft.ProgressBar(value=1, color=PRIMARY, bgcolor="#A5D6A7"),

                ft.Text(
                    ref=err_text,
                    value=init_err or "",
                    color="#C62828", size=12,
                    visible=bool(init_err),
                ),

                ft.Container(
                    border=ft.border.all(1, "#A5D6A7"),
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Row(expand=True, controls=[
                        ft.Column(
                            ref=table_col,
                            expand=True,
                            controls=[build_clickable_table(init_rows)],
                        ),
                    ]),
                ),

                # Text widget — Total Volunteers
                ft.Container(
                    bgcolor=TEXTBOX,
                    border_radius=8,
                    border=ft.border.all(1, "#A5D6A7"),
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Column(spacing=2, controls=[
                        ft.Text("Text widget — Total Volunteers",
                                color=TEXT_SEC, size=10, italic=True),
                        ft.Text(
                            ref=total_text,
                            value=f"Total Volunteers: {total_count}",
                            color=PRIMARY,
                            weight=ft.FontWeight.BOLD,
                            size=15,
                        ),
                    ]),
                ),
            ],
        )

    def projects_view():
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Container(height=40),
                ft.Icon(ft.Icons.FOLDER_SPECIAL, size=56, color=PRIMARY),
                ft.Text("Projects", size=18, color=TEXT_SEC),
                ft.Text("Projects list will be shown here.",
                        color=TEXT_SEC, size=13, text_align=ft.TextAlign.CENTER),
            ],
        )

    def assignments_view():
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Container(height=40),
                ft.Icon(ft.Icons.ASSIGNMENT, size=56, color=PRIMARY),
                ft.Text("Assignments", size=18, color=TEXT_SEC),
                ft.Text("Assignments list will be shown here.",
                        color=TEXT_SEC, size=13, text_align=ft.TextAlign.CENTER),
            ],
        )

    views = [volunteers_view, projects_view, assignments_view]

    def on_nav_change(e):
        idx = e.control.selected_index
        body.current.content = views[idx]()
        if idx == 0:
            refresh_main_table()
        else:
            page.update()

    content = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            # ── AppBar
            ft.Container(
                bgcolor=PRIMARY,
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                content=ft.Row([
                    ft.Text("VolunteerApp", color="white", size=18,
                            weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(icon=ft.Icons.PERSON_ADD, icon_color="white",
                                  on_click=lambda _: go_to_add(),
                                  tooltip="Add Volunteer"),
                ]),
            ),

            ft.Container(
                ref=body,
                expand=True,
                padding=ft.padding.all(14),
                content=volunteers_view(),
            ),

            ft.NavigationBar(
                selected_index=0,
                bgcolor="white",
                indicator_color="#C8E6C9",
                on_change=on_nav_change,
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.PEOPLE,     label="Volunteers"),
                    ft.NavigationBarDestination(icon=ft.Icons.FOLDER_SPECIAL, label="Projects"),
                    ft.NavigationBarDestination(icon=ft.Icons.ASSIGNMENT,  label="Assignments"),
                ],
            ),
        ],
    )

    return content, refresh_main_table


# MAIN
def main(page: ft.Page):
    page.title         = "VolunteerApp"
    page.bgcolor       = PAGE_BG
    page.padding       = 0
    page.window_width  = 420
    page.window_height = 780

    root = ft.Ref[ft.Stack]()

    def go_to_add():
        root.current.controls[1].visible = True
        root.current.controls[0].visible = False
        page.update()

    def go_back():
        root.current.controls[0].visible = True
        root.current.controls[1].visible = False
        refresh_w1()
        page.update()

    w1, refresh_w1 = window1(page, go_to_add)
    w2 = window2(page, go_back)

    page.add(
        ft.Stack(
            ref=root,
            expand=True,
            controls=[
                ft.Container(content=w1, expand=True, visible=True),
                ft.Container(content=w2, expand=True, visible=False),
            ],
        )
    )


ft.app(target=main)
