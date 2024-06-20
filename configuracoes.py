# configuracoes.py
import flet as ft

class TemaConfig(ft.Column):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.build()

    def build(self):
        self.controls = [
            ft.Text("Configurações de Tema", size=20),
            ft.Switch(label="Modo Claro", on_change=self.trocar_tema),
        ]

    def trocar_tema(self, e):
        self.page.theme_mode = ft.ThemeMode.LIGHT if e.control.value else ft.ThemeMode.DARK
        self.page.update()

class AtalhosConfig(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.build()

    def build(self):
        self.controls = [ft.Text("Configurações de Atalhos", size=20)]
        for vehicle, key in self.contador.atalhos.items():
            self.controls.append(
                ft.Row(
                    controls=[
                        ft.Text(vehicle, width=100),
                        ft.TextField(
                            value=key,
                            width=50,
                            on_change=lambda e, v=vehicle: self.atualizar_atalho(v, e.control.value),
                        ),
                    ]
                )
            )

    def atualizar_atalho(self, vehicle, new_key):
        self.contador.atalhos[vehicle] = new_key
        print(f"Atalho atualizado: {vehicle} -> {new_key}")

class CategoriasConfig(ft.Column):
    def __init__(self, contador):
        super().__init__()
        self.contador = contador
        self.build()

    def build(self):
        self.nome_categoria = ft.TextField(label="Nome da Categoria")
        self.atalho_categoria = ft.TextField(label="Atalho", width=50)
        self.adicionar_button = ft.Button("Adicionar Categoria", on_click=self.adicionar_categoria)
        
        self.controls = [
            ft.Text("Configurações de Categorias", size=20),
            self.nome_categoria,
            self.atalho_categoria,
            self.adicionar_button
        ]

    def adicionar_categoria(self, e):
        nome = self.nome_categoria.value
        atalho = self.atalho_categoria.value
        if nome and atalho:
            self.contador.adicionar_categoria(nome, atalho)
            self.nome_categoria.value = ""
            self.atalho_categoria.value = ""
            self.update()
        else:
            print("Nome e atalho não podem ser vazios.")
