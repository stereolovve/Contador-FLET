import flet as ft
import sqlite3
from pynput import keyboard
import pandas as pd

class VehicleCounter(ft.Column):
    def __init__(self, db_path="app.db"):
        super().__init__()
        self.db_path = db_path
        self.init_db()
        self.counts, self.shortcuts = self.load_settings()
        self.labels = {}
        self.listener = None
        self.tabs = None
        self.new_vehicle_input = None
        self.new_shortcut_input = None
        self.setup_ui()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS categories
                        (vehicle TEXT PRIMARY KEY, shortcut TEXT, count INTEGER DEFAULT 0)''')
            conn.commit()

    def load_settings(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('SELECT vehicle, shortcut, count FROM categories')
            data = cur.fetchall()
        return {v: c for v, s, c in data}, {s: v for v, s, c in data}

    def setup_ui(self):
        self.tabs = ft.Tabs(
            tabs=[
                ft.Tab(text="Contador", content=ft.Column()),
                ft.Tab(text="Categorias", content=ft.Column([])),
            ]
        )
        self.controls.append(self.tabs)
        self.setup_counter_tab()
        self.setup_category_tab()

    def setup_counter_tab(self):
        tab = self.tabs.tabs[0].content
        for vehicle in self.counts:
            self.add_row(vehicle, tab)
        self.add_save_button(tab)

    def setup_category_tab(self):
        tab = self.tabs.tabs[1].content
        self.add_category_form(tab)
        self.load_categories(tab)

    def add_row(self, vehicle, tab): 
        label_vehicle = ft.Text(f"{vehicle}", width=100, size=16)
        label_count = ft.Text(f"{self.counts[vehicle]}", width=50, size=20)
        self.labels[vehicle] = label_count
        add_button = ft.IconButton(icon=ft.icons.ADD, icon_color="green", on_click=lambda e, v=vehicle: self.increment(v))
        remove_button = ft.IconButton(icon=ft.icons.REMOVE, icon_color="red", on_click=lambda e, v=vehicle: self.decrement(v))
        row = ft.Row([label_vehicle, label_count, add_button, remove_button])
        tab.controls.insert(-1, row)

    def add_save_button(self, tab):
        save_button = ft.IconButton(icon=ft.icons.SAVE, on_click=self.save_counts)
        tab.controls.append(ft.Container(content=save_button, alignment=ft.alignment.center))

    def add_category_form(self, tab):
        self.new_vehicle_input = ft.TextField(label="Categoria", width=150)
        self.new_shortcut_input = ft.TextField(label="Atalho", width=90)
        add_button = ft.IconButton(icon=ft.icons.ADD, icon_color="BLUE", on_click=self.add_category)
        form_row = ft.Row([self.new_vehicle_input, self.new_shortcut_input, add_button])
        tab.controls.insert(0, form_row)  # Adiciona o formulário na parte superior

    def load_categories(self, tab):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('SELECT vehicle, shortcut FROM categories')
            categories = cur.fetchall()
        for vehicle, shortcut in categories:
            self.add_category_row(vehicle, shortcut, tab)

    def add_category_row(self, vehicle, shortcut, tab):
        vehicle_input = ft.TextField(value=vehicle, width=150)
        shortcut_input = ft.TextField(value=shortcut, width=90)
        rename_button = ft.IconButton(icon=ft.icons.EDIT, icon_color="AMBER", on_click=lambda e, v=vehicle, vi=vehicle_input, si=shortcut_input: self.rename_category(v, vi.value, si.value))
        delete_button = ft.IconButton(icon=ft.icons.DELETE, icon_color="red", on_click=lambda e, v=vehicle: self.delete_category(v))
        row = ft.Row([vehicle_input, shortcut_input, rename_button, delete_button])
        tab.controls.append(row)  # Adiciona ao final, abaixo do formulário de adição

    def add_category(self, e):
        vehicle = self.new_vehicle_input.value
        shortcut = self.new_shortcut_input.value
        if vehicle and shortcut:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('INSERT INTO categories (vehicle, shortcut, count) VALUES (?, ?, 0)', (vehicle, shortcut))
                conn.commit()
            self.counts[vehicle] = 0
            self.shortcuts[shortcut] = vehicle
            self.add_category_row(vehicle, shortcut, self.tabs.tabs[1].content)
            self.new_vehicle_input.value = ""
            self.new_shortcut_input.value = ""
            self.update()

    def rename_category(self, old_vehicle, new_vehicle, new_shortcut):
        if new_vehicle and new_shortcut:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('UPDATE categories SET vehicle = ?, shortcut = ? WHERE vehicle = ?', (new_vehicle, new_shortcut, old_vehicle))
                conn.commit()

            # Atualize os dicionários e labels
            self.counts[new_vehicle] = self.counts.pop(old_vehicle)
            old_shortcut = None
            for key, value in self.shortcuts.items():
                if value == old_vehicle:
                    old_shortcut = key
                    break
            if old_shortcut:
                self.shortcuts.pop(old_shortcut)
            self.shortcuts[new_shortcut] = new_vehicle
            self.labels[new_vehicle] = self.labels.pop(old_vehicle)
            self.update_ui()

    def delete_category(self, vehicle):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM categories WHERE vehicle = ?', (vehicle,))
            conn.commit()

        # Remova das estruturas de dados
        if vehicle in self.counts:
            del self.counts[vehicle]
        if vehicle in self.labels:
            del self.labels[vehicle]
        old_shortcut = None
        for key, value in self.shortcuts.items():
            if value == vehicle:
                old_shortcut = key
                break
        if old_shortcut:
            del self.shortcuts[old_shortcut]
        self.update_ui()

    def update_ui(self):
        self.tabs.tabs[0].content.controls.clear()
        self.tabs.tabs[1].content.controls.clear()
        self.setup_counter_tab()
        self.setup_category_tab()
        self.update()

    def increment(self, vehicle):
        self.counts[vehicle] += 1
        self.update_labels(vehicle)
        self.save_to_db(vehicle)

    def decrement(self, vehicle):
        if self.counts[vehicle] > 0:
            self.counts[vehicle] -= 1
            self.update_labels(vehicle)
            self.save_to_db(vehicle)

    def update_labels(self, vehicle):
        self.labels[vehicle].value = str(self.counts[vehicle])
        self.update()

    def save_counts(self, e):
        df = pd.DataFrame([self.counts])
        try:
            existing_df = pd.read_excel('counts.xlsx')
            df = pd.concat([existing_df, df])
        except FileNotFoundError:
            pass
        df.to_excel('counts.xlsx', index=False)
        print("Counts saved to counts.xlsx")

    def save_to_db(self, vehicle):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE categories SET count = ? WHERE vehicle = ?', (self.counts[vehicle], vehicle))
            conn.commit()

    def on_key_press(self, key):
        char = getattr(key, 'char', '')
        vehicle = self.shortcuts.get(char)
        if vehicle:
            self.increment(vehicle)

    def start_listener(self):
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.start()

    def stop_listener(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

def main(page: ft.Page):
    counter = VehicleCounter()
    page.scroll = ft.ScrollMode.AUTO
    page.add(counter)
    
    counter.start_listener()
    page.on_close = lambda e: counter.stop_listener()

ft.app(target=main)
