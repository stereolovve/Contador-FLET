# main.py
import flet as ft
from pynput import keyboard
from contador_digital import ContadorDigital
from configuracoes import TemaConfig, AtalhosConfig, CategoriasConfig

def main(page: ft.Page):
    contador = ContadorDigital()

    def mudar_aba(e):
        page.controls.clear()
        page.add(tabs)  # Re-adiciona as tabs para manter a interface consistente
        if e.control.selected_index == 0:
            page.add(contador)
        elif e.control.selected_index == 1:
            configuracoes_tabs = ft.Tabs(
                tabs=[
                    ft.Tab(text="Tema", content=TemaConfig(page)),
                    ft.Tab(text="Atalhos", content=AtalhosConfig(contador)),
                    ft.Tab(text="Categorias", content=CategoriasConfig(contador)),
                ]
            )
            page.add(configuracoes_tabs)
        page.update()

    tabs = ft.Tabs(
        tabs=[
            ft.Tab(text="Contador"),
            ft.Tab(text="Configurações"),
        ],
        on_change=mudar_aba
    )

    page.add(tabs)
    page.add(contador)  # Adiciona o contador inicialmente

    page.window_width = 300
    page.window_height = 650
    page.title = "Contador de Veículos"
    page.window_always_on_top = True

    # Listener para capturar eventos de teclado globalmente
    def on_press(key):
        contador.key_event_handler(key)
        page.update()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

ft.app(target=main)
