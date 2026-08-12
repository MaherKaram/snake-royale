import os
import pygame
import config
from base_screen import BaseScreen
from button import Button

class ResultScreen(BaseScreen):
    def __init__(self,manager,client_state,network):
        super().__init__(manager)
        self.client_state=client_state
        self.network=network
        self.result=client_state.get("result",{}) or {}

        self.back_button=Button((370,560,260,75),"Back to Lobby",self.back_to_lobby)
        self.background=self.load_background()

    def load_background(self):
        path=os.path.join("assets","snake_royale_bg.png")
        try:
            img=pygame.image.load(path).convert()
            img=pygame.transform.smoothscale(img,(config.WINDOW_WIDTH,config.WINDOW_HEIGHT))
            return img
        except Exception:
            bg=pygame.Surface((config.WINDOW_WIDTH,config.WINDOW_HEIGHT))
            bg.fill((12,16,28))
            return bg

    def back_to_lobby(self):
        from lobby_screen import LobbyScreen

        self.client_state["result"]=None
        self.client_state["game_state"]=None
        self.client_state["in_game"]=False
        self.client_state["previous_game_state"]=None
        self.client_state["game_state_received_at"]=0.0
        self.client_state["is_spectator"]=False
        self.client_state["watching_players"]=[]

        lobby=LobbyScreen(self.manager,self.client_state,self.network)
        lobby.set_players(self.client_state.get("online_players",[]))
        self.manager.set_screen(lobby)

    def format_reason(self,winner,reason):
        reason=str(reason or "").strip().lower()

        if reason=="health_zero":
            return f"{winner} won because the opponent's health reached zero." if winner else "A player lost all health."
        if reason=="time_up":
            return f"{winner} won by having more health when time ran out." if winner else "Time ran out."
        if reason=="disconnect":
            return f"{winner} won because the opponent disconnected." if winner else "A player disconnected."
        if reason=="wall_collision":
            return f"{winner} won because the opponent hit a wall." if winner else "A wall collision ended the match."
        if reason=="snake_collision":
            return f"{winner} won because the opponent collided with a snake." if winner else "A snake collision ended the match."
        if reason=="obstacle_collision":
            return f"{winner} won because the opponent hit an obstacle." if winner else "An obstacle collision ended the match."
        if reason:
            clean=reason.replace("_"," ").capitalize()
            return clean
        return "Final result"

    def handle_events(self,events):
        for event in events:
            if event.type==pygame.QUIT:
                pygame.quit()
                raise SystemExit
            self.back_button.handle_event(event)

    def update(self):
        self.result=self.client_state.get("result",{}) or {}

    def draw_winner_badge(self,surface,winner):
        badge=pygame.Rect(355,150,290,62)
        pygame.draw.rect(surface,(188,156,78),badge,border_radius=16)
        inner=badge.inflate(-6,-6)
        pygame.draw.rect(surface,(8,18,55),inner,border_radius=14)

        title="DRAW" if winner is None else "VICTORY"
        txt=config.NORMAL_FONT.render(title,True,(255,220,90))
        surface.blit(txt,(badge.centerx-txt.get_width()//2,badge.centery-txt.get_height()//2))

    def draw_score_row(self,surface,y,username,hp,is_winner=False):
        row=pygame.Rect(260,y,480,56)
        pygame.draw.rect(surface,(18,24,56),row,border_radius=14)
        border=(255,220,90) if is_winner else (95,220,255)
        pygame.draw.rect(surface,border,row,2,border_radius=14)

        name=config.NORMAL_FONT.render(str(username),True,config.WHITE)
        score=config.NORMAL_FONT.render(f"{hp} HP",True,(255,245,180) if is_winner else config.WHITE)

        surface.blit(name,(row.x+20,row.y+13))
        surface.blit(score,(row.right-score.get_width()-20,row.y+13))

    def draw(self,surface):
        surface.blit(self.background,(0,0))

        overlay=pygame.Surface((config.WINDOW_WIDTH,config.WINDOW_HEIGHT),pygame.SRCALPHA)
        overlay.fill((0,0,0,95))
        surface.blit(overlay,(0,0))

        panel=pygame.Rect(180,110,640,470)
        pygame.draw.rect(surface,(8,18,55),panel,border_radius=24)
        pygame.draw.rect(surface,(95,220,255),panel,3,border_radius=24)

        winner=self.result.get("winner")
        reason=self.result.get("reason","")
        final_health=self.result.get("final_health",{})
        remaining_time=self.result.get("remaining_time",0)

        if not final_health:
            p1=self.result.get("player1_username","Player 1")
            p2=self.result.get("player2_username","Player 2")
            final_health={
                p1:self.result.get("player1_health",0),
                p2:self.result.get("player2_health",0)
            }

        self.draw_winner_badge(surface,winner)

        title_text="DRAW!" if winner is None else f"{winner} WINS!"
        title=config.TITLE_FONT.render(title_text,True,(255,220,90))
        title_rect=title.get_rect(center=(500,245))
        surface.blit(title,title_rect)

        reason_line=self.format_reason(winner,reason)
        reason_text=config.SMALL_FONT.render(reason_line,True,config.WHITE)
        reason_rect=reason_text.get_rect(center=(500,294))
        surface.blit(reason_text,reason_rect)

        time_text=config.TINY_FONT.render(f"Time left: {remaining_time}",True,config.GRAY)
        surface.blit(time_text,(500-time_text.get_width()//2,325))

        y=370
        for username,hp in final_health.items():
            self.draw_score_row(surface,y,username,hp,is_winner=(winner==username))
            y+=72

        self.back_button.draw(surface)