import os
import pygame
import config
from base_screen import BaseScreen
from username_screen import UsernameScreen
from button import Button
from text_input import TextInput

class ConnectScreen(BaseScreen):
    def __init__(self,manager,client_state,network):
        super().__init__(manager)
        self.client_state=client_state
        self.network=network

        self.ip_input = TextInput((350, 470, 300, 58), "Server IP", "", text_align="center")
        self.port_input = TextInput((350, 545, 300, 58), "Port", "", text_align="center")
        self.connect_button=Button((370,625,260,72),"CONNECT",self.try_connect)
        self.error=""

        self.background=self.load_background()

    def load_background(self):
        path=os.path.join("assets","snake_royale_bg.png")
        img=pygame.image.load(path).convert()
        img=pygame.transform.smoothscale(img,(config.WINDOW_WIDTH,config.WINDOW_HEIGHT))
        return img

    def try_connect(self):
        ip=self.ip_input.text.strip()
        port=self.port_input.text.strip()

        if ip=="" or port=="":
            self.error="Please enter IP and port."
            return

        ok,msg=self.network.connect(ip,port)
        if ok:
            self.client_state["server_ip"]=ip
            self.client_state["server_port"]=port
            self.error=""
            self.manager.set_screen(UsernameScreen(self.manager,self.client_state,self.network))
        else:
            self.error=f"Connection failed"

    def handle_events(self,events):
        for event in events:
            if event.type==pygame.QUIT:
                pygame.quit()
                raise SystemExit

            self.ip_input.handle_event(event)
            self.port_input.handle_event(event)
            self.connect_button.handle_event(event)

    def update(self):
        pass

    def draw(self,surface):
        surface.blit(self.background,(0,0))

        self.ip_input.draw(surface)
        self.port_input.draw(surface)
        self.connect_button.draw(surface)

        hint = config.TINY_FONT.render(
            "Use 127.0.0.1 only on the server laptop. Other laptops must use the server's Wi-Fi IPv4 address.",
            True,
            (230, 240, 255)
        )
        surface.blit(hint, (198, 602))

        if self.error:
            err=config.SMALL_FONT.render(self.error,True,config.ERROR_COLOR)
            surface.blit(err,(350,440))