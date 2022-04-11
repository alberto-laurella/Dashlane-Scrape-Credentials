import selenium.common.exceptions
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import tkinter as tk

from pynput.keyboard import Key, KeyCode, Listener
from threading import Timer

from win32gui import GetForegroundWindow, ShowWindow, IsWindowVisible, IsWindowEnabled, EnumWindows
from win32process import GetWindowThreadProcessId
from win32clipboard import OpenClipboard, EmptyClipboard, SetClipboardText, CF_UNICODETEXT, CloseClipboard
import psutil

from win32con import SW_HIDE

import pickle

from os import getcwd
from os.path import expanduser

known_credentials = None
browser = None
pasted = False
credentials = [None, None]
suppress = True
button_answer = None


def make_window_centered(root):
    window_width = root.winfo_reqwidth()
    window_height = root.winfo_reqheight()
    position_right = int(root.winfo_screenwidth() / 2 - window_width / 2)
    position_down = int(root.winfo_screenheight() / 2 - window_height / 2)
    root.geometry("+{}+{}".format(position_right, position_down))
    root.lift()
    root.attributes("-topmost", True)
    return root


def get_button_answer(mode, root, textbox=None):
    global button_answer

    if mode == "textbox":
        button_answer = textbox.get(1.0, "end-1c")
    else:
        button_answer = mode
    root.destroy()
    return


def get_vk(key):
    return key.vk if hasattr(key, 'vk') else key.value.vk


def is_combination_pressed(combination):
    return all([get_vk(key) in pressed_vks for key in combination])


def on_press(key):
    global pressed_vks

    vk = get_vk(key)
    pressed_vks.add(vk)

    for combination in COMBINATIONS:
        if is_combination_pressed(combination):
            COMBINATIONS[combination]()


def on_release(key):
    global pressed_vks

    vk = get_vk(key)
    pressed_vks = pressed_vks - {vk}


def on_activate():
    print("ctrl+shift+p has been pressed")
    global pressed_vks
    global credentials
    global browser
    global suppress
    global button_answer
    global known_credentials

    pressed_vks = pressed_vks - {80, 162}

    if suppress:
        window_process_name = get_current_window_pname()
        title = window_process_name[:-4]
        result = retrieve_pwd(title)
        if not result:
            print("could not retrieve username and password")
            new_title = ""
            while not result:
                root = tk.Tk()
                textbox = tk.Text(root, height=1, width=20)
                tk_label = tk.Label(root, text=f'No results were found for "{title}"\nWhat did you mean to look for?')
                b1 = tk.Button(root, text="Ok", width=10, command=lambda m="textbox", r=root,
                               t=textbox: get_button_answer(m, r, t))

                tk_label.pack()
                textbox.pack()
                b1.pack()

                root = make_window_centered(root)
                root.mainloop()
                new_title = button_answer
                if not new_title or new_title == "":
                    print("Canceling Password Retrieve")
                    return True
                print(f"trying with {new_title}...")
                result = retrieve_pwd(new_title)
            button_answer = None
            root = tk.Tk()
            root.geometry("300x100")
            top = tk.Frame(root)
            bottom = tk.Frame(root)
            top.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            bottom.pack(side=tk.BOTTOM)
            w = tk.Message(top, text=f'Save "{new_title}" as "{title}" from now on?',
                           width=290)
            confirm_button = tk.Button(bottom, text="Yes", command=lambda m="confirm", r=root: get_button_answer(m, r),
                                       width=10)
            cancel_button = tk.Button(bottom, text="No", command=lambda m="cancel", r=root: get_button_answer(m, r),
                                      width=10)

            w.pack(expand=True)
            confirm_button.pack(side=tk.LEFT)
            cancel_button.pack(side=tk.RIGHT)

            root = make_window_centered(root)
            root.mainloop()

            if button_answer == "confirm":
                known_credentials[title] = new_title
                with open("known_credentials.pickle", "wb") as f:
                    pickle.dump(known_credentials, f)
            else:
                button_answer = None
                return True
        button_answer = None
        paste_credentials_routine(result)
    else:
        print("but did nothing")
    print("ctrl+p was successful, returning...")
    return True


def paste_credentials_routine(result):
    global suppress

    username, password = result
    print("credentials retrieved")
    credentials[0], credentials[1] = username, password
    OpenClipboard()
    EmptyClipboard()
    SetClipboardText(username, CF_UNICODETEXT)
    CloseClipboard()

    suppress = False

    root = tk.Tk()
    root.overrideredirect(True)
    tk_label = tk.Label(root, text="Ready", height=2, width=10)
    tk_label.pack()

    root = make_window_centered(root)
    root.after(2000, root.destroy)
    root.mainloop()


def paste_activate():
    print("ctrl+v has been pressed")
    global credentials
    global pasted
    global suppress
    global pressed_vks

    pressed_vks = pressed_vks - {80, 162}

    if not suppress:
        if not pasted:
            pasted = True
        else:
            OpenClipboard()
            EmptyClipboard()
            SetClipboardText(credentials[1], CF_UNICODETEXT)
            CloseClipboard()
            credentials[0], credentials[1] = None, None
            pasted = False
            suppress = True
    else:
        print("but did nothing")
    print("ctrl+v was successful, returning...")
    return True


def get_current_window_pname():
    hwnd = GetForegroundWindow()
    _, pid = GetWindowThreadProcessId(hwnd)
    return psutil.Process(pid).name()


def get_hwnds_for_pname(pname):
    def callback(hwnd, hwnds):
        if IsWindowVisible(hwnd) and IsWindowEnabled(hwnd):
            _, found_pid = GetWindowThreadProcessId(hwnd)
            if pname == psutil.Process(found_pid).name():
                hwnds.add(hwnd)
        return True
    hwnds = set()
    EnumWindows(callback, hwnds)
    return hwnds


def on_time_is_up():
    global browser
    
    print('5 minutes have passed closing browser...')
    browser.quit()
    browser = None
    return


def retrieve_pwd(title, username=None, email="YOURDEFAULTEMAIL"):  # if no username or email is found you might want
    global browser                                                 # to have a default email
    global button_answer

    if title in known_credentials:
        title = known_credentials[title]
    print("looking for ", title)
    if not browser:
        print("browser is None so it's being created")
        chrome_options = Options()
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        chrome_options.add_extension("extension_6_2212_2_0.crx")
        chrome_options.add_argument("user-data-dir=" + expanduser('~') +
                                    "\\AppData\\Local\\Google\\Chrome\\Dashlane Scrape User Folder\\")
        chrome_options.add_argument("--profile-directory=Default")

        s = Service(ChromeDriverManager().install())
        print("getting list of old hwnds")
        old_hwnds = get_hwnds_for_pname('chrome.exe')
        browser = webdriver.Chrome(service=s, options=chrome_options)
        print("browser created")
        
        timer = Timer(300, on_time_is_up)
        timer.start()
        print("5 minute timer started")
        
        hwnds = get_hwnds_for_pname('chrome.exe')
        hwnds_to_hide = list(hwnds - old_hwnds)
        print(f"hiding {len(hwnds_to_hide)} windows")
        for hwnd in hwnds_to_hide:
            ShowWindow(hwnd, SW_HIDE)

    unique_id = "fdjamakpfbbddfjaooikfcpapjohcfmg"  # this unique id is relative to dashlane extension
    main_page = "chrome-extension://" + unique_id + "/credentials"
    signup_page = "chrome-extension://" + unique_id + "/signup"

    browser.get(signup_page)
    print("going to login page and asking for authentication")
    print("waiting for collapse button as confirmation that login was successful")
    try:
        collapse_button = WebDriverWait(browser, 260).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'collapseButton')]")))
    except selenium.common.exceptions.TimeoutException:
        print("couldn't find collapse button, authentication got old?")
        browser.close()
        return False
    print("found collapse button, login is assumed to be successful, getting credentials")
    search_input = WebDriverWait(browser, 5).until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='search']")))
    if search_input.get_attribute("disabled"):
        collapse_button.click()
    error = True
    count = 0
    while error:
        error = False
        count += 1
        search_input.send_keys(title)
        try:
            results_panel = WebDriverWait(browser, 1).until(
                EC.presence_of_element_located((By.ID, "search-results")))
        except exceptions.TimeoutException:
            error = True
            search_input.clear()

        if count > 5:
            return False

    if username:
        credentials_box = results_panel.find_elements(By.XPATH, f".//*[text() = '{username}']")
    elif email:
        credentials_box = results_panel.find_elements(By.XPATH, f".//*[text() = '{email}']")
    else:
        credentials_box = results_panel.find_elements(By.XPATH, ".//a[contains(@href,'credentials')]")
    if len(credentials_box) == 0:
        credentials_box = results_panel.find_elements(By.XPATH, ".//a[contains(@href,'credentials')]")
        if len(credentials_box) == 0:
            print(f'No results were found for "{title}"')
            return False
    if len(credentials_box) != 1:
        root = tk.Tk()
        for credential in credentials_box:
            b = tk.Button(root, text=credential.text, command=lambda m=credential, r=root: get_button_answer(m, r))
            b.pack()
        root.overrideredirect(True)

        root = make_window_centered(root)
        root.mainloop()
        if button_answer:
            credentials_box = button_answer
            button_answer = None
        else:
            raise Exception("Error no answer was given to tkinter, this is not expected behaviour" +
                            "and should never happen")
    else:
        credentials_box = credentials_box[0]

    credentials_box.click()
    aside_panel = WebDriverWait(browser, 5).until(
        EC.presence_of_element_located((By.XPATH, ".//aside[contains(@class,'container')]")))
    login_container = aside_panel.find_element(
        By.XPATH, ".//div[contains(@class,'buttonsContainer') and .//input[@data-name='login']]")
    email_container = aside_panel.find_element(
        By.XPATH, ".//div[contains(@class,'buttonsContainer') and .//input[@data-name='email']]")
    password_container = aside_panel.find_element(
        By.XPATH, ".//div[contains(@class,'buttonsContainer') and .// input[@id = 'password']]")

    login_container_buttons = login_container.find_elements(By.XPATH, ".//button")
    if len(login_container_buttons) == 1:
        username = login_container.find_element(By.TAG_NAME, "input").get_attribute("value")
    else:
        username = email_container.find_element(By.TAG_NAME, "input").get_attribute("value")
    password = password_container.find_element(By.TAG_NAME, "input").get_attribute("value")

    action = ActionChains(browser)
    action.send_keys(Keys.ESCAPE).perform()
    search_input.clear()

    return username, password


if __name__ == '__main__':
    with open("known_credentials.pickle", "rb") as f:
        known_credentials = pickle.load(f)
    pressed_vks = set()
    COMBINATIONS = {
        frozenset([Key.ctrl_l, KeyCode(vk=80)]): on_activate,
        frozenset([Key.ctrl_l, KeyCode(vk=86)]): paste_activate
    }
    with Listener(
        on_press=on_press,
        on_release=on_release
    ) as listener:
        listener.join()
