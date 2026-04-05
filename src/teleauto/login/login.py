# src/teleauto/login/login.py
import subprocess
import logging
import time
from pywinauto import Desktop
from src.teleauto.localization import tr
from src.teleauto.gui.constants import (
    TELEMART_KILL_DELAY, TELEMART_WINDOW_TIMEOUT, TELEMART_MAX_CYCLES,
)

logger = logging.getLogger(__name__)

CREATE_NO_WINDOW = 0x08000000

def start_telemart(path):
    try:
        subprocess.run(['taskkill', '/f', '/im', 'Telemart.Client.exe'],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
        subprocess.run(['taskkill', '/f', '/im', 'Telemart.exe'],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
        time.sleep(TELEMART_KILL_DELAY)
    except Exception:
        pass

    try:
        logger.info(tr("log_tm_launching"))
        if path:
            subprocess.Popen([path], creationflags=CREATE_NO_WINDOW)
            logger.info(tr("log_tm_launched"))
        else:
             logger.error(tr("error_no_tm_path"))
    except Exception as e:
        logger.error(tr("log_tm_check_err", e=e))

def login_telemart(username: str, password: str, timeout: int = 20):
    def wait_for_login_box():
        logger.info(tr("log_tm_wait_login"))
        for attempt in range(TELEMART_WINDOW_TIMEOUT):
            try:
                spec = Desktop(backend="uia").window(title_re=r"^Telemart\.Client")
                if spec.exists():
                    wrapper = spec.wrapper_object()
                    login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                      if ctrl.element_info.automation_id == "LoginTextBox"), None)

                    if login_box:
                        logger.info(tr("log_tm_login_found"))
                        return wrapper
                    else:
                        logger.info(tr("log_tm_login_not_found", attempt=attempt + 1))
                        time.sleep(1)
                else:
                    logger.info(tr("log_tm_window_not_found", attempt=attempt + 1))
                    time.sleep(1)
            except Exception:
                logger.error(tr("log_tm_login_err", e="[REDACTED]"))

        logger.warning(tr("log_tm_timeout"))
        return None

    def perform_login(wrapper):
        logger.info(tr("log_tm_performing_login"))
        try:
            login_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                              if ctrl.element_info.automation_id == "LoginTextBox"), None)
            if not login_box:
                raise RuntimeError(tr("log_tm_err_login_field"))
            login_box.set_text(username)
            logger.info(tr("log_tm_login_entered"))

            password_box = next((ctrl for ctrl in wrapper.descendants(control_type="Edit")
                                 if ctrl.element_info.automation_id == "PasswordBoxEdit"), None)
            if not password_box:
                raise RuntimeError(tr("log_tm_err_pass_field"))
            password_box.set_text(password)
            logger.info(tr("log_tm_pass_entered"))

            login_button = next((ctrl for ctrl in wrapper.descendants(control_type="Button")
                                 if ctrl.element_info.name == "Вход"), None)
            if not login_button:
                raise RuntimeError(tr("log_tm_err_btn"))
            login_button.click_input()
            logger.info(tr("log_tm_btn_clicked"))
            return True

        except Exception as e:
            logger.error(tr("log_tm_login_err", e=e))
            return False

    for cycle in range(TELEMART_MAX_CYCLES):
        logger.info(tr("log_tm_update_cycle", current=cycle + 1, max=TELEMART_MAX_CYCLES))
        wrapper = wait_for_login_box()
        if wrapper is None:
            continue
        if perform_login(wrapper):
            logger.info(tr("log_tm_login_ok"))
            return True
        else:
            continue

    raise RuntimeError(tr("log_tm_update_fail", max=TELEMART_MAX_CYCLES))
