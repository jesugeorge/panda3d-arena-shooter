"""
Arena Shooter - A top-down 2D arena game built with Panda3D
Author: Jesudas George
Description: A top-down arena shooter where the player defends against
             waves of enemies. Features collision detection, scoring,
             health system, and progressive wave difficulty.
"""

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectLabel
from panda3d.core import (
    CollisionTraverser, CollisionNode, CollisionSphere,
    CollisionHandlerQueue, BitMask32,
    TextNode, Vec4, Vec3, Point3,
    AmbientLight, DirectionalLight,
    CardMaker, NodePath
)
import random
import math
import sys


# ── Constants ────────────────────────────────────────────────────────────────
ARENA_SIZE      = 20.0
PLAYER_SPEED    = 8.0
BULLET_SPEED    = 18.0
ENEMY_SPEED     = 3.5
BULLET_LIFETIME = 2.5   # seconds
FIRE_COOLDOWN   = 0.22  # seconds between shots
MAX_HEALTH      = 5
WAVE_ENEMY_BASE = 5     # enemies in wave 1


# ── Colour helpers ───────────────────────────────────────────────────────────
def _rgba(r, g, b, a=1.0):
    return Vec4(r / 255, g / 255, b / 255, a)


COLOUR_PLAYER  = _rgba(50,  200, 255)
COLOUR_ENEMY   = _rgba(255,  80,  80)
COLOUR_BULLET  = _rgba(255, 240,  60)
COLOUR_FLOOR   = _rgba( 30,  30,  45)
COLOUR_WALL    = _rgba( 80,  80, 100)
COLOUR_HUD_BG  = _rgba(  0,   0,   0, 0.55)


# ── Utility: build a flat square NodePath ────────────────────────────────────
def make_quad(name, size, colour):
    cm = CardMaker(name)
    half = size / 2.0
    cm.setFrame(-half, half, -half, half)
    np = NodePath(cm.generate())
    np.setColor(colour)
    np.setP(-90)          # lay flat on XY plane
    np.setBin("opaque", 0)
    return np


# ── Entity classes ───────────────────────────────────────────────────────────
class Player:
    def __init__(self, game):
        self.game   = game
        self.health = MAX_HEALTH
        self.alive  = True

        self.node = make_quad("player", 1.2, COLOUR_PLAYER)
        self.node.reparentTo(game.render)
        self.node.setPos(0, 0, 0.05)

        # collision sphere
        c_node = CollisionNode("player_col")
        c_node.addSolid(CollisionSphere(0, 0, 0, 0.6))
        c_node.setFromCollideMask(BitMask32.bit(1))
        c_node.setIntoCollideMask(BitMask32.allOff())
        self.col_np = self.node.attachNewNode(c_node)
        game.c_trav.addCollider(self.col_np, game.c_handler)

    def move(self, dx, dy, dt):
        x = self.node.getX() + dx * PLAYER_SPEED * dt
        y = self.node.getY() + dy * PLAYER_SPEED * dt
        half = ARENA_SIZE / 2 - 0.8
        x = max(-half, min(half, x))
        y = max(-half, min(half, y))
        self.node.setPos(x, y, 0.05)

    def take_damage(self):
        self.health -= 1
        if self.health <= 0:
            self.alive = False
            self.node.hide()

    def cleanup(self):
        self.game.c_trav.removeCollider(self.col_np)
        self.node.removeNode()


class Bullet:
    def __init__(self, game, x, y, dx, dy):
        self.game     = game
        self.dx       = dx
        self.dy       = dy
        self.lifetime = BULLET_LIFETIME
        self.alive    = True

        self.node = make_quad("bullet", 0.35, COLOUR_BULLET)
        self.node.reparentTo(game.render)
        self.node.setPos(x, y, 0.1)

        c_node = CollisionNode("bullet_col")
        c_node.addSolid(CollisionSphere(0, 0, 0, 0.18))
        c_node.setFromCollideMask(BitMask32.bit(2))
        c_node.setIntoCollideMask(BitMask32.allOff())
        self.col_np = self.node.attachNewNode(c_node)
        game.c_trav.addCollider(self.col_np, game.c_handler)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.destroy()
            return
        x = self.node.getX() + self.dx * BULLET_SPEED * dt
        y = self.node.getY() + self.dy * BULLET_SPEED * dt
        half = ARENA_SIZE / 2
        if abs(x) > half or abs(y) > half:
            self.destroy()
            return
        self.node.setPos(x, y, 0.1)

    def destroy(self):
        if not self.alive:
            return
        self.alive = False
        self.game.c_trav.removeCollider(self.col_np)
        self.node.removeNode()


class Enemy:
    def __init__(self, game, x, y):
        self.game  = game
        self.alive = True

        self.node = make_quad("enemy", 1.1, COLOUR_ENEMY)
        self.node.reparentTo(game.render)
        self.node.setPos(x, y, 0.05)

        c_node = CollisionNode("enemy_col")
        c_node.addSolid(CollisionSphere(0, 0, 0, 0.55))
        c_node.setIntoCollideMask(BitMask32.bit(1) | BitMask32.bit(2))
        self.col_np = self.node.attachNewNode(c_node)

    def update(self, dt, target_x, target_y):
        ex, ey = self.node.getX(), self.node.getY()
        ddx, ddy = target_x - ex, target_y - ey
        dist = math.hypot(ddx, ddy)
        if dist > 0.01:
            nx, ny = ddx / dist, ddy / dist
            self.node.setPos(ex + nx * ENEMY_SPEED * dt,
                             ey + ny * ENEMY_SPEED * dt, 0.05)

    def destroy(self):
        if not self.alive:
            return
        self.alive = False
        self.node.removeNode()


# ── Main game ────────────────────────────────────────────────────────────────
class ArenaShooter(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(*_rgba(15, 15, 25))
        self._setup_camera()
        self._setup_lights()
        self._build_arena()
        self._setup_collision()
        self._setup_input()
        self._setup_hud()
        self._new_game()

    # ── Setup ────────────────────────────────────────────────────────────────
    def _setup_camera(self):
        self.camera.setPos(0, 0, 38)
        self.camera.setP(-90)

    def _setup_lights(self):
        amb = AmbientLight("amb")
        amb.setColor(Vec4(0.85, 0.85, 0.90, 1))
        self.render.setLight(self.render.attachNewNode(amb))

        sun = DirectionalLight("sun")
        sun.setColor(Vec4(1, 1, 0.95, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(30, -60, 0)
        self.render.setLight(sun_np)

    def _build_arena(self):
        # floor
        floor = make_quad("floor", ARENA_SIZE, COLOUR_FLOOR)
        floor.reparentTo(self.render)
        floor.setPos(0, 0, 0)

        # walls (4 thin quads as borders)
        half = ARENA_SIZE / 2
        thick = 0.5
        for pos, scale in [
            ((0,  half + thick/2, 0.1), (ARENA_SIZE + thick*2, thick)),
            ((0, -half - thick/2, 0.1), (ARENA_SIZE + thick*2, thick)),
            (( half + thick/2, 0, 0.1), (thick, ARENA_SIZE)),
            ((-half - thick/2, 0, 0.1), (thick, ARENA_SIZE)),
        ]:
            w = make_quad("wall", 1, COLOUR_WALL)
            w.reparentTo(self.render)
            w.setPos(*pos)
            w.setScale(scale[0], 1, scale[1])

    def _setup_collision(self):
        self.c_trav    = CollisionTraverser("main")
        self.c_handler = CollisionHandlerQueue()

    def _setup_input(self):
        self.keys = {k: False for k in ("w", "s", "a", "d")}
        for k in self.keys:
            self.accept(k,       self._key_down, [k])
            self.accept(k + "-up", self._key_up,   [k])
        self.accept("mouse1",    self._shoot)
        self.accept("escape",    sys.exit)
        self.accept("r",         self._new_game)

    def _key_down(self, k): self.keys[k] = True
    def _key_up(self,   k): self.keys[k] = False

    def _setup_hud(self):
        # Score
        self.score_text = OnscreenText(
            text="Score: 0", pos=(-1.3, 0.90),
            scale=0.07, fg=(1, 1, 1, 1),
            align=TextNode.ALeft, mayChange=True
        )
        # Health
        self.health_text = OnscreenText(
            text=f"Health: {'♥ ' * MAX_HEALTH}", pos=(-1.3, 0.80),
            scale=0.065, fg=(1, 0.3, 0.3, 1),
            align=TextNode.ALeft, mayChange=True
        )
        # Wave
        self.wave_text = OnscreenText(
            text="Wave: 1", pos=(1.3, 0.90),
            scale=0.07, fg=(0.8, 0.8, 1, 1),
            align=TextNode.ARight, mayChange=True
        )
        # Centre message (game over / wave clear)
        self.centre_text = OnscreenText(
            text="", pos=(0, 0),
            scale=0.12, fg=(1, 1, 0.4, 1),
            align=TextNode.ACenter, mayChange=True
        )
        self.sub_text = OnscreenText(
            text="", pos=(0, -0.15),
            scale=0.065, fg=(1, 1, 1, 0.85),
            align=TextNode.ACenter, mayChange=True
        )

    # ── Game state ───────────────────────────────────────────────────────────
    def _new_game(self):
        # clear old entities
        for attr in ("player", "bullets", "enemies"):
            obj = getattr(self, attr, None)
            if obj is None:
                continue
            if attr == "player" and obj is not None:
                try: obj.cleanup()
                except Exception: pass
            elif isinstance(obj, list):
                for e in obj:
                    try: e.destroy()
                    except Exception: pass

        self.score         = 0
        self.wave          = 1
        self.fire_timer    = 0.0
        self.bullets       = []
        self.enemies       = []
        self.game_over     = False
        self.wave_paused   = False
        self.wave_pause_t  = 0.0

        self.player = Player(self)
        self._spawn_wave()
        self._update_hud()
        self.centre_text.setText("")
        self.sub_text.setText("")

        self.taskMgr.remove("game_loop")
        self.taskMgr.add(self._game_loop, "game_loop")

    def _spawn_wave(self):
        count = WAVE_ENEMY_BASE + (self.wave - 1) * 3
        half  = ARENA_SIZE / 2 - 1.5
        for _ in range(count):
            while True:
                x = random.uniform(-half, half)
                y = random.uniform(-half, half)
                if math.hypot(x, y) > 5:   # keep away from spawn centre
                    break
            self.enemies.append(Enemy(self, x, y))

    # ── Main loop ────────────────────────────────────────────────────────────
    def _game_loop(self, task):
        dt = globalClock.getDt()
        dt = min(dt, 0.05)   # clamp to avoid spiral of death

        if self.game_over:
            return Task.cont

        # wave-clear pause
        if self.wave_paused:
            self.wave_pause_t -= dt
            if self.wave_pause_t <= 0:
                self.wave_paused = False
                self.wave += 1
                self._spawn_wave()
                self._update_hud()
                self.centre_text.setText("")
                self.sub_text.setText("")
            return Task.cont

        # player movement
        dx = (self.keys["d"] - self.keys["a"])
        dy = (self.keys["w"] - self.keys["s"])
        length = math.hypot(dx, dy)
        if length > 0:
            dx, dy = dx / length, dy / length
        self.player.move(dx, dy, dt)

        # fire cooldown
        self.fire_timer = max(0, self.fire_timer - dt)

        # update bullets
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if b.alive]

        # update enemies
        px, py = self.player.node.getX(), self.player.node.getY()
        for e in self.enemies:
            e.update(dt, px, py)
        self.enemies = [e for e in self.enemies if e.alive]

        # collision detection
        self.c_trav.traverse(self.render)
        self._handle_collisions()

        # check player death
        if not self.player.alive:
            self._end_game()
            return Task.cont

        # check wave cleared
        if not self.enemies:
            self.wave_paused  = True
            self.wave_pause_t = 2.5
            self.centre_text.setText(f"Wave {self.wave} Cleared!")
            self.sub_text.setText("Next wave incoming…")

        self._update_hud()
        return Task.cont

    # ── Shooting ─────────────────────────────────────────────────────────────
    def _shoot(self):
        if self.game_over or self.wave_paused or self.fire_timer > 0:
            return
        if not self.mouseWatcherNode.hasMouse():
            return

        m = self.mouseWatcherNode.getMouse()
        # unproject mouse to world plane z=0
        near_pt = Point3(); far_pt = Point3()
        self.camLens.extrude(m, near_pt, far_pt)
        near_w = self.render.getRelativePoint(self.cam, near_pt)
        far_w  = self.render.getRelativePoint(self.cam, far_pt)

        t = -near_w.getZ() / (far_w.getZ() - near_w.getZ() + 1e-9)
        world_x = near_w.getX() + t * (far_w.getX() - near_w.getX())
        world_y = near_w.getY() + t * (far_w.getY() - near_w.getY())

        px, py = self.player.node.getX(), self.player.node.getY()
        ddx, ddy = world_x - px, world_y - py
        dist = math.hypot(ddx, ddy)
        if dist < 0.01:
            return

        self.bullets.append(Bullet(self, px, py, ddx / dist, ddy / dist))
        self.fire_timer = FIRE_COOLDOWN

    # ── Collision resolution ──────────────────────────────────────────────────
    def _handle_collisions(self):
        hit_enemies  = set()
        hit_player   = False

        for entry in self.c_handler.getEntries():
            fn = entry.getFromNode().getName()
            in_ = entry.getIntoNode().getName()

            # bullet hits enemy
            if fn == "bullet_col" and in_ == "enemy_col":
                b_np = entry.getFromNodePath().getParent()
                e_np = entry.getIntoNodePath().getParent()
                hit_enemies.add(id(e_np))
                # mark bullet dead
                for b in self.bullets:
                    if b.node == b_np:
                        b.alive = False
                        try: b.node.removeNode()
                        except Exception: pass

            # player hits enemy
            if fn == "player_col" and in_ == "enemy_col":
                hit_player = True

        # destroy hit enemies
        for e in self.enemies:
            if id(e.node) in hit_enemies:
                e.destroy()
                self.score += 10

        if hit_player and self.player.alive:
            self.player.take_damage()

        # remove dead bullets from list (already removed node above)
        self.bullets = [b for b in self.bullets if b.alive]

    # ── HUD ──────────────────────────────────────────────────────────────────
    def _update_hud(self):
        self.score_text.setText(f"Score: {self.score}")
        hearts = "♥ " * self.player.health + "♡ " * (MAX_HEALTH - self.player.health)
        self.health_text.setText(f"Health: {hearts.strip()}")
        self.wave_text.setText(f"Wave: {self.wave}")

    # ── Game over ─────────────────────────────────────────────────────────────
    def _end_game(self):
        self.game_over = True
        self.centre_text.setText("GAME OVER")
        self.sub_text.setText(f"Score: {self.score}   |   Wave: {self.wave}   |   Press R to restart")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    game = ArenaShooter()
    game.run()
