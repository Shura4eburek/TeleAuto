from pywinauto.application import Application

class ServiceUI:
    def __init__(self, app: Application):
        self.main_window = app.window(title_re=".*Telemart.*")  # главное окно

        # Навигация по "Сервис"
        self.service_button = self._get_menu_item("Сервис")
        self.trade_in_button = self._get_menu_item("Trade-In")
        self.repair_button = self._get_menu_item("Ремонт")
        self.service_requests_button = self._get_menu_item("Серв. заявки")
        self.service_invoices_button = self._get_menu_item("Серв. накладные")
        self.service_moves_button = self._get_menu_item("Серв. перемещения")
        self.service_goods_button = self._get_menu_item("Серв. товары")
        self.service_centers_button = self._get_menu_item("Серв. центры")

    def _get_menu_item(self, title: str):
        # Сначала ищем все NavigationMenuItem
        menu_items = self.main_window.descendants(class_name="Telemart.Client.Common.Navigation.NavigationMenuItem")
        for item in menu_items:
            try:
                text_elem = item.child_window(title=title, control_type="Text")
                if text_elem.exists(timeout=0.5):
                    return item.wrapper_object()
            except Exception:
                continue
        raise RuntimeError(f"Меню с названием '{title}' не найдено")


    def click_service(self):
        self.service_button.click_input()

    def click_trade_in(self):
        self.trade_in_button.click_input()

    def click_repair(self):
        self.repair_button.click_input()

    def click_service_requests(self):
        self.service_requests_button.click_input()

    def click_service_invoices(self):
        self.service_invoices_button.click_input()

    def click_service_moves(self):
        self.service_moves_button.click_input()

    def click_service_goods(self):
        self.service_goods_button.click_input()

    def click_service_centers(self):
        self.service_centers_button.click_input()
