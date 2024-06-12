import flet as ft
from pynput import keyboard
import pandas as pd

class ContadorDigital(ft.Column):
    def __init__(self):
        super().__init__()
        self.contagem = {
            'Leve': 0,
            'VUC': 0,
            'Moto': 0,
            'Cami2': 0,
            'Cami3': 0,
            'Cami4': 0,
            'Carr5': 0,
            'Carr6': 0,
            'Carr7': 0,
            'Carr9': 0
        }
        self.atalhos = {
            'Leve': '1',
            'VUC': '2',
            'Moto': '3',
            'Cami2': '4',
            'Cami3': '5',
            'Cami4': '6',
            'Carr5': '7',
            'Carr6': '8',
            'Carr7': '9',
            'Carr9': '0'
        }
        self.labelV = {}  # Dicionário para rótulos dos veículos
        self.labelC = {}  # Dicionário para rótulos das contagens
        self.controls.extend(self.build())

    def build(self):
        controls = []
        for vehicle, count in self.contagem.items():
            row = ft.Row()  # Define o espaçamento entre os elementos
            labelVeiculo = ft.Text(f"{vehicle}:",
                                   width=50,
                                   size=16,
                                   color=ft.colors.WHITE)
            labelContagem = ft.Text(f"{count}",
                                    width=50,
                                    size=20,
                                    color=ft.colors.WHITE)
            self.labelV[vehicle] = labelVeiculo  # Armazena a referência do rótulo do veículo
            self.labelC[vehicle] = labelContagem  # Armazena a referência do rótulo da contagem
        
            add_button = ft.IconButton(ft.icons.ADD,
                                        style=ft.ButtonStyle(
                                        color=ft.colors.WHITE,
                                        bgcolor=ft.colors.GREEN,
                                        #shape="rounded",
                                        ),
                                        on_click=lambda e,
                                        v=vehicle: self.adicionar_contagem(v), 
                                        )
            remove_button = ft.IconButton(ft.icons.REMOVE,
                                              style=ft.ButtonStyle(
                                              color=ft.colors.WHITE,
                                              bgcolor=ft.colors.RED,
                                              ),
                                              on_click=lambda e,
                                              v=vehicle: self.retirar_contagem(v), 
                                              )
            row.controls.extend([
                ft.Container(
                    labelVeiculo),
                ft.Container(labelContagem),
                ft.Container(add_button),
                ft.Container(remove_button),
                ])
            controls.append(row)

            save_button = ft.IconButton(
                icon=ft.icons.SAVE,
                tooltip="Salvar",
                on_click=self.salvar15,
                style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE,  # Cor de fundo
                color=ft.colors.WHITE) # Cor do ícone
    
)
        save_button_container = ft.Container(
            content=save_button,
            alignment=ft.alignment.center
        )
        controls.append(save_button_container)
        return controls

    def adicionar_contagem(self, vehicle):
        self.contagem[vehicle] += 1
        self.labelC[vehicle].value = f"{self.contagem[vehicle]}"  # Atualiza o rótulo da contagem
        self.update()

    def retirar_contagem(self, vehicle):
        if self.contagem[vehicle] > 0:
            self.contagem[vehicle] -= 1
            self.labelC[vehicle].value = f"{self.contagem[vehicle]}"  # Atualiza o rótulo da contagem
            self.update()

    def salvar15(self, e):
        nova_linha = pd.DataFrame(self.contagem, index=[0])
        try:
            df_existente = pd.read_excel('contagem.xlsx')
            df = pd.concat([df_existente, nova_linha], ignore_index=True)
        except FileNotFoundError:
            df = nova_linha
        df.to_excel('contagem.xlsx', index=False, engine='openpyxl')
        print("Contagem salva em contagem.xlsx")

    def key_event_handler(self, key):
        try:
            if key.char in self.atalhos.values():
                vehicle = list(self.atalhos.keys())[list(self.atalhos.values()).index(key.char)]
                self.adicionar_contagem(vehicle)
        except AttributeError:
            pass


def main(page: ft.Page):
    page.window_width = 300
    page.window_height = 600
    page.title = "Contador de Veículos"
    #page.theme_mode = ft.ThemeMode.SYSTEM
    contador = ContadorDigital()
    page.window_always_on_top = True
    page.add(contador)
    # Listener para capturar eventos de teclado globalmente
    def on_press(key):
        contador.key_event_handler(key)
        page.update()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

ft.app(target=main)
