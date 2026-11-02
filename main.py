import threading
import requests
import img2pdf
import FreeSimpleGUI as sg


# ===== FUNCTIONS ===== #

def get_publication(window,
                    login,
                    password,
                    publication_url,
                    publication_name):

    publication_number = publication_url.split("id=")[1].split("&")[0]  # Номер публикации
    page_number = -2                                                    # Начальный номер страницы
    page_list = []                                                      # Список для сохранения контента страниц

    # КОНТЕНТ 401
    url = (f"https://lib.msk.misis.ru/"                                 # Url для запроса контента страницы с ошибкой 401 - Unauthorized
           f"elib/libs/view.php?id=1&page=0&type=large/fast")
    unauthorized_content = requests.get(url).content                    # Контент, который будет на странице если возникнет ошибка 401 - Unauthorized

    # СОЗДАНИЕ СЕССИИ
    s = requests.Session()                                              # Создаем сессию

    s.post("https://lib.msk.misis.ru/elib/login.php",               # Авторизуемся в сессии
           data={"login": login,                                        # Номер студенческого/пропуска/личного дела - Логин
                 "password": password,                                  # Полное имя с большой буквы - Пароль
                 "language": "ru"})                                     # Язык

    # ЦИКЛ
    while True:
        page_number += 1                                                # Увеличиваем номер страницы на один

        window.write_event_value(                                       # !!! Отправляем событие в основной поток
            "-PAGE-",
            f"Cкачивается страница {page_number}"
        )

        url = (f"https://lib.msk.misis.ru/elib/libs/view.php?"          # Url страницы
               f"id={publication_number}&"                              # Номер публикации
               f"page={page_number}&"                                   # Номер страницы
               f"type=large/fast")

        content = s.get(url).content                                    # Делаем запрос по Url

        if page_number < 0:                                             # Если номер страницы отрицательный, то будет возвращен контент, соответствующий ошибке 404 - Not Found
            not_found_content = content                                 # Сохраняем контент 404 в переменную
            continue                                                    # Переходим к следующей итерации цикла

        if content == unauthorized_content:                             # Если контент 401
            window.write_event_value(                                   # !!! Отправляем событие в основной поток
                "-PAGE-",
                "Недостаточно прав на скачивание"
            )
            break                                                       # Выходим из цикла

        elif content == not_found_content:                              # Если контент страницы 404
            window.write_event_value(                                   # !!! Отправляем событие в основной поток
                "-PAGE-",
                f"Скачивание завршено\nфайл сохранен - "
                f"{publication_name}.pdf"
            )
            break                                                       # Выходим из цикла

        else:                                                           # Если все проверки пройдены
            page_list.append(content)                                   # Сохраняем страницу в список

    # ПОСЛЕ ЦИКЛА
    with open(f"{publication_name}.pdf", "wb") as f:                    # Открываем файл pdf в режиме записи байтов
        f.write(img2pdf.convert(page_list))                             # Конвертируем список контента файл


# ============================== PROGRAM ============================== #

# Setting font for application
sg.set_options(font=("Helvetica", 14))


# ===== ОБРАБОТЧИК CTRL+V / CTRL+C / CTRL+X ДЛЯ РУССКОЙ РАСКЛАДКИ ===== #
def _on_key_release(event):
    """Обход бага Tkinter: Ctrl+V/C/X не работают при русской раскладке."""
    ctrl = (event.state & 0x4) != 0
    # 86 — V, 67 — C, 88 — X (аппаратные коды клавиш)
    # Проверяем, что keysym не совпадает с латинской буквой — значит раскладка не английская
    if event.keycode == 86 and ctrl and event.keysym.lower() != "v":
        event.widget.event_generate("<<Paste>>")
    if event.keycode == 67 and ctrl and event.keysym.lower() != "c":
        event.widget.event_generate("<<Copy>>")
    if event.keycode == 88 and ctrl and event.keysym.lower() != "x":
        event.widget.event_generate("<<Cut>>")


# ===== LAYOUT ===== #
layout = [
    [sg.Text("Введите номер студенческого билета")],
    [sg.Text("Например: 3000001")],
    [sg.Input(key="-LOGIN-", expand_x=True)],
    [sg.Text()],
    [sg.Text("Введите свое имя")],
    [sg.Text("Например: Иван")],
    [sg.Input(key="-PASSWORD-", expand_x=True)],
    [sg.Text()],
    [sg.Text("Введите ссылку на публикацию")],
    [sg.Text("Например: https://lib.msk.misis.ru/elib/view.php?id=10000")],
    [sg.Input(key="-URL-", expand_x=True)],
    [sg.Text()],
    [sg.Text("Введите название публикации")],
    [sg.Text("Например: Рассчет цепей постоянного тока")],
    [sg.Input(key="-NAME-", expand_x=True)],
    [sg.Text()],
    [sg.Text("", key="-PAGE-", visible=False)],
    [sg.Text()],
    [sg.Button("Скачать"), sg.Button("Выход")]
]

# ===== WINDOW ===== #
window = sg.Window("Пример ввода", layout, finalize=True, icon="misis_logo.ico")

# Привязываем обработчик ко всем виджетам окна (для работы Ctrl+V при русской раскладке)
window.TKroot.bind_all("<KeyRelease>", _on_key_release, "+")


# ===== EVENT LOOP ===== #
while True:
    event, values = window.read()
    if event in (sg.WIN_CLOSED, "Выход"):
        break

    if event == "Скачать":
        threading.Thread(                                               # !!!
            target=get_publication,
            args=(window,
                  values["-LOGIN-"],
                  values["-PASSWORD-"],
                  values["-URL-"],
                  values["-NAME-"]),
            daemon=True
        ).start()

    if event == "-PAGE-":
        # Это событие приходит из потока — здесь безопасно обновлять GUI
        window["-PAGE-"].update(f"{values[event]}", visible=True)


window.close()