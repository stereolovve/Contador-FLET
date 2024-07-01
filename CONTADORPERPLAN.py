import flet as ft
import sqlite3
from pynput import keyboard
import pandas as pd
from datetime import datetime

class ContadorPerplan(ft.Column):
    def __init__(self, page, caminho_db="dados.db"):
        super().__init__()
        self.page = page  # Armazena a referência da página
        self.caminho_db = caminho_db
        self.init_db()
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.labels = {}
        self.listener = None
        self.tabs = None
        self.novo_veiculo_input = None
        self.nova_bind_input = None
        self.numpad_mappings = {
            96: "np0",
            97: "np1",
            98: "np2",
            99: "np3",
            100: "np4",
            101: "np5",
            102: "np6",
            103: "np7",
            104: "np8",
            105: "np9",
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
        return {v: c for v, b, c, t in data}, {b: v for v, b, c, t in data}, data

    def setup_ui(self):
        self.tabs = ft.Tabs(
            tabs=[
                ft.Tab(text="Contador", content=ft.Column()),
                ft.Tab(text="Categorias", content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.BAR_CHART, content=ft.Column()),
            ]
        )
        self.controls.append(self.tabs)
        self.setup_aba_contagem()
        self.setup_aba_categorias()
        self.setup_aba_perfil()
        self.setup_aba_relatorio()

    def setup_aba_contagem(self):
        tab = self.tabs.tabs[0].content
        for veiculo, bind, count, criado_em in self.categorias:
            self.add_row(veiculo, tab)
        self.add_save_button(tab)

    def setup_aba_categorias(self):
        tab = self.tabs.tabs[1].content
        self.add_category_form(tab)
        self.load_categorias(tab)
        
    def setup_aba_perfil(self):
        tab = self.tabs.tabs[2].content
        self.theme_mode(tab)
        
    def setup_aba_relatorio(self):
        tab = self.tabs.tabs[3].content
        self.page.scroll = ft.ScrollMode.AUTO

        self.view_relatorio(tab)

    # Config. da aba_contagem
    def add_row(self, veiculo, tab): 
        label_veiculo = ft.Text(f"{veiculo}", width=110, size=18)
        label_count = ft.Text(f"{self.contagens[veiculo]}", width=50, size=20)
        self.labels[veiculo] = label_count
        add_button = ft.IconButton(ft.icons.ADD, style=ft.ButtonStyle(color=ft.colors.GREEN), on_click=lambda e, v=veiculo: self.increment(v))
        remove_button = ft.IconButton(ft.icons.REMOVE, style=ft.ButtonStyle(color=ft.colors.RED), on_click=lambda e, v=veiculo: self.decrement(v))
        reset_button = ft.IconButton(ft.icons.RESTART_ALT_ROUNDED, style=ft.ButtonStyle(color=ft.colors.BLUE), on_click=lambda e, v=veiculo: self.reset(v))
        row = ft.Row([label_veiculo, label_count, add_button, remove_button, reset_button])
        tab.controls.append(row)

    def add_save_button(self, tab):
        save_button = ft.IconButton(icon=ft.icons.SAVE, on_click=self.save_contagens)
        tab.controls.append(ft.Container(content=save_button, alignment=ft.alignment.center))
        
    def increment(self, veiculo):
        self.contagens[veiculo] += 1
        self.update_labels(veiculo)
        self.save_to_db(veiculo)

    def decrement(self, veiculo):
        if self.contagens[veiculo] > 0:
            self.contagens[veiculo] -= 1
            self.update_labels(veiculo)
            self.save_to_db(veiculo)
            
    def reset(self, veiculo):
        if self.contagens[veiculo] > 0:
            self.contagens[veiculo] = 0
            self.update_labels(veiculo)
            self.save_to_db(veiculo)
    
    def update_labels(self, veiculo):
        self.labels[veiculo].value = str(self.contagens[veiculo])
        self.update()
    
    def save_contagens(self, e):
        df = pd.DataFrame([self.contagens])
        df.fillna(0, inplace=True)
        try:
            existing_df = pd.read_excel('contagens.xlsx')
            existing_df.fillna(0, inplace=True)
            df = pd.concat([existing_df, df])
        except FileNotFoundError:
            pass
        df.to_excel('contagens.xlsx', index=False)
        print("Contagem salva em contagens.xlsx")
        self.load_data_table() 
        
    def save_to_db(self, veiculo):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('UPDATE categorias SET count = ? WHERE veiculo = ?', (self.contagens[veiculo], veiculo))
            conn.commit()

    # Config. aba_categoria
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
     
    # Config. aba_configurações   
    def theme_mode(self, tab):
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.c = ft.Switch(label="Modo claro", on_change=self.theme_changed)
        opacity = ft.Slider(value=100, min=20, max=100, divisions=80, label="Opacidade", on_change=self.ajustar_opacidade)
        tab.controls.append(self.c)
        tab.controls.append(opacity)
        
    def theme_changed(self, e):
        self.page.theme_mode = (
            ft.ThemeMode.DARK
            if self.page.theme_mode == ft.ThemeMode.LIGHT
            else ft.ThemeMode.LIGHT
        )
        self.c.label = (
            "Modo claro" if self.page.theme_mode == ft.ThemeMode.LIGHT else "Modo escuro"
        )
        self.page.update()
        
    def ajustar_opacidade(self, e):
        nova_opacidade = e.control.value / 100
        self.page.window.opacity = nova_opacidade
        self.page.update()

    def update_ui(self):
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.tabs.tabs[0].content.controls.clear()
        self.tabs.tabs[1].content.controls.clear()
        self.tabs.tabs[2].content.controls.clear()
        self.tabs.tabs[3].content.controls.clear()
        self.setup_aba_contagem()
        self.setup_aba_categorias()
        self.setup_aba_perfil()
        self.setup_aba_relatorio()
        self.update()

    # Config. Relatório
    def view_relatorio(self, tab):

        try:
            df = pd.read_excel("contagens.xlsx")
            if df.empty:
                tab.controls.append(ft.Text("Não há dados salvos."))
            else:
                columns = [
                    ft.DataColumn(ft.Text(col, weight=ft.FontWeight.BOLD))
                    for col in df.columns
                ]
                rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(int(row[col]) if pd.notna(row[col]) and isinstance(row[col], float) else str(row[col])))
                            for col in df.columns
                            
                        ]
                    )
                    for _, row in df.iterrows() # _ é usado para ignorar o índice retornado, enquanto row é a linha atual do DataFrame sendo iterada.
                ]
                data_table = ft.DataTable(
                    columns=columns,
                    rows=rows,
                    border=ft.border.all(2, "red"),
                    divider_thickness=0,
                    

                    border_radius=ft.border_radius.all(5),
                    show_checkbox_column=False,
                )
                tab.controls.append(data_table)
                    
        except FileNotFoundError:
            tab.controls.append(ft.Text("No data available"))
        self.page.update()

    def load_data_table(self):
        tab = self.tabs.tabs[3].content
        tab.controls.clear()  # Limpa os controles existentes antes de adicionar novos
        self.view_relatorio(tab)

    # Código main
    def on_key_press(self, key):
        try:
            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:  # Se a tecla for do numpad
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):  # Se for uma tecla normal
                char = key.char
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
    contador = ContadorPerplan(page)
    page.fonts = {
        "Jetbrains": "fonts/JetbrainsMono.ttf",
        "RobotoMono": "fonts/RobotoMono.ttf",
    }

    page.theme = ft.Theme(font_family="Jetbrains")
    page.scroll = ft.ScrollMode.AUTO
    
    page.window.width = 450  # Define a largura da janela
    page.window.height = 600  # Define a altura da janela
    page.window.always_on_top = True
    page.add(contador)
    
    contador.start_listener()
    page.on_close = lambda e: contador.stop_listener()

ft.app(target=main)
