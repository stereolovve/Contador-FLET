import flet as ft
import sqlite3
from pynput import keyboard
import pandas as pd
from datetime import datetime
import json
import os


class ContadorPerplan(ft.Column):
    def __init__(self, page, caminho_db="dados.db"):
        super().__init__()
        self.page = page
        self.caminho_db = caminho_db
        self.sessao = None
        self.detalhes = {}
        self.init_db()
        self.carregar_categorias_padrao('categorias_padrao.json')
        self.carregar_sessao_ativa()
        self.contagens, self.binds, self.categorias = self.carregar_config()
        self.labels = {}
        self.listener = None
        self.contagem_ativa = False
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
            conn.execute('''CREATE TABLE IF NOT EXISTS sessoes
                            (sessao TEXT PRIMARY KEY, detalhes TEXT, criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ativa INTEGER)''')
            conn.commit()

    def carregar_categorias_padrao(self, caminho_json):
        with sqlite3.connect(self.caminho_db) as conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM categorias')
            count = cur.fetchone()[0]
            if count == 0:
                try:
                    with open(caminho_json, 'r') as f:
                        categorias_padrao = json.load(f)
                        for categoria in categorias_padrao:
                            veiculo = categoria.get('veiculo')
                            bind = categoria.get('bind')
                            if veiculo and bind:
                                cur.execute('INSERT INTO categorias (veiculo, bind, count, criado_em) VALUES (?, ?, 0, ?)', 
                                            (veiculo, bind, datetime.now().isoformat()))
                    conn.commit()
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Erro ao carregar categorias padrão: {e}")

    def carregar_config(self):
        with sqlite3.connect(self.caminho_db) as conn:
            cur = conn.cursor()
            cur.execute('SELECT veiculo, bind, count, criado_em FROM categorias ORDER BY criado_em')
            data = cur.fetchall()
        return {v: c for v, b, c, t in data}, {b: v for v, b, c, t in data}, data

    def carregar_sessao_ativa(self):
        with sqlite3.connect(self.caminho_db) as conn:
            cur = conn.cursor()
            cur.execute('SELECT sessao, detalhes FROM sessoes WHERE ativa = 1')
            sessao_ativa = cur.fetchone()
            if sessao_ativa:
                self.sessao, detalhes_json = sessao_ativa
                self.detalhes = json.loads(detalhes_json)
                self.page.overlay.append(ft.SnackBar(ft.Text("Sessão ativa recuperada.")))
                self.page.update()

    def salvar_sessao(self):
        with sqlite3.connect(self.caminho_db) as conn:
            detalhes_json = json.dumps(self.detalhes)
            conn.execute('INSERT OR REPLACE INTO sessoes (sessao, detalhes, ativa) VALUES (?, ?, 1)', 
                         (self.sessao, detalhes_json))
            conn.commit()

    def finalizar_sessao(self):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('UPDATE sessoes SET ativa = 0 WHERE sessao = ?', (self.sessao,))
            conn.commit()

    def setup_ui(self):
        self.tabs = ft.Tabs(
            animation_duration=150,
            tabs=[
                ft.Tab(text="Inicio", content=ft.Column()),
                ft.Tab(text="Contador", content=ft.Column()),  # Desabilitado até criar uma sessão
                ft.Tab(text="Categorias", content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.SETTINGS, content=ft.Column()),
                ft.Tab(text="", icon=ft.icons.BAR_CHART, content=ft.Column()),
            ]
        )
        self.controls.append(self.tabs)
        self.setup_aba_inicio()
        self.setup_aba_contagem()
        self.setup_aba_categorias()
        self.setup_aba_perfil()
        self.setup_aba_relatorio()

    def setup_aba_inicio(self):
        tab = self.tabs.tabs[0].content
        self.pesquisador_input = ft.TextField(label="Pesquisador")
        self.codigo_ponto_input = ft.TextField(label="Código")
        self.nome_ponto_input = ft.TextField(label="Ponto (ex: P10N)")
        self.horas_contagem_input = ft.TextField(label="Periodo (ex: 6h-18h)")
        self.movimentos_input = ft.TextField(label="Movimentos (ex: A-B)")
        self.data_ponto_input = ft.TextField(label="Data do Ponto (dd-mm-aaaa)")
        criar_sessao_button = ft.ElevatedButton(text="Criar Sessão", on_click=self.criar_sessao)

        tab.controls.extend([
            self.pesquisador_input,
            self.codigo_ponto_input,
            self.nome_ponto_input,
            self.horas_contagem_input,
            self.movimentos_input,
            self.data_ponto_input,
            criar_sessao_button
        ])

        self.sessao_status = ft.Text("", weight=ft.FontWeight.BOLD)
        tab.controls.append(self.sessao_status)
        self.update_sessao_status()

    def criar_sessao(self, e):
        self.detalhes = {
            "Pesquisador": self.pesquisador_input.value,
            "Código": self.codigo_ponto_input.value,
            "Ponto": self.nome_ponto_input.value,
            "Periodo": self.horas_contagem_input.value,
            "Movimentos": self.movimentos_input.value,
            "Data do Ponto": self.data_ponto_input.value
        }
        self.sessao = f"Sessao_{self.detalhes['Código']}_{self.detalhes['Ponto']}_{self.detalhes['Movimentos']}_{self.detalhes['Data do Ponto']}"
        print("Detalhes da sessão:", self.detalhes)
        self.salvar_sessao()
        self.page.overlay.append(ft.SnackBar(ft.Text("Sessão criada com sucesso!")))
        self.page.update()
        self.tabs.selected_index = 1
        self.tabs.tabs[1].content.enabled = True
        self.update_sessao_status()
        self.page.update()

    def update_sessao_status(self):
        if self.sessao:
            self.sessao_status.value = f"Sessão ativa: {self.sessao}"
        else:
            self.sessao_status.value = "Nenhuma sessão ativa"
        self.page.update()

    def setup_aba_contagem(self):
        tab = self.tabs.tabs[1].content
        self.contagem_ativa = False  # Inicia com a contagem desativada
        
        self.toggle_button = ft.Switch(
            label="",
            label_position="left",
            value=False,
            on_change=self.toggle_contagem
        )
        
        save_button = ft.IconButton(
            icon=ft.icons.SAVE,
            tooltip="Salvar contagem",
            on_click=self.save_contagens
        )
        
        end_session_button = ft.IconButton(
            icon=ft.icons.STOP,
            tooltip="Finalizar sessão",
            icon_size=30,
            on_click=self.confirmar_finalizar_sessao
        )
        
        container_switch = ft.Container(
            content=self.toggle_button,
            tooltip="Contagem Ativada/Desativada",
        )
        
        container_save = ft.Container(
            content=save_button,
        )
        
        container_stop = ft.Container(
            content=end_session_button,
        )
        
        row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            controls=[
                container_switch,
                container_save,
                container_stop
            ],
        )
        
        tab.controls.append(row)
        
        for veiculo, bind, count, criado_em in self.categorias:
            self.add_row(veiculo, bind, tab)
        
    def toggle_contagem(self, e):
        self.contagem_ativa = e.control.value
        estado = "ativada" if self.contagem_ativa else "desativada"
        print(f"{estado}")
        self.page.update()

    def add_row(self, veiculo, bind, tab): 
        label_bind = ft.Text(f"({bind})", width=30, size=16, color="AMBER")
        label_veiculo = ft.Text(f"{veiculo}", width=80, size=18)
        label_count = ft.Text(f"{self.contagens[veiculo]}", width=50, size=20)
        self.labels[veiculo] = label_count
        
        add_button = ft.IconButton(
            ft.icons.ADD,
            style=ft.ButtonStyle(color=ft.colors.GREEN),
            on_click=lambda e, v=veiculo: self.increment(v)
        )
        
        remove_button = ft.IconButton(
            ft.icons.REMOVE,
            style=ft.ButtonStyle(color=ft.colors.RED),
            on_click=lambda e, v=veiculo: self.decrement(v)
        )
        
        reset_button = ft.IconButton(
            ft.icons.RESTART_ALT_ROUNDED,
            style=ft.ButtonStyle(color=ft.colors.BLUE),
            on_click=lambda e, v=veiculo: self.reset(v)
        )
        
        row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                label_bind,
                label_veiculo,
                label_count,
                add_button,
                remove_button,
                reset_button
            ]
        )
        tab.controls.append(row)

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
        self.contagens[veiculo] = 0
        self.update_labels(veiculo)
        self.save_to_db(veiculo)

    def update_labels(self, veiculo):
        self.labels[veiculo].value = str(self.contagens[veiculo])
        self.page.update()

    def save_contagens(self, e):
        # Cria um DataFrame com as contagens
        contagens_df = pd.DataFrame([self.contagens])
        # Cria um DataFrame com os detalhes da sessão
        detalhes_df = pd.DataFrame([self.detalhes])
        
        contagens_df.fillna(0, inplace=True)
        
        # Define o caminho do arquivo da sessão
        if not os.path.exists('contagens'):
            os.makedirs('contagens')
        arquivo_sessao = f'{self.sessao}.xlsx'

        # Tenta ler o arquivo existente, se existir
        try:
            existing_df = pd.read_excel(arquivo_sessao, sheet_name=None)
            if 'Detalhes' in existing_df and 'Contagens' in existing_df:
                contagens_df = pd.concat([existing_df['Contagens'], contagens_df])
                detalhes_df = pd.concat([existing_df['Detalhes'], detalhes_df])

        except FileNotFoundError:
            pass

        # Salva os DataFrames em diferentes planilhas no arquivo Excel
        with pd.ExcelWriter(arquivo_sessao, engine='xlsxwriter') as writer:
            contagens_df.to_excel(writer, sheet_name='Contagens', index=False)
            detalhes_df.to_excel(writer, sheet_name='Detalhes', index=False)

        print(f"Contagem salva em {arquivo_sessao}")
        self.load_data_table()

    def confirmar_finalizar_sessao(self, e):
        def close_dialog(e):
            dialog.open = False
            self.page.update()

        def end_and_close(e):
            self.end_session()
            dialog.open = False
            self.page.update()
            
        dialog = ft.AlertDialog(
            title=ft.Text("Finalizar Sessão"),
            content=ft.Text("Você tem certeza que deseja finalizar a sessão?"),
            actions=[
                ft.TextButton("Sim", on_click=end_and_close),
                ft.TextButton("Cancelar", on_click=close_dialog),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def end_session(self):
        self.finalizar_sessao()
        for veiculo in self.contagens:
            self.contagens[veiculo] = 0
            self.update_labels(veiculo)
            self.save_to_db(veiculo)
        self.sessao = None
        self.page.overlay.append(ft.SnackBar(ft.Text("Sessão finalizada!")))
        self.tabs.selected_index = 0
        self.tabs.tabs[1].content.enabled = False
        self.update_sessao_status()
        self.page.update()
        self.stop_listener()

    def save_to_db(self, veiculo):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('UPDATE categorias SET count = ? WHERE veiculo = ?', (self.contagens[veiculo], veiculo))
            conn.commit()

    def setup_aba_categorias(self):
        tab = self.tabs.tabs[2].content
        self.add_category_form(tab)
        self.load_categorias(tab)

    def add_category_form(self, tab):
        self.novo_veiculo_input = ft.TextField(label="Categoria", width=150)
        self.nova_bind_input = ft.TextField(label="Atalho", width=90)
        add_button = ft.IconButton(icon=ft.icons.ADD, icon_color="BLUE", on_click=self.add_category)
        form_row = ft.Row([self.novo_veiculo_input, self.nova_bind_input, add_button])
        tab.controls.insert(0, form_row)

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
        tab.controls.append(row)

    def add_category(self, e):
        veiculo = self.novo_veiculo_input.value
        bind = self.nova_bind_input.value
        if veiculo and bind:
            criado_em = datetime.now().isoformat()
            with sqlite3.connect(self.caminho_db) as conn:
                conn.execute('INSERT INTO categorias (veiculo, bind, count, criado_em) VALUES (?, ?, 0, ?)', (veiculo, bind, criado_em))
                conn.commit()
            self.contagens[veiculo] = 0
            self.binds[bind] = veiculo
            self.update_categorias()

    def rename_category(self, old_veiculo, new_veiculo, new_bind):
        if new_veiculo and new_bind:
            with sqlite3.connect(self.caminho_db) as conn:
                conn.execute('UPDATE categorias SET veiculo = ?, bind = ? WHERE veiculo = ?', (new_veiculo, new_bind, old_veiculo))
                conn.commit()
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
            self.update_categorias()

    def delete_category(self, veiculo):
        with sqlite3.connect(self.caminho_db) as conn:
            conn.execute('DELETE FROM categorias WHERE veiculo = ?', (veiculo,))
            conn.commit()
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
        self.update_categorias()

    def update_categorias(self):
        self.categorias = self.carregar_config()[2]
        self.update_ui()

    def update_ui(self):
        # Atualiza a aba de categorias
        tab_categorias = self.tabs.tabs[2].content
        tab_categorias.controls.clear()
        self.add_category_form(tab_categorias)
        self.load_categorias(tab_categorias)

        # Atualiza a aba de contagem
        tab_contagem = self.tabs.tabs[1].content
        tab_contagem.controls.clear()
        self.setup_aba_contagem()
        
        self.page.update()

    def setup_aba_perfil(self):
        tab = self.tabs.tabs[3].content
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

    def setup_aba_relatorio(self):
        tab = self.tabs.tabs[4].content
        self.page.scroll = ft.ScrollMode.AUTO
        self.view_relatorio(tab)

    def view_relatorio(self, tab):
        try:
            arquivo_sessao = f'{self.sessao}.xlsx'  # Usa a sessão atual para o arquivo
            df_contagens = pd.read_excel(arquivo_sessao, sheet_name='Contagens')
            if df_contagens.empty:
                tab.controls.append(ft.Text("Não há dados salvos."))
            else:
                detalhes_texto = "\n".join([f"{key}: {value}" for key, value in self.detalhes.items()])
                tab.controls.append(ft.Text(detalhes_texto, weight=ft.FontWeight.BOLD))
                columns = [
                    ft.DataColumn(ft.Text(col, weight=ft.FontWeight.BOLD))
                    for col in df_contagens.columns
                ]
                rows = [
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(int(row[col])) if pd.api.types.is_numeric_dtype(row[col]) else str(row[col]))) for col in df_contagens.columns if pd.notna(row[col])
                        ]
                    )
                    for _, row in df_contagens.iterrows()
                ]
                data_table = ft.DataTable(
                    columns=columns,
                    rows=rows,
                    border=ft.border.all(2, "red"),
                    divider_thickness=0,
                    border_radius=5,
                    show_checkbox_column=False,
                )
                tab.controls.append(data_table)
        except FileNotFoundError:
            tab.controls.append(ft.Text("Não há dados salvos."))
        except ValueError as e:
            tab.controls.append(ft.Text(str(e)))
        self.page.update()

    def load_data_table(self):
        tab = self.tabs.tabs[4].content
        tab.controls.clear()
        self.view_relatorio(tab)

    def on_key_press(self, key):
        if not self.contagem_ativa:
            return
        try:
            char = None
            if hasattr(key, 'vk') and key.vk in self.numpad_mappings:
                char = self.numpad_mappings[key.vk]
            elif hasattr(key, 'char'):
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
        "Jetbrains": "assets/fonts/JetbrainsMono.ttf",
        "RobotoMono": "assets/fonts/RobotoMono.ttf",
    }

    page.theme = ft.Theme(font_family="Jetbrains")
    page.scroll = ft.ScrollMode.AUTO
    
    page.window.width = 450
    page.window.height = 700
    page.window.always_on_top = True
    page.add(contador)
    
    contador.start_listener()
    page.on_close = lambda e: contador.stop_listener()

ft.app(target=main)