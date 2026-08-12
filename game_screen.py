import os
import time
import pygame
import config
from base_screen import BaseScreen
from button import Button
from art import draw_panel

class GameScreen(BaseScreen):
    FLASH_DURATION_SECONDS=0.18
    DAMAGE_FLASH_COLOR=(120,0,0)

    def __init__(self,manager,client_state,network):
        super().__init__(manager)
        self.client_state=client_state
        self.network=network

        self.cell_size=34
        self.board_x=295
        self.board_y=175

        self.arena_field=pygame.Rect(255,145,490,430)
        self.cached_background=self.load_game_background() 
        self.cached_board_key = None
        self.cached_board_overlay = None

        self.left_cheer_button = Button(
            (40, 98, 108, 38),
            "Cheer",
            self.cheer_left_player
        )

        self.right_cheer_button = Button(
            (852, 98, 108, 38),
            "Cheer",
            self.cheer_right_player
        )

        self.leave_game_button = Button(
            (812, 575, 155, 52),
            "Leave Game",
            self.leave_spectating,
            bg=(170, 60, 60),
            hover=(195, 78, 78),
            text_color=config.WHITE
        )   

    def load_game_background(self):
        base_dir=os.path.dirname(os.path.abspath(__file__))
        path=os.path.join(base_dir,"assets","game_arena_bg.png")

        bg=pygame.Surface((config.WINDOW_WIDTH,config.WINDOW_HEIGHT)).convert()
        bg.fill((30,40,35))

        if not os.path.exists(path):
            print("GAME BACKGROUND NOT FOUND:",path)
            return bg

        try:
            img=pygame.image.load(path).convert()
            iw,ih=img.get_size()
            sw,sh=config.WINDOW_WIDTH,config.WINDOW_HEIGHT

            scale=max(sw/iw,sh/ih)
            new_w=int(iw*scale)
            new_h=int(ih*scale)

            img=pygame.transform.smoothscale(img,(new_w,new_h))

            crop_x=(new_w-sw)//2
            crop_y=(new_h-sh)//2

            bg.blit(img,(-crop_x,-crop_y))
            print("GAME BACKGROUND LOADED:",path)
            return bg

        except Exception as e:
            print("Could not load game arena background:",e)
            return bg

    def prepare_board_layout(self,board):
        grid_w=board["width"]
        grid_h=board["height"]

        cell=min(self.arena_field.w//grid_w,self.arena_field.h//grid_h)
        self.cell_size=max(20,min(36,cell))

        board_w=grid_w*self.cell_size
        board_h=grid_h*self.cell_size

        self.board_x=self.arena_field.centerx-board_w//2
        self.board_y=self.arena_field.centery-board_h//2

    def get_palette(self):
        return {
            "pink":(255,100,180),
            "cyan":(60,240,255),
            "yellow":(255,230,60),
            "green":(80,240,120),
            "purple":(160,90,255),
            "blue":(50,130,255),
            "orange":(255,150,50),
            "red":(255,60,60),
            "white":(240,240,245),
            "black":(40,40,50),
        }

    def get_base_snake_color(self,player):
        palette=self.get_palette()
        color_name=str(player.get("color","")).lower()

        if color_name in palette:
            return palette[color_name]

        my_username=self.client_state.get("username","")
        snake_color_name=str(self.client_state.get("snake_color","pink")).lower()

        if player.get("username")==my_username:
            return palette.get(snake_color_name,palette["pink"])

        return palette["cyan"]

    def get_color(self,player):
        flash_map=self.client_state.setdefault("damage_flash_until",{})
        username=player.get("username","")
        now=time.time()

        if player.get("took_damage",False):
            flash_map[username]=now+self.FLASH_DURATION_SECONDS

        if flash_map.get(username,0)>now:
            return self.DAMAGE_FLASH_COLOR

        return self.get_base_snake_color(player)

    def send_direction_from_key(self,key_name):
        controls=self.client_state["controls"]

        if key_name==controls["up"]:
            self.network.send_move("UP")
        elif key_name==controls["down"]:
            self.network.send_move("DOWN")
        elif key_name==controls["left"]:
            self.network.send_move("LEFT")
        elif key_name==controls["right"]:
            self.network.send_move("RIGHT")

    def handle_events(self,events):
        for event in events:
            if event.type==pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if self.is_spectator():
                self.left_cheer_button.handle_event(event)
                self.right_cheer_button.handle_event(event)
                self.leave_game_button.handle_event(event)

            if event.type==pygame.KEYDOWN:
                if self.is_spectator() or self.is_countdown_active():
                    continue

                key_name=pygame.key.name(event.key)
                self.send_direction_from_key(key_name)

    def update(self):
        pass

    def is_countdown_active(self):
        return time.time()<self.client_state.get("match_starts_at",0.0)

    def is_spectator(self):
        return bool(self.client_state.get("is_spectator",False))

    def leave_spectating(self):
        self.client_state["status"] = "Leaving spectated match..."
        self.network.send_leave_spectate()

    def cheer_left_player(self):
        state = self.client_state.get("game_state") or {}
        target = state.get("player1", {}).get("username")
        if target:
            self.client_state["status"] = f"You cheered for {target}"
            self.network.send_cheer(target)

    def cheer_right_player(self):
        state = self.client_state.get("game_state") or {}
        target = state.get("player2", {}).get("username")
        if target:
            self.client_state["status"] = f"You cheered for {target}"
            self.network.send_cheer(target)

    def fit_text_to_width(self, text, font, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text

        ellipsis = "..."
        while len(text) > 0 and font.size(text + ellipsis)[0] > max_width:
            text = text[:-1]

        return text + ellipsis

    def draw_cheer_messages(self, surface, state):
        cheers = state.get("cheers", {})
        current_tick = state.get("tick_count", 0)

        left_username = state.get("player1", {}).get("username", "")
        right_username = state.get("player2", {}).get("username", "")

        left_cheer = cheers.get(left_username)
        right_cheer = cheers.get(right_username)

        if isinstance(left_cheer, dict):
            if current_tick <= left_cheer.get("expires_tick", 0):
                left_line = left_cheer.get("message", "")
                left_line = self.fit_text_to_width(left_line, config.TINY_FONT, 300)

                shadow = config.TINY_FONT.render(left_line, True, (20, 15, 10))
                text = config.TINY_FONT.render(left_line, True, config.WHITE)

                surface.blit(shadow, (30, 143))
                surface.blit(text, (28, 141))

        if isinstance(right_cheer, dict):
            if current_tick <= right_cheer.get("expires_tick", 0):
                right_line = right_cheer.get("message", "")
                right_line = self.fit_text_to_width(right_line, config.TINY_FONT, 300)

                shadow = config.TINY_FONT.render(right_line, True, (20, 15, 10))
                text = config.TINY_FONT.render(right_line, True, config.WHITE)

                text_x = 970 - text.get_width()

                surface.blit(shadow, (text_x + 2, 143))
                surface.blit(text, (text_x, 141))


    def draw_spectator_controls(self, surface, state):
        if not self.is_spectator():
            return

        self.left_cheer_button.draw(surface)
        self.right_cheer_button.draw(surface)
        self.leave_game_button.draw(surface)

    def get_countdown_value(self):
        remaining=self.client_state.get("match_starts_at",0.0)-time.time()
        return max(0,int(remaining+0.999))

    def draw_countdown_overlay(self,surface):
        seconds=self.get_countdown_value()
        if seconds<=0:
            return

        overlay=pygame.Surface((config.WINDOW_WIDTH,config.WINDOW_HEIGHT),pygame.SRCALPHA)
        overlay.fill((10,16,40,110))
        surface.blit(overlay,(0,0))

        box=pygame.Rect(340,255,320,170)
        draw_panel(surface,box,config.PANEL_GLASS)

        title=config.NORMAL_FONT.render("Match starts in",True,config.WHITE)
        number=config.TITLE_FONT.render(str(seconds),True,config.WHITE)
        hint=config.TINY_FONT.render("Get ready...",True,config.GRAY)

        surface.blit(title,(box.centerx-title.get_width()//2,box.y+28))
        surface.blit(number,(box.centerx-number.get_width()//2,box.y+68))
        surface.blit(hint,(box.centerx-hint.get_width()//2,box.y+130))

    def get_interpolation_alpha(self):
        received_at=self.client_state.get("game_state_received_at",0.0)
        tick_rate=max(1,self.client_state.get("server_tick_rate",3))

        if received_at==0.0:
            return 1.0

        tick_duration=1.0/tick_rate
        alpha=(time.time()-received_at)/tick_duration
        return max(0.0,min(1.0,alpha))

    def interpolate_snake(self,previous_player,current_player,alpha):
        if not previous_player:
            return current_player

        prev_body=previous_player.get("body",[])
        curr_body=current_player.get("body",[])

        if len(prev_body)!=len(curr_body):
            return current_player

        interpolated_player=dict(current_player)
        interpolated_body=[]

        for prev_segment,curr_segment in zip(prev_body,curr_body):
            interpolated_body.append({
                "x":prev_segment["x"]+(curr_segment["x"]-prev_segment["x"])*alpha,
                "y":prev_segment["y"]+(curr_segment["y"]-prev_segment["y"])*alpha,
            })

        interpolated_player["body"]=interpolated_body
        return interpolated_player

    def draw_top_timer(self,surface,state):
        time_value=str(state.get("remaining_time",0))
        text=f"TIME: {time_value}"

        shadow=config.NORMAL_FONT.render(text,True,(30,20,10))
        gold=config.NORMAL_FONT.render(text,True,(255,220,90))
        glow=config.NORMAL_FONT.render(text,True,(255,245,180))

        x=config.WINDOW_WIDTH//2-gold.get_width()//2
        y=32

        surface.blit(shadow,(x+2,y+3))
        surface.blit(gold,(x,y))
        surface.blit(glow,(x+1,y+1))

    def draw_single_health_bar(self,surface,x,y,w,player,side):
        username=str(player.get("username","Player"))

        actual_hp=int(player.get("health",0))
        actual_hp=max(0,actual_hp)

        bar_hp=min(100,actual_hp)
        ratio=bar_hp/100

        if ratio>0.6:
            fill=(70,220,110)
        elif ratio>0.3:
            fill=(255,190,60)
        else:
            fill=(255,70,70)

        name_text=f"{username}: {actual_hp} HP"
        name_shadow=config.SMALL_FONT.render(name_text,True,(20,15,10))
        name_surf=config.SMALL_FONT.render(name_text,True,config.WHITE)

        if side=="left":
            name_x=x
        else:
            name_x=x+w-name_surf.get_width()

        surface.blit(name_shadow,(name_x+2,y+2))
        surface.blit(name_surf,(name_x,y))

        bar_y=y+28
        bar_h=17

        shadow_rect=pygame.Rect(x+2,bar_y+3,w,bar_h)
        pygame.draw.rect(surface,(20,16,12),shadow_rect,border_radius=9)

        bar_bg=pygame.Rect(x,bar_y,w,bar_h)
        pygame.draw.rect(surface,(55,42,34),bar_bg,border_radius=9)
        pygame.draw.rect(surface,(230,210,150),bar_bg,2,border_radius=9)

        fill_w=int(w*ratio)

        if fill_w>0:
            bar_fill=pygame.Rect(x,bar_y,fill_w,bar_h)
            pygame.draw.rect(surface,fill,bar_fill,border_radius=9)

            shine=pygame.Surface((fill_w,max(2,bar_h//3)),pygame.SRCALPHA)
            shine.fill((255,255,255,50))
            surface.blit(shine,(x,bar_y+2))

        pygame.draw.rect(surface,(255,255,255),bar_bg,1,border_radius=9)

    def draw_top_health_bars(self,surface,state):
        p1=state["player1"]
        p2=state["player2"]

        self.draw_single_health_bar(surface,30,25,290,p1,"left")
        self.draw_single_health_bar(surface,680,25,290,p2,"right")

    def draw_board(self,surface,board):
        self.prepare_board_layout(board)

        grid_w=board["width"]
        grid_h=board["height"]

        board_w=grid_w*self.cell_size
        board_h=grid_h*self.cell_size

        board_key = (grid_w, grid_h, self.cell_size)

        if self.cached_board_key != board_key or self.cached_board_overlay is None:
            overlay=pygame.Surface((board_w,board_h),pygame.SRCALPHA)

            for row in range(grid_h):
                for col in range(grid_w):
                    cell=pygame.Rect(
                        col*self.cell_size,
                        row*self.cell_size,
                        self.cell_size,
                        self.cell_size
                    )

                    if (row+col)%2==0:
                        pygame.draw.rect(overlay,(255,230,150,28),cell)
                    else:
                        pygame.draw.rect(overlay,(180,120,55,22),cell)

            for row in range(grid_h+1):
                y=row*self.cell_size
                pygame.draw.line(overlay,(255,245,190,55),(0,y),(board_w,y),1)

            for col in range(grid_w+1):
                x=col*self.cell_size
                pygame.draw.line(overlay,(255,245,190,55),(x,0),(x,board_h),1)

            self.cached_board_key = board_key
            self.cached_board_overlay = overlay

        surface.blit(self.cached_board_overlay,(self.board_x,self.board_y))

        border_rect=pygame.Rect(self.board_x,self.board_y,board_w,board_h)
        pygame.draw.rect(surface,(255,230,140),border_rect,2,border_radius=8)

    def draw_pies(self,surface,pies):
        for pie in pies:
            pos=pie["position"]
            x=self.board_x+pos["x"]*self.cell_size+self.cell_size//2
            y=self.board_y+pos["y"]*self.cell_size+self.cell_size//2

            if pie.get("is_power",False):
                glow=pygame.Surface((42,42),pygame.SRCALPHA)
                pygame.draw.circle(glow,(180,80,255,80),(21,21),20)
                surface.blit(glow,(x-21,y-21))

                pygame.draw.circle(surface,(88,30,130),(x,y+4),12)
                pygame.draw.circle(surface,(170,70,255),(x,y+1),11)
                pygame.draw.circle(surface,(220,160,255),(x-4,y-3),4)
                pygame.draw.arc(surface,(245,220,255),(x-10,y-2,20,14),0.2,3.0,2)
                pygame.draw.line(surface,(92,66,34),(x,y-8),(x,y-14),2)
                pygame.draw.ellipse(surface,(74,138,68),(x+2,y-15,7,4))

            else:
                pygame.draw.circle(surface,(170,110,56),(x,y+4),11)
                pygame.draw.circle(surface,(224,176,96),(x,y+1),10)
                pygame.draw.arc(surface,(136,86,40),(x-10,y-2,20,14),0.2,3.0,2)
                pygame.draw.line(surface,(92,66,34),(x,y-8),(x,y-14),2)
                pygame.draw.ellipse(surface,(74,138,68),(x+2,y-15,7,4))

    def draw_obstacles(self,surface,obstacles):
        for ob in obstacles:
            pos=ob["position"]

            cell_x=self.board_x+pos["x"]*self.cell_size
            cell_y=self.board_y+pos["y"]*self.cell_size

            pad=max(3,self.cell_size//10)
            x=cell_x+pad
            y=cell_y+pad
            size=self.cell_size-(pad*2)

            shadow=pygame.Rect(x+3,y+4,size,size)
            pygame.draw.rect(surface,(18,18,24),shadow)

            base=pygame.Rect(x,y,size,size)
            pygame.draw.rect(surface,(84,86,92),base)
            pygame.draw.rect(surface,(38,40,46),base,2)

            top_face=[
                (x,y),
                (x+size,y),
                (x+size-5,y+5),
                (x+5,y+5),
            ]
            left_face=[
                (x,y),
                (x+5,y+5),
                (x+5,y+size-5),
                (x,y+size),
            ]
            bottom_face=[
                (x,y+size),
                (x+size,y+size),
                (x+size-5,y+size-5),
                (x+5,y+size-5),
            ]

            pygame.draw.polygon(surface,(138,140,146),top_face)
            pygame.draw.polygon(surface,(58,60,66),left_face)
            pygame.draw.polygon(surface,(48,50,56),bottom_face)

            inner=pygame.Rect(x+5,y+5,size-10,size-10)
            pygame.draw.rect(surface,(102,104,110),inner)
            pygame.draw.rect(surface,(54,56,62),inner,2)

            crack_color=(38,40,46)
            highlight=(160,162,168)

            pygame.draw.line(surface,crack_color,(inner.x+4,inner.y+7),(inner.x+13,inner.y+3),2)
            pygame.draw.line(surface,crack_color,(inner.x+13,inner.y+3),(inner.x+18,inner.y+10),2)

            pygame.draw.line(surface,crack_color,(inner.right-6,inner.y+8),(inner.right-14,inner.y+15),2)
            pygame.draw.line(surface,crack_color,(inner.right-14,inner.y+15),(inner.right-8,inner.y+23),2)

            pygame.draw.line(surface,(70,72,78),(inner.x+3,inner.bottom-7),(inner.right-5,inner.bottom-7),2)
            pygame.draw.line(surface,highlight,(inner.x+3,inner.y+3),(inner.right-4,inner.y+3),1)
            pygame.draw.line(surface,highlight,(inner.x+3,inner.y+3),(inner.x+3,inner.bottom-4),1)

            corner=4
            pygame.draw.rect(surface,(35,37,43),(x,y,corner,corner))
            pygame.draw.rect(surface,(35,37,43),(x+size-corner,y,corner,corner))
            pygame.draw.rect(surface,(35,37,43),(x,y+size-corner,corner,corner))
            pygame.draw.rect(surface,(35,37,43),(x+size-corner,y+size-corner,corner,corner))

    def draw_snake(self,surface,player):
        base=self.get_color(player)
        dark=(max(0,base[0]-75),max(0,base[1]-75),max(0,base[2]-75))
        light=(min(255,base[0]+35),min(255,base[1]+35),min(255,base[2]+35))

        body=player["body"]
        if not body:
            return

        pts=[]
        for segment in body:
            x=self.board_x+segment["x"]*self.cell_size+self.cell_size//2
            y=self.board_y+segment["y"]*self.cell_size+self.cell_size//2
            pts.append((x,y))

        for i in range(len(pts)-1):
            a=pts[i]
            b=pts[i+1]
            width=max(10,self.cell_size-12-i)

            pygame.draw.line(surface,dark,a,b,width)
            pygame.draw.line(surface,base,(a[0],a[1]-2),(b[0],b[1]-2),max(4,width-6))

        for i,(x,y) in enumerate(pts):
            r=max(7,self.cell_size//2-4-i)
            pygame.draw.circle(surface,dark,(x,y),r)
            pygame.draw.circle(surface,base,(x,y-1),max(4,r-2))

            shine_rect=pygame.Rect(x-r//2,y-r//2-2,max(3,r),max(2,r//2))
            pygame.draw.ellipse(surface,light,shine_rect)

        hx,hy=pts[0]
        pygame.draw.circle(surface,config.WHITE,(hx-5,hy-4),3)
        pygame.draw.circle(surface,config.WHITE,(hx+5,hy-4),3)
        pygame.draw.circle(surface,config.BLACK,(hx-5,hy-4),1)
        pygame.draw.circle(surface,config.BLACK,(hx+5,hy-4),1)

        if player.get("has_crown",False):
            self.draw_crown(surface,hx,hy)

    def draw_crown(self,surface,hx,hy):
        hx=int(hx)
        hy=int(hy)

        crown_w=max(22,self.cell_size-8)
        crown_h=max(14,self.cell_size//2)

        left=hx-crown_w//2
        right=hx+crown_w//2
        top=hy-self.cell_size//2-crown_h+4
        base=top+crown_h

        points=[
            (left,base),
            (left+4,top+5),
            (hx-crown_w//5,base-4),
            (hx,top),
            (hx+crown_w//5,base-4),
            (right-4,top+5),
            (right,base),
        ]

        pygame.draw.polygon(surface,(255,215,70),points)
        pygame.draw.polygon(surface,(120,80,20),points,2)

        pygame.draw.circle(surface,(255,245,170),(hx,top),3)
        pygame.draw.circle(surface,(255,245,170),(left+4,top+5),2)
        pygame.draw.circle(surface,(255,245,170),(right-4,top+5),2)

        base_rect=pygame.Rect(left,base-4,crown_w,6)
        pygame.draw.rect(surface,(235,170,45),base_rect,border_radius=3)
        pygame.draw.rect(surface,(120,80,20),base_rect,1,border_radius=3)


    def draw_status(self,surface,state):
        pass

    def draw_chat_notifications(self,surface):
        live_notes=[]
        for note in self.client_state.get("chat_notifications",[]):
            if note.get("expires_at",0)>time.time():
                live_notes.append(note)

        self.client_state["chat_notifications"]=live_notes

        y=140
        for note in live_notes[-2:]:
            box=pygame.Rect(690,y,260,50)
            pygame.draw.rect(surface,(188,156,78),box,border_radius=14)
            inner=box.inflate(-4,-4)
            pygame.draw.rect(surface,(8,18,55),inner,border_radius=12)
            txt=config.TINY_FONT.render(note.get("message","")[:34],True,config.WHITE)
            surface.blit(txt,(707,y+16))
            y+=58

    def draw(self,surface):
        surface.blit(self.cached_background,(0,0))

        state=self.client_state.get("game_state")
        if not state:
            waiting=config.NORMAL_FONT.render("Waiting for game state...",True,config.WHITE)
            surface.blit(waiting,(360,320))
            return

        self.draw_top_health_bars(surface,state)
        self.draw_top_timer(surface,state)
        self.draw_cheer_messages(surface,state)
        self.draw_spectator_controls(surface,state)

        self.draw_board(surface,state["board"])
        self.draw_pies(surface,state["pies"])
        self.draw_obstacles(surface,state["obstacles"])

        previous_state=self.client_state.get("previous_game_state")
        alpha=self.get_interpolation_alpha()

        player1_to_draw=state["player1"]
        player2_to_draw=state["player2"]

        if previous_state:
            player1_to_draw=self.interpolate_snake(previous_state.get("player1"),state["player1"],alpha)
            player2_to_draw=self.interpolate_snake(previous_state.get("player2"),state["player2"],alpha)

        self.draw_snake(surface,player1_to_draw)
        self.draw_snake(surface,player2_to_draw)

        self.draw_status(surface,state)
        self.draw_chat_notifications(surface)
        self.draw_countdown_overlay(surface)