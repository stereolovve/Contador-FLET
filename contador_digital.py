# contador_digital.py
import flet as ft
from sqlalchemy.orm import Session
from database import engine, Contagem, get_db
from contextlib import contextmanager

@contextmanager
def get_session():
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()

class ContadorDigital(ft.Column):
    def __init__(self):
        super().__init__()
        self.contagem = {}
        self.atalhos = {}
        self.labelV = {}
        self.labelC = {}
        self.controls.extend(self.build())
        self.carregar_dados_iniciais()

    def carregar_dados_iniciais(self):
        with get_session() as session:
            categorias = session.query(Contagem).all()
            for categoria in categorias:
                self.contagem[categoria.categoria] = categoria.quantidade
                self.atalhos[categoria.categoria] = str(len(self.atalhos) + 1)

    def build(self):
        controls = []
        for vehicle, count in self.contagem.items():
            row = ft.Row()
            labelVeiculo = ft.Text(f"{vehicle}:", width=50, size=16, color=ft.colors.WHITE)
            labelContagem = ft.Text(f"{count}", width=50, size=20, color=ft.colors.WHITE)
            self.labelV[vehicle] = labelVeiculo
            self.labelC[vehicle] = labelContagem
        
            add_button = ft.IconButton(ft.icons.ADD, style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.GREEN), on_click=lambda e, v=vehicle: self.adicionar_contagem(v))
            remove_button = ft.IconButton(ft.icons.REMOVE, style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.RED), on_click=lambda e, v=vehicle: self.retirar_contagem(v))
            row.controls.extend([ft.Container(labelVeiculo), ft.Container(labelContagem), ft.Container(add_button), ft.Container(remove_button)])
            controls.append(row)

        save_button = ft.IconButton(icon=ft.icons.SAVE, tooltip="Salvar", on_click=self.salvar15, style=ft.ButtonStyle(bgcolor=ft.colors.BLUE, color=ft.colors.WHITE))
        save_button_container = ft.Container(content=save_button, alignment=ft.alignment.center)
        controls.append(save_button_container)
        return controls

    def adicionar_contagem(self, vehicle):
        self.contagem[vehicle] += 1
        self.labelC[vehicle].value = f"{self.contagem[vehicle]}"
        self.update()

    def retirar_contagem(self, vehicle):
        if self.contagem[vehicle] > 0:
            self.contagem[vehicle] -= 1
            self.labelC[vehicle].value = f"{self.contagem[vehicle]}"
            self.update()

    def salvar15(self, e):
        with get_session() as session:
            for vehicle, count in self.contagem.items():
                contagem = session.query(Contagem).filter(Contagem.categoria == vehicle).first()
                if contagem:
                    contagem.quantidade = count
                else:
                    contagem = Contagem(categoria=vehicle, quantidade=count)
                    session.add(contagem)
            session.commit()
        print("Contagem salva no banco de dados")

    def key_event_handler(self, key):
        try:
            if key.char in self.atalhos.values():
                vehicle = list(self.atalhos.keys())[list(self.atalhos.values()).index(key.char)]
                self.adicionar_contagem(vehicle)
        except AttributeError:
            pass

    def adicionar_categoria(self, nome, atalho):
        if nome not in self.contagem and atalho not in self.atalhos.values():
            self.contagem[nome] = 0
            self.atalhos[nome] = atalho
            self.controls = self.build()
            self.update()
            with get_session() as session:
                nova_categoria = Contagem(categoria=nome, quantidade=0)
                session.add(nova_categoria)
                session.commit()
        else:
            print("Categoria já existe ou atalho já está em uso.")
