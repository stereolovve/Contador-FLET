import flet as ft
import sqlite3
from pynput import keyboard
import pandas as pd
from datetime import datetime

class ContadorPerplan(ft.Column):
    def __init__(self, caminho_db="dados.db"):
        super().__init__()
        self.caminho_db = caminho_db
        self.init_db()
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.labels = {}
        self.listener = None
        self.tabs = None
        self.novo_veiculo_input = None
        self.nova_bind_input = None
        self.key_mappings = {
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7",
            "8": "8",
            "9": "9",
            "0": "0",
            keyboard.KeyCode.from_vk(96): "np0",
            keyboard.KeyCode.from_vk(97): "np1",
            keyboard.KeyCode.from_vk(98): "np2",
            keyboard.KeyCode.from_vk(99): "np3",
            keyboard.KeyCode.from_vk(100): "np4",
            keyboard.KeyCode.from_vk(101): "np5",
            keyboard.KeyCode.from_vk(102): "np6",
            keyboard.KeyCode.from_vk(103): "np7",
            keyboard.KeyCode.from_vk(104): "np8",
            keyboard.KeyCode.from_vk(105): "np9",
        }
        self.setup_ui()

    def init_db(self):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS categorias
                        (veiculo TEXT PRIMARY KEY, bind TEXT, count INTEGER DEFAULT 0, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            conn.commit()

    def carregar_config(self):
        with sqlite3.connect(self.caminho_db) as conn:
            cur = conn.cursor()
            cur.execute('SELECT veiculo, bind, count, criado_em FROM categorias ORDER BY criado_em')
            data = cur.fetchall()
        return {v: c for v, s, c, t in data}, {s: v for v, s, c, t in data}, data

    def setup_ui(self):
        self.tabs = ft.Tabs(
            tabs=[
                ft.Tab(text="Contador", content=ft.Column()),
                ft.Tab(text="Categorias", content=ft.Column()),
            ]
        )
        self.controls.append(self.tabs)
        self.setup_aba_contagem()
        self.setup_aba_categorias()

    def setup_aba_contagem(self):
        tab = self.tabs.tabs[0].content
        for veiculo, bind, count, criado_em in self.categorias:
            self.add_row(veiculo, tab)
        self.add_save_button(tab)

    def setup_aba_categorias(self):
        tab = self.tabs.tabs[1].content
        self.add_category_form(tab)
        self.load_categorias(tab)

    def add_row(self, veiculo, tab): 
        label_veiculo = ft.Text(f"{veiculo}", width=110, size=18)
        label_count = ft.Text(f"{self.contagens[veiculo]}", width=50, size=20)
        self.labels[veiculo] = label_count
        add_button = ft.IconButton(ft.icons.ADD, style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.GREEN), on_click=lambda e, v=veiculo: self.increment(v))
        remove_button = ft.IconButton(ft.icons.REMOVE, style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.RED), on_click=lambda e, v=veiculo: self.decrement(v))
        row = ft.Row([label_veiculo, label_count, add_button, remove_button])
        tab.controls.append(row)

    def add_save_button(self, tab):
        save_button = ft.IconButton(icon=ft.icons.SAVE, on_click=self.save_contagens)
        tab.controls.append(ft.Container(content=save_button, alignment=ft.alignment.center))

    def add_category_form(self, tab):
        self.novo_veiculo_input = ft.TextField(label="Categoria", width=150)
        self.nova_bind_input = ft.TextField(label="Atalho", width=90)
        add_button = ft.IconButton(icon=ft.icons.ADD, icon_color="BLUE", on_click=self.add_category)
        form_row = ft.Row([self.novo_veiculo_input, self.nova_bind_input, add_button])
        tab.controls.insert(0, form_row)  # Adiciona o formulário na parte superior

    def load_categorias(self, tab):
        with sqlite3.connect(self.caminho_db) as conn:
            cur = conn.cursor()
            cur.execute('SELECT veiculo, bind FROM categorias ORDER BY criado_em')
            categorias = cur.fetchall()
        for veiculo, bind in categorias:
            self.add_category_row(veiculo, bind, tab)

    def add_category_row(self, veiculo, bind, tab):
        veiculo_input = ft.TextField(value=veiculo, width=150)
        bind_input = ft.TextField(value=bind, width=90)
        rename_button = ft.IconButton(icon=ft.icons.EDIT, icon_color="AMBER", on_click=lambda e, v=veiculo, vi=veiculo_input, si=bind_input: self.rename_category(v, vi.value, si.value))
        delete_button = ft.IconButton(icon=ft.icons.DELETE, icon_color="red", on_click=lambda e, v=veiculo: self.delete_category(v))
        row = ft.Row([veiculo_input, bind_input, rename_button, delete_button])
        tab.controls.append(row)  # Adiciona ao final, abaixo do formulário de adição

    def add_category(self, e):
        veiculo = self.novo_veiculo_input.value
        bind = self.nova_bind_input.value
        if veiculo and bind:
            criado_em = datetime.now().isoformat()  # Formato ISO para compatibilidade com SQLite
            with sqlite3.connect(self.caminho_db) as conn:
                conn.execute('INSERT INTO categorias (veiculo, bind, count, criado_em) VALUES (?, ?, 0, ?)', (veiculo, bind, criado_em))
                conn.commit()
            self.contagens[veiculo] = 0
            self.binds[bind] = veiculo
            self.update_ui()

    def rename_category(self, old_veiculo, new_veiculo, new_bind):
        if new_veiculo and new_bind:
            with sqlite3.connect(self.caminho_db) as conn:
                conn.execute('UPDATE categorias SET veiculo = ?, bind = ? WHERE veiculo = ?', (new_veiculo, new_bind, old_veiculo))
                conn.commit()

            # Atualize os dicionários e labels
            self.contagens[new_veiculo] = self.contagens.pop(old_veiculo)
            old_bind = None
            for key, value in self.binds.items():
                if value == old_veiculo:
                    old_bind = key
                    break
            if old_bind:
                self.binds.pop(old_bind)
            self.binds[new_bind] = new_veiculo
            self.labels[new_veiculo] = self.labels.pop(old_veiculo)
            self.update_ui()

    def delete_category(self, veiculo):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('DELETE FROM categorias WHERE veiculo = ?', (veiculo,))
            conn.commit()

        # Remova das estruturas de dados
        if veiculo in self.contagens:
            del self.contagens[veiculo]
        if veiculo in self.labels:
            del self.labels[veiculo]
        old_bind = None
        for key, value in self.binds.items():
            if value == veiculo:
                old_bind = key
                break
        if old_bind:
            del self.binds[old_bind]
        self.update_ui()

    def update_ui(self):
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.tabs.tabs[0].content.controls.clear()
        self.tabs.tabs[1].content.controls.clear()
        self.setup_aba_contagem()
        self.setup_aba_categorias()
        self.update()

    def increment(self, veiculo):
        self.contagens[veiculo] += 1
        self.update_labels(veiculo)
        self.save_to_db(veiculo)

    def decrement(self, veiculo):
        if self.contagens[veiculo] > 0:
            self.contagens[veiculo] -= 1
            self.update_labels(veiculo)
            self.save_to_db(veiculo)

    def update_labels(self, veiculo):
        self.labels[veiculo].value = str(self.contagens[veiculo])
        self.update()

    def save_contagens(self, e):
        df = pd.DataFrame([self.contagens])
        try:
            existing_df = pd.read_excel('contagens.xlsx')
            df = pd.concat([existing_df, df])
        except FileNotFoundError:
            pass
        df.to_excel('contagens.xlsx', index=False)
        print("contagens saved to contagens.xlsx")

    def save_to_db(self, veiculo):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('UPDATE categorias SET count = ? WHERE veiculo = ?', (self.contagens[veiculo], veiculo))
            conn.commit()

    def on_key_press(self, key):
        try:
            char = None
            if hasattr(key, 'vk'):  # Se a tecla tiver um código virtual
                char = self.key_mappings.get(keyboard.KeyCode.from_vk(key.vk))
            if char is None and hasattr(key, 'char'):  # Se a tecla não tiver código virtual ou não estiver mapeada, use o caractere
                char = self.key_mappings.get(key.char)
            if char:
                veiculo = self.binds.get(char)
                if veiculo:
                    self.increment(veiculo)
        except Exception as e:
            print(f"Error: {e}")

    def start_listener(self):
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.start()

    def stop_listener(self):
        if self.listener is not None:
            self.listener.stop()
            self.listener = None

def main(page: ft.Page):
    counter = ContadorPerplan()
    page.scroll = ft.ScrollMode.AUTO
    page.window.width = 400  # Define a largura da janela
    page.window.height = 600  # Define a altura da janela
    page.add(counter)
    
    counter.start_listener()
    page.on_close = lambda e: counter.stop_listener()

ft.app(target=main)
